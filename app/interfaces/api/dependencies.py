"""Compatibility facade for API dependency providers and aliases."""

from app.interfaces.api.deps import (
    AuthDep,
    Authenticator,
    CsrfTokenServiceDep,
    DropUseCasesDep,
    OptionalAuthDep,
    PasswordLoginUseCaseDep,
    RequiredAuthDep,
    RevokeSessionUseCaseDep,
    get_create_session_use_case,
    get_csrf_token_service,
    get_drop_use_cases,
    get_password_login_use_case,
    get_revoke_session_use_case,
    get_verify_session_use_case,
)

__all__ = [
    "AuthDep",
    "Authenticator",
    "CsrfTokenServiceDep",
    "DropUseCasesDep",
    "OptionalAuthDep",
    "PasswordLoginUseCaseDep",
    "RequiredAuthDep",
    "RevokeSessionUseCaseDep",
    "get_create_session_use_case",
    "get_csrf_token_service",
    "get_drop_use_cases",
    "get_password_login_use_case",
    "get_revoke_session_use_case",
    "get_verify_session_use_case",
]
