from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from fastapi import Depends

from app.application.auth.ports import (
    AuthApiKeyUnitOfWorkFactory,
    AuthSessionUnitOfWorkFactory,
)
from app.application.auth.use_cases import (
    CreateApiKeyUseCase,
    CreateSessionUseCase,
    DeleteApiKeyUseCase,
    ListApiKeysUseCase,
    PasswordLoginUseCase,
    RevokeApiKeyUseCase,
    RevokeSessionUseCase,
    VerifyApiKeyUseCase,
    VerifySessionUseCase,
)
from app.bootstrap.container import get_app_settings, get_db_session_factory
from app.core.config import Settings
from app.infrastructure.db.repositories import SQLModelApiKeyReadRepository
from app.infrastructure.db.uow_api_key import SQLModelApiKeyUnitOfWork
from app.infrastructure.db.uow_auth import SQLModelAuthSessionUnitOfWork


def get_auth_session_uow_factory(
    db_session_factory: sessionmaker[Session] = Depends(get_db_session_factory),
) -> AuthSessionUnitOfWorkFactory:
    return lambda: SQLModelAuthSessionUnitOfWork(db_session_factory)


def get_auth_api_key_read_repository(
    db_session_factory: sessionmaker[Session] = Depends(get_db_session_factory),
) -> SQLModelApiKeyReadRepository:
    return SQLModelApiKeyReadRepository(db_session_factory)


def get_auth_api_key_uow_factory(
    db_session_factory: sessionmaker[Session] = Depends(get_db_session_factory),
) -> AuthApiKeyUnitOfWorkFactory:
    return lambda: SQLModelApiKeyUnitOfWork(db_session_factory)


def get_create_session_use_case(
    settings: Settings = Depends(get_app_settings),
    session_uow_factory: AuthSessionUnitOfWorkFactory = Depends(get_auth_session_uow_factory),
) -> CreateSessionUseCase:
    return CreateSessionUseCase(
        session_ttl_seconds=settings.SESSION_TTL_SECONDS,
        uow_factory=session_uow_factory,
    )


def get_verify_session_use_case(
    session_uow_factory: AuthSessionUnitOfWorkFactory = Depends(get_auth_session_uow_factory),
) -> VerifySessionUseCase:
    return VerifySessionUseCase(uow_factory=session_uow_factory)


def get_revoke_session_use_case(
    session_uow_factory: AuthSessionUnitOfWorkFactory = Depends(get_auth_session_uow_factory),
) -> RevokeSessionUseCase:
    return RevokeSessionUseCase(uow_factory=session_uow_factory)


def get_password_login_use_case(
    settings: Settings = Depends(get_app_settings),
    create_session_use_case: CreateSessionUseCase = Depends(get_create_session_use_case),
) -> PasswordLoginUseCase:
    return PasswordLoginUseCase(
        web_username=settings.WEB_USERNAME,
        web_password_hash=settings.WEB_PASSWORD,
        create_session_use_case=create_session_use_case,
    )


def get_create_api_key_use_case(
    api_key_uow_factory: AuthApiKeyUnitOfWorkFactory = Depends(get_auth_api_key_uow_factory),
) -> CreateApiKeyUseCase:
    return CreateApiKeyUseCase(uow_factory=api_key_uow_factory)


def get_list_api_keys_use_case(
    api_key_read_repository: SQLModelApiKeyReadRepository = Depends(
        get_auth_api_key_read_repository
    ),
) -> ListApiKeysUseCase:
    return ListApiKeysUseCase(repository=api_key_read_repository)


def get_revoke_api_key_use_case(
    api_key_uow_factory: AuthApiKeyUnitOfWorkFactory = Depends(get_auth_api_key_uow_factory),
) -> RevokeApiKeyUseCase:
    return RevokeApiKeyUseCase(uow_factory=api_key_uow_factory)


def get_delete_api_key_use_case(
    api_key_uow_factory: AuthApiKeyUnitOfWorkFactory = Depends(get_auth_api_key_uow_factory),
) -> DeleteApiKeyUseCase:
    return DeleteApiKeyUseCase(uow_factory=api_key_uow_factory)


def get_verify_api_key_use_case(
    api_key_uow_factory: AuthApiKeyUnitOfWorkFactory = Depends(get_auth_api_key_uow_factory),
) -> VerifyApiKeyUseCase:
    return VerifyApiKeyUseCase(uow_factory=api_key_uow_factory)


__all__ = [
    "get_auth_api_key_read_repository",
    "get_auth_api_key_uow_factory",
    "get_auth_session_uow_factory",
    "get_create_api_key_use_case",
    "get_create_session_use_case",
    "get_delete_api_key_use_case",
    "get_list_api_keys_use_case",
    "get_password_login_use_case",
    "get_revoke_api_key_use_case",
    "get_revoke_session_use_case",
    "get_verify_api_key_use_case",
    "get_verify_session_use_case",
]
