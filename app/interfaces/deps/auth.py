from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status

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


async def authenticate_with_session(
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


def extract_api_key(request: Request) -> str | None:
    value = request.headers.get("X-API-Key")
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


async def get_optional_session_auth(
    request: Request,
    response: Response,
    settings: SettingsDep,
    verify_session_use_case: VerifySessionUseCase = Depends(get_verify_session_use_case),
) -> AuthIdentity:
    return await authenticate_with_session(
        request=request,
        response=response,
        settings=settings,
        verify_session_use_case=verify_session_use_case,
    )


async def get_optional_api_auth(
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
            username = await verify_api_key_use_case.execute(VerifyApiKeyQuery(api_key=api_key))
            return AuthIdentity(username=username)
        except ApiKeyInvalid:
            pass

    return AuthIdentity(username=None)


OptionalSessionAuthDep = Annotated[AuthIdentity, Depends(get_optional_session_auth)]
OptionalApiAuthDep = Annotated[AuthIdentity, Depends(get_optional_api_auth)]


async def get_required_session_auth(
    auth_data: OptionalSessionAuthDep,
) -> AuthIdentity:
    if auth_data.username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return auth_data


RequiredSessionAuthDep = Annotated[AuthIdentity, Depends(get_required_session_auth)]

PasswordLoginUseCaseDep = Annotated[PasswordLoginUseCase, Depends(get_password_login_use_case)]
RevokeSessionUseCaseDep = Annotated[RevokeSessionUseCase, Depends(get_revoke_session_use_case)]
CreateApiKeyUseCaseDep = Annotated[CreateApiKeyUseCase, Depends(get_create_api_key_use_case)]
ListApiKeysUseCaseDep = Annotated[ListApiKeysUseCase, Depends(get_list_api_keys_use_case)]
RevokeApiKeyUseCaseDep = Annotated[RevokeApiKeyUseCase, Depends(get_revoke_api_key_use_case)]
DeleteApiKeyUseCaseDep = Annotated[DeleteApiKeyUseCase, Depends(get_delete_api_key_use_case)]
VerifyApiKeyUseCaseDep = Annotated[VerifyApiKeyUseCase, Depends(get_verify_api_key_use_case)]
VerifySessionUseCaseDep = Annotated[VerifySessionUseCase, Depends(get_verify_session_use_case)]


__all__ = [
    "CreateApiKeyUseCaseDep",
    "DeleteApiKeyUseCaseDep",
    "ListApiKeysUseCaseDep",
    "OptionalApiAuthDep",
    "RequiredSessionAuthDep",
    "OptionalSessionAuthDep",
    "PasswordLoginUseCaseDep",
    "RevokeApiKeyUseCaseDep",
    "RevokeSessionUseCaseDep",
    "VerifyApiKeyUseCaseDep",
    "VerifySessionUseCaseDep",
    "authenticate_with_session",
    "extract_api_key",
    "get_create_api_key_use_case",
    "get_delete_api_key_use_case",
    "get_list_api_keys_use_case",
    "get_optional_api_auth",
    "get_optional_session_auth",
    "get_password_login_use_case",
    "get_required_session_auth",
    "get_revoke_api_key_use_case",
    "get_revoke_session_use_case",
    "get_verify_api_key_use_case",
    "get_verify_session_use_case",
]
