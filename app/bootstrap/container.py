import logging
import threading

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from app.application.auth.ports import (
    AuthApiKeyUnitOfWorkFactory,
    AuthSessionUnitOfWorkFactory,
)
from app.application.auth.use_cases import (
    CreateApiKeyUseCase,
    CreateSessionUseCase,
    CsrfTokenService,
    DeleteApiKeyUseCase,
    ListApiKeysUseCase,
    PasswordLoginUseCase,
    RevokeApiKeyUseCase,
    RevokeSessionUseCase,
    VerifyApiKeyUseCase,
    VerifySessionUseCase,
)
from app.application.drop.ports import DropSlugCandidateGeneratorPort, DropUnitOfWorkFactory
from app.application.drop.slug_service import DropSlugService
from app.application.drop.use_cases import (
    CheckSlugAvailabilityUseCase,
    CreateDropUseCase,
    DeleteDropUseCase,
    GetDropMetaUseCase,
    GetDropStreamSourceUseCase,
    ListDropsUseCase,
    UpdateDropUseCase,
)
from app.bootstrap.runtime_paths import project_root_dir
from app.core.config import Settings
from app.infrastructure.db.engine import create_db_engine, create_db_session_factory
from app.infrastructure.db.repositories import (
    SQLModelApiKeyReadRepository,
    SQLModelDropReadRepository,
)
from app.infrastructure.db.uow_api_key import SQLModelApiKeyUnitOfWork
from app.infrastructure.db.uow_auth import SQLModelAuthSessionUnitOfWork
from app.infrastructure.db.uow_drop import SQLModelDropUnitOfWork
from app.infrastructure.slug import (
    PatternWordPoolsSlugCandidateGenerator,
    UuidHexSlugCandidateGenerator,
    load_slug_word_pools_from_dir,
)
from app.infrastructure.storage.local_file_storage import LocalFileStorage


logger = logging.getLogger(__name__)
_container_lock = threading.Lock()


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    db_engine: Engine
    db_session_factory: sessionmaker[Session]
    csrf_token_service: CsrfTokenService
    file_storage: LocalFileStorage
    drop_slug_candidate_generator: DropSlugCandidateGeneratorPort
    create_drop_use_case: CreateDropUseCase
    list_drops_use_case: ListDropsUseCase
    get_drop_meta_use_case: GetDropMetaUseCase
    get_drop_stream_source_use_case: GetDropStreamSourceUseCase
    update_drop_use_case: UpdateDropUseCase
    delete_drop_use_case: DeleteDropUseCase
    check_slug_availability_use_case: CheckSlugAvailabilityUseCase
    password_login_use_case: PasswordLoginUseCase
    create_session_use_case: CreateSessionUseCase
    verify_session_use_case: VerifySessionUseCase
    revoke_session_use_case: RevokeSessionUseCase
    create_api_key_use_case: CreateApiKeyUseCase
    list_api_keys_use_case: ListApiKeysUseCase
    revoke_api_key_use_case: RevokeApiKeyUseCase
    delete_api_key_use_case: DeleteApiKeyUseCase
    verify_api_key_use_case: VerifyApiKeyUseCase


def _resolve_slug_words_dir(settings: Settings) -> Path:
    configured = getattr(settings, "SLUG_WORDS_FILES_DIR", "app/core/data/slug_words")
    candidate = Path(configured)
    if candidate.is_absolute():
        return candidate
    return project_root_dir() / candidate


def _build_drop_slug_candidate_generator(settings: Settings) -> DropSlugCandidateGeneratorPort:
    if not getattr(settings, "SLUG_WORDS_FILES_ENABLED", True):
        return UuidHexSlugCandidateGenerator()

    slug_words_dir = _resolve_slug_words_dir(settings)
    try:
        word_pools = load_slug_word_pools_from_dir(slug_words_dir)
    except Exception as exc:
        logger.warning(
            "Failed to load slug word pools from %s; falling back to UUID-only generator (%s)",
            slug_words_dir,
            exc,
        )
        return UuidHexSlugCandidateGenerator()

    total_words = sum(len(words) for words in word_pools.values())
    logger.info(
        "Loaded slug word pools from %s (%s categories, %s words)",
        slug_words_dir,
        len(word_pools),
        total_words,
    )
    return PatternWordPoolsSlugCandidateGenerator(word_pools)


def _build_drop_use_cases(
    settings: Settings,
    read_repository: SQLModelDropReadRepository,
    storage: LocalFileStorage,
    slug_service: DropSlugService,
    uow_factory: DropUnitOfWorkFactory,
) -> dict[str, object]:
    return {
        "create_drop_use_case": CreateDropUseCase(
            storage=storage,
            slug_service=slug_service,
            uow_factory=uow_factory,
        ),
        "list_drops_use_case": ListDropsUseCase(
            repository=read_repository,
            default_page_size=settings.DEFAULT_PAGE_SIZE,
            max_page_size=settings.MAX_PAGE_SIZE,
        ),
        "get_drop_meta_use_case": GetDropMetaUseCase(repository=read_repository),
        "get_drop_stream_source_use_case": GetDropStreamSourceUseCase(
            repository=read_repository,
            storage=storage,
        ),
        "update_drop_use_case": UpdateDropUseCase(
            uow_factory=uow_factory,
        ),
        "delete_drop_use_case": DeleteDropUseCase(
            storage=storage,
            uow_factory=uow_factory,
        ),
        "check_slug_availability_use_case": CheckSlugAvailabilityUseCase(
            slug_service=slug_service
        ),
    }


def _build_auth_use_cases(
    settings: Settings,
    session_uow_factory: AuthSessionUnitOfWorkFactory,
    api_key_read_repository: SQLModelApiKeyReadRepository,
    api_key_uow_factory: AuthApiKeyUnitOfWorkFactory,
) -> dict[str, object]:
    create_session_use_case = CreateSessionUseCase(
        session_ttl_seconds=settings.SESSION_TTL_SECONDS,
        uow_factory=session_uow_factory,
    )
    return {
        "password_login_use_case": PasswordLoginUseCase(
            web_username=settings.WEB_USERNAME,
            web_password_hash=settings.WEB_PASSWORD,
            create_session_use_case=create_session_use_case,
        ),
        "create_session_use_case": create_session_use_case,
        "verify_session_use_case": VerifySessionUseCase(
            uow_factory=session_uow_factory,
        ),
        "revoke_session_use_case": RevokeSessionUseCase(
            uow_factory=session_uow_factory,
        ),
        "create_api_key_use_case": CreateApiKeyUseCase(
            uow_factory=api_key_uow_factory,
        ),
        "list_api_keys_use_case": ListApiKeysUseCase(
            repository=api_key_read_repository,
        ),
        "revoke_api_key_use_case": RevokeApiKeyUseCase(
            uow_factory=api_key_uow_factory,
        ),
        "delete_api_key_use_case": DeleteApiKeyUseCase(
            uow_factory=api_key_uow_factory,
        ),
        "verify_api_key_use_case": VerifyApiKeyUseCase(
            uow_factory=api_key_uow_factory,
        ),
    }


def build_app_container(settings: Settings) -> AppContainer:
    db_engine = create_db_engine(settings)
    db_session_factory = create_db_session_factory(db_engine)
    file_storage = LocalFileStorage(settings.SHARE_DIRECTORY)
    drop_slug_candidate_generator = _build_drop_slug_candidate_generator(settings)

    drop_read_repository = SQLModelDropReadRepository(db_session_factory)
    drop_uow_factory: DropUnitOfWorkFactory = lambda: SQLModelDropUnitOfWork(db_session_factory)
    drop_slug_service = DropSlugService(
        repository=drop_read_repository,
        candidate_generator=drop_slug_candidate_generator,
    )
    drop_use_cases = _build_drop_use_cases(
        settings=settings,
        read_repository=drop_read_repository,
        storage=file_storage,
        slug_service=drop_slug_service,
        uow_factory=drop_uow_factory,
    )

    session_uow_factory: AuthSessionUnitOfWorkFactory = (
        lambda: SQLModelAuthSessionUnitOfWork(db_session_factory)
    )
    api_key_read_repository = SQLModelApiKeyReadRepository(db_session_factory)
    api_key_uow_factory: AuthApiKeyUnitOfWorkFactory = (
        lambda: SQLModelApiKeyUnitOfWork(db_session_factory)
    )
    auth_use_cases = _build_auth_use_cases(
        settings=settings,
        session_uow_factory=session_uow_factory,
        api_key_read_repository=api_key_read_repository,
        api_key_uow_factory=api_key_uow_factory,
    )

    return AppContainer(
        settings=settings,
        db_engine=db_engine,
        db_session_factory=db_session_factory,
        csrf_token_service=CsrfTokenService(settings.CSRF_SECRET_KEY),
        file_storage=file_storage,
        drop_slug_candidate_generator=drop_slug_candidate_generator,
        **drop_use_cases,
        **auth_use_cases,
    )


def attach_app_container(app: FastAPI, container: AppContainer) -> None:
    app.state.container = container


def ensure_app_container(
    app: FastAPI,
    *,
    settings: Settings | None = None,
) -> AppContainer:
    existing = getattr(app.state, "container", None)
    if existing is not None:
        return existing

    if settings is None:
        raise RuntimeError(
            "App container is not attached. Use create_app() or attach_app_container() "
            "before resolving application dependencies."
        )

    with _container_lock:
        existing = getattr(app.state, "container", None)
        if existing is not None:
            return existing

        container = build_app_container(settings)
        attach_app_container(app, container)
        return container


def get_app_container(request: Request) -> AppContainer:
    container = getattr(request.app.state, "container", None)
    if container is None:
        raise RuntimeError(
            "App container is not attached. Use create_app() or attach_app_container() "
            "before resolving application dependencies."
        )
    return container


def get_app_settings(request: Request) -> Settings:
    return get_app_container(request).settings


AppContainerDep = Annotated[AppContainer, Depends(get_app_container)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
