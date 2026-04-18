from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from fastapi import Depends

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
from app.bootstrap.container import (
    get_app_settings,
    get_db_session_factory,
    get_drop_slug_candidate_generator,
    get_file_storage,
)
from app.core.config import Settings
from app.domain.drop.grants import DropPasswordGrantService
from app.infrastructure.db.repositories import SQLModelDropReadRepository
from app.infrastructure.db.uow_drop import SQLModelDropUnitOfWork
from app.infrastructure.storage.local_file_storage import LocalFileStorage


def get_drop_read_repository(
    db_session_factory: sessionmaker[Session] = Depends(get_db_session_factory),
) -> SQLModelDropReadRepository:
    return SQLModelDropReadRepository(db_session_factory)


def get_drop_uow_factory(
    db_session_factory: sessionmaker[Session] = Depends(get_db_session_factory),
) -> DropUnitOfWorkFactory:
    return lambda: SQLModelDropUnitOfWork(db_session_factory)


def get_drop_slug_service(
    repository: SQLModelDropReadRepository = Depends(get_drop_read_repository),
    candidate_generator: DropSlugCandidateGeneratorPort = Depends(
        get_drop_slug_candidate_generator
    ),
) -> DropSlugService:
    return DropSlugService(
        repository=repository,
        candidate_generator=candidate_generator,
    )


def get_create_drop_use_case(
    storage: LocalFileStorage = Depends(get_file_storage),
    slug_service: DropSlugService = Depends(get_drop_slug_service),
    uow_factory: DropUnitOfWorkFactory = Depends(get_drop_uow_factory),
) -> CreateDropUseCase:
    return CreateDropUseCase(
        storage=storage,
        slug_service=slug_service,
        uow_factory=uow_factory,
    )


def get_list_drops_use_case(
    repository: SQLModelDropReadRepository = Depends(get_drop_read_repository),
    settings: Settings = Depends(get_app_settings),
) -> ListDropsUseCase:
    return ListDropsUseCase(
        repository=repository,
        default_page_size=settings.DEFAULT_PAGE_SIZE,
        max_page_size=settings.MAX_PAGE_SIZE,
    )


def get_drop_password_grant_service(
    settings: Settings = Depends(get_app_settings),
) -> DropPasswordGrantService:
    return DropPasswordGrantService(
        getattr(settings, "CSRF_SECRET_KEY", "teledrop-drop-grant-dev-secret"),
        ttl_seconds=settings.SESSION_TTL_SECONDS,
    )


def get_get_drop_meta_use_case(
    repository: SQLModelDropReadRepository = Depends(get_drop_read_repository),
    grant_service: DropPasswordGrantService = Depends(get_drop_password_grant_service),
) -> GetDropMetaUseCase:
    return GetDropMetaUseCase(repository=repository, grant_service=grant_service)


def get_get_drop_stream_source_use_case(
    repository: SQLModelDropReadRepository = Depends(get_drop_read_repository),
    storage: LocalFileStorage = Depends(get_file_storage),
    grant_service: DropPasswordGrantService = Depends(get_drop_password_grant_service),
) -> GetDropStreamSourceUseCase:
    return GetDropStreamSourceUseCase(
        repository=repository,
        storage=storage,
        grant_service=grant_service,
    )


def get_update_drop_use_case(
    uow_factory: DropUnitOfWorkFactory = Depends(get_drop_uow_factory),
    grant_service: DropPasswordGrantService = Depends(get_drop_password_grant_service),
) -> UpdateDropUseCase:
    return UpdateDropUseCase(
        uow_factory=uow_factory,
        grant_service=grant_service,
    )


def get_delete_drop_use_case(
    storage: LocalFileStorage = Depends(get_file_storage),
    uow_factory: DropUnitOfWorkFactory = Depends(get_drop_uow_factory),
    grant_service: DropPasswordGrantService = Depends(get_drop_password_grant_service),
) -> DeleteDropUseCase:
    return DeleteDropUseCase(
        storage=storage,
        uow_factory=uow_factory,
        grant_service=grant_service,
    )


def get_check_slug_availability_use_case(
    slug_service: DropSlugService = Depends(get_drop_slug_service),
) -> CheckSlugAvailabilityUseCase:
    return CheckSlugAvailabilityUseCase(slug_service=slug_service)


__all__ = [
    "get_check_slug_availability_use_case",
    "get_create_drop_use_case",
    "get_delete_drop_use_case",
    "get_drop_password_grant_service",
    "get_drop_read_repository",
    "get_drop_slug_service",
    "get_drop_uow_factory",
    "get_get_drop_meta_use_case",
    "get_get_drop_stream_source_use_case",
    "get_list_drops_use_case",
    "get_update_drop_use_case",
]
