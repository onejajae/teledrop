from fastapi import Depends, Request, Response

from app.application.auth.models import VerifyApiKeyQuery, VerifySessionQuery
from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases import VerifyApiKeyUseCase, VerifySessionUseCase
from app.bootstrap.container import get_app_settings
from app.bootstrap.providers.auth import (
    get_verify_api_key_use_case,
    get_verify_session_use_case,
)
from app.core.auth import clear_session_cookie, get_session_id_from_request
from app.core.config import Settings
from app.domain.auth.errors import ApiKeyInvalid, SessionExpired, SessionInvalid


async def authenticate_with_session(
    *,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_app_settings),
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
    settings: Settings = Depends(get_app_settings),
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
    settings: Settings = Depends(get_app_settings),
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


__all__ = [
    "authenticate_with_session",
    "extract_api_key",
    "get_optional_api_auth",
    "get_optional_session_auth",
]
