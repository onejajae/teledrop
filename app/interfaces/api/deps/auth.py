from typing import Annotated

from fastapi import Depends, Request, Response

from app.application.auth.models import VerifyApiKeyQuery, VerifySessionQuery
from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases import (
    CreateApiKeyUseCase,
    DeleteApiKeyUseCase,
    ListApiKeysUseCase,
    PasswordLoginUseCase,
    RevokeApiKeyUseCase,
    RevokeSessionUseCase,
    VerifyApiKeyUseCase,
    VerifySessionUseCase,
)
from app.bootstrap.container import AuthUseCasesDep, SettingsDep
from app.core.auth import clear_session_cookie, get_session_id_from_request
from app.domain.auth.errors import ApiKeyInvalid, SessionExpired, SessionInvalid
from app.interfaces.api.errors import (
    api_auth_unauthorized_exception,
    response_set_cookie_header,
)


def get_verify_session_use_case(
    auth_use_cases: AuthUseCasesDep,
) -> VerifySessionUseCase:
    return auth_use_cases.verify_session_use_case


def get_verify_api_key_use_case(
    auth_use_cases: AuthUseCasesDep,
) -> VerifyApiKeyUseCase:
    return auth_use_cases.verify_api_key_use_case


def get_revoke_session_use_case(
    auth_use_cases: AuthUseCasesDep,
) -> RevokeSessionUseCase:
    return auth_use_cases.revoke_session_use_case


def get_password_login_use_case(
    auth_use_cases: AuthUseCasesDep,
) -> PasswordLoginUseCase:
    return auth_use_cases.password_login_use_case


def get_create_api_key_use_case(
    auth_use_cases: AuthUseCasesDep,
) -> CreateApiKeyUseCase:
    return auth_use_cases.create_api_key_use_case


def get_list_api_keys_use_case(
    auth_use_cases: AuthUseCasesDep,
) -> ListApiKeysUseCase:
    return auth_use_cases.list_api_keys_use_case


def get_revoke_api_key_use_case(
    auth_use_cases: AuthUseCasesDep,
) -> RevokeApiKeyUseCase:
    return auth_use_cases.revoke_api_key_use_case


def get_delete_api_key_use_case(
    auth_use_cases: AuthUseCasesDep,
) -> DeleteApiKeyUseCase:
    return auth_use_cases.delete_api_key_use_case


async def _authenticate_with_session(
    *,
    request: Request,
    response: Response,
    settings: SettingsDep,
    verify_session_use_case: VerifySessionUseCase,
) -> AuthIdentity:
    session_id = get_session_id_from_request(request, settings)
    if not session_id:
        return AuthIdentity(username=None)

    try:
        username = await verify_session_use_case.execute(VerifySessionQuery(sid=session_id))
    except (SessionExpired, SessionInvalid):
        clear_session_cookie(response, settings)
        return AuthIdentity(username=None)

    return AuthIdentity(username=username)


def _extract_api_key(request: Request) -> str | None:
    value = request.headers.get("X-API-Key")
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


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
        identity = await _authenticate_with_session(
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
        identity = await _authenticate_with_session(
            request=request,
            response=response,
            settings=settings,
            verify_session_use_case=verify_session_use_case,
        )
        if identity.username is not None:
            return identity

        api_key = _extract_api_key(request)
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


RequiredSessionAuthDep = Annotated[
    AuthIdentity,
    Depends(SessionOnlyAuthenticator(auto_error=True)),
]
OptionalSessionAuthDep = Annotated[
    AuthIdentity,
    Depends(SessionOnlyAuthenticator(auto_error=False)),
]
RequiredApiAuthDep = Annotated[
    AuthIdentity,
    Depends(SessionOrApiKeyAuthenticator(auto_error=True)),
]
OptionalApiAuthDep = Annotated[
    AuthIdentity,
    Depends(SessionOrApiKeyAuthenticator(auto_error=False)),
]

# Backward-compat aliases for existing API-layer imports.
AuthDep = RequiredApiAuthDep
RequiredAuthDep = RequiredApiAuthDep
OptionalAuthDep = OptionalApiAuthDep

PasswordLoginUseCaseDep = Annotated[PasswordLoginUseCase, Depends(get_password_login_use_case)]
RevokeSessionUseCaseDep = Annotated[RevokeSessionUseCase, Depends(get_revoke_session_use_case)]
CreateApiKeyUseCaseDep = Annotated[CreateApiKeyUseCase, Depends(get_create_api_key_use_case)]
ListApiKeysUseCaseDep = Annotated[ListApiKeysUseCase, Depends(get_list_api_keys_use_case)]
RevokeApiKeyUseCaseDep = Annotated[RevokeApiKeyUseCase, Depends(get_revoke_api_key_use_case)]
DeleteApiKeyUseCaseDep = Annotated[DeleteApiKeyUseCase, Depends(get_delete_api_key_use_case)]
VerifyApiKeyUseCaseDep = Annotated[VerifyApiKeyUseCase, Depends(get_verify_api_key_use_case)]


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
    "get_create_api_key_use_case",
    "get_delete_api_key_use_case",
    "get_list_api_keys_use_case",
    "get_password_login_use_case",
    "get_revoke_api_key_use_case",
    "get_revoke_session_use_case",
    "get_verify_api_key_use_case",
    "get_verify_session_use_case",
]
