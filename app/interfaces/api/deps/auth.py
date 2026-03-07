from typing import Annotated

from fastapi import Depends, Request, Response

from app.application.auth.models import VerifyApiKeyQuery
from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases import (
    VerifyApiKeyUseCase,
    VerifySessionUseCase,
)
from app.bootstrap.container import SettingsDep
from app.core.auth import clear_session_cookie
from app.domain.auth.errors import ApiKeyInvalid
from app.interfaces.api.errors import (
    api_auth_unauthorized_exception,
    response_set_cookie_header,
)
from app.interfaces.deps.auth import (
    CreateApiKeyUseCaseDep,
    DeleteApiKeyUseCaseDep,
    ListApiKeysUseCaseDep,
    OptionalApiAuthDep as SharedOptionalApiAuthDep,
    OptionalSessionAuthDep as SharedOptionalSessionAuthDep,
    PasswordLoginUseCaseDep,
    RevokeApiKeyUseCaseDep,
    RevokeSessionUseCaseDep,
    VerifyApiKeyUseCaseDep,
    authenticate_with_session,
    extract_api_key,
    get_create_api_key_use_case,
    get_delete_api_key_use_case,
    get_list_api_keys_use_case,
    get_password_login_use_case,
    get_revoke_api_key_use_case,
    get_revoke_session_use_case,
    get_verify_api_key_use_case,
    get_verify_session_use_case,
)


class SessionOnlyAuthenticator:
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(
        self,
        request: Request,
        response: Response,
        settings: SettingsDep,
        verify_session_use_case: VerifySessionUseCase = Depends(get_verify_session_use_case),
    ) -> AuthIdentity:
        identity = await authenticate_with_session(
            request=request,
            response=response,
            settings=settings,
            verify_session_use_case=verify_session_use_case,
        )
        if identity.username is not None:
            return identity

        if self.auto_error:
            clear_session_cookie(response, settings)
            raise api_auth_unauthorized_exception(
                detail="Authentication credentials were not provided or are invalid.",
                set_cookie=response_set_cookie_header(response),
            )

        return identity


class SessionOrApiKeyAuthenticator:
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(
        self,
        request: Request,
        response: Response,
        settings: SettingsDep,
        verify_session_use_case: VerifySessionUseCase = Depends(get_verify_session_use_case),
        verify_api_key_use_case: VerifyApiKeyUseCase = Depends(get_verify_api_key_use_case),
    ) -> AuthIdentity:
        identity = await authenticate_with_session(
            request=request,
            response=response,
            settings=settings,
            verify_session_use_case=verify_session_use_case,
        )
        if identity.username is not None:
            return identity

        api_key = extract_api_key(request)
        if api_key:
            try:
                username = await verify_api_key_use_case.execute(
                    VerifyApiKeyQuery(api_key=api_key)
                )
                return AuthIdentity(username=username)
            except ApiKeyInvalid:
                pass

        if self.auto_error:
            clear_session_cookie(response, settings)
            raise api_auth_unauthorized_exception(
                detail="Authentication credentials were not provided or are invalid.",
                set_cookie=response_set_cookie_header(response),
            )

        return AuthIdentity(username=None)


OptionalSessionAuthDep = SharedOptionalSessionAuthDep
OptionalApiAuthDep = SharedOptionalApiAuthDep
RequiredSessionAuthDep = Annotated[
    AuthIdentity,
    Depends(SessionOnlyAuthenticator(auto_error=True)),
]
RequiredApiAuthDep = Annotated[
    AuthIdentity,
    Depends(SessionOrApiKeyAuthenticator(auto_error=True)),
]

# Backward-compat aliases for existing API-layer imports.
AuthDep = RequiredApiAuthDep
RequiredAuthDep = RequiredApiAuthDep
OptionalAuthDep = OptionalApiAuthDep

__all__ = [
    "AuthDep",
    "CreateApiKeyUseCaseDep",
    "DeleteApiKeyUseCaseDep",
    "ListApiKeysUseCaseDep",
    "OptionalApiAuthDep",
    "OptionalAuthDep",
    "OptionalSessionAuthDep",
    "PasswordLoginUseCaseDep",
    "RequiredApiAuthDep",
    "RequiredAuthDep",
    "RequiredSessionAuthDep",
    "RevokeApiKeyUseCaseDep",
    "RevokeSessionUseCaseDep",
    "SessionOnlyAuthenticator",
    "SessionOrApiKeyAuthenticator",
    "VerifyApiKeyUseCaseDep",
    "authenticate_with_session",
    "extract_api_key",
    "get_create_api_key_use_case",
    "get_delete_api_key_use_case",
    "get_list_api_keys_use_case",
    "get_password_login_use_case",
    "get_revoke_api_key_use_case",
    "get_revoke_session_use_case",
    "get_verify_api_key_use_case",
    "get_verify_session_use_case",
]
