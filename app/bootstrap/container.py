import logging
import threading

from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from app.application.auth.use_cases import CsrfTokenService
from app.application.drop.ports import DropSlugCandidateGeneratorPort
from app.bootstrap.runtime_paths import project_root_dir
from app.core.config import Settings
from app.infrastructure.db.engine import create_db_engine, create_db_session_factory
from app.infrastructure.slug import (
    PatternWordPoolsSlugCandidateGenerator,
    UuidHexSlugCandidateGenerator,
    load_slug_word_pools_from_dir,
)
from app.infrastructure.storage.local_file_storage import LocalFileStorage


logger = logging.getLogger(__name__)
_app_state_lock = threading.Lock()


@dataclass(slots=True)
class AppInfra:
    settings: Settings
    db_engine: Engine
    db_session_factory: sessionmaker[Session]
    file_storage: LocalFileStorage
    drop_slug_candidate_generator: DropSlugCandidateGeneratorPort
    csrf_token_service: CsrfTokenService


def _resolve_slug_words_dir(settings: Settings) -> Path:
    configured = getattr(settings, "SLUG_WORDS_FILES_DIR", "app/core/data/slug_words")
    candidate = Path(configured)
    if candidate.is_absolute():
        return candidate
    return project_root_dir() / candidate


def build_drop_slug_candidate_generator(settings: Settings) -> DropSlugCandidateGeneratorPort:
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


def build_app_infra(settings: Settings) -> AppInfra:
    db_engine = create_db_engine(settings)
    return AppInfra(
        settings=settings,
        db_engine=db_engine,
        db_session_factory=create_db_session_factory(db_engine),
        file_storage=LocalFileStorage(settings.SHARE_DIRECTORY),
        drop_slug_candidate_generator=build_drop_slug_candidate_generator(settings),
        csrf_token_service=CsrfTokenService(settings.CSRF_SECRET_KEY),
    )


def attach_app_infra(app: FastAPI, settings: Settings) -> None:
    app.state.infra = build_app_infra(settings)


def ensure_app_infra(
    app: FastAPI,
    *,
    settings: Settings | None = None,
) -> None:
    if hasattr(app.state, "infra"):
        return None

    if settings is None:
        raise RuntimeError(
            "App infrastructure is not attached. Use create_app() or attach_app_infra() "
            "before resolving application dependencies."
        )

    with _app_state_lock:
        if hasattr(app.state, "infra"):
            return None

        attach_app_infra(app, settings)
        return None


def _missing_infra_error() -> RuntimeError:
    return RuntimeError(
        "App infrastructure is not attached. Use create_app() or attach_app_infra() "
        "before resolving application dependencies."
    )


def _get_attached_infra(request: Request) -> AppInfra | None:
    return getattr(request.app.state, "infra", None)


def _require_infra(request: Request) -> AppInfra:
    infra = _get_attached_infra(request)
    if infra is None:
        raise _missing_infra_error()
    return infra


def get_app_settings(request: Request) -> Settings:
    return _require_infra(request).settings


def _require_state_attr(request: Request, attr_name: str):
    infra = _require_infra(request)
    value = getattr(infra, attr_name, None)
    if value is None:
        raise RuntimeError(
            "App infrastructure is not attached. Use create_app() or attach_app_infra() "
            "before resolving application dependencies."
        )
    return value


def get_db_engine(request: Request) -> Engine:
    return _require_state_attr(request, "db_engine")


def get_db_session_factory(request: Request) -> sessionmaker[Session]:
    return _require_state_attr(request, "db_session_factory")


def get_file_storage(request: Request) -> LocalFileStorage:
    return _require_state_attr(request, "file_storage")


def get_drop_slug_candidate_generator(request: Request) -> DropSlugCandidateGeneratorPort:
    return _require_state_attr(request, "drop_slug_candidate_generator")


def get_csrf_token_service(request: Request) -> CsrfTokenService:
    return _require_state_attr(request, "csrf_token_service")


__all__ = [
    "AppInfra",
    "attach_app_infra",
    "build_app_infra",
    "build_drop_slug_candidate_generator",
    "ensure_app_infra",
    "get_app_settings",
    "get_csrf_token_service",
    "get_db_engine",
    "get_db_session_factory",
    "get_drop_slug_candidate_generator",
    "get_file_storage",
]
