from fastapi import Depends, Request

from app.application.auth.models import VerifySessionQuery
from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases import VerifySessionUseCase
from app.bootstrap.container import get_app_settings
from app.bootstrap.providers.auth import get_verify_session_use_case
from app.core.auth import get_session_id_from_request
from app.core.config import Settings
from app.domain.auth.errors import SessionExpired, SessionInvalid
from app.interfaces.web.presenters.common import mark_session_cookie_for_clear


def session_cookie_clear_pending(request: Request) -> bool:
    return bool(getattr(request.state, "clear_session_cookie_pending", False))


async def authenticate_with_session(
    *,
    request: Request,
    settings: Settings = Depends(get_app_settings),
    verify_session_use_case: VerifySessionUseCase,
) -> AuthIdentity:
    session_id = get_session_id_from_request(request, settings)
    if not session_id:
        return AuthIdentity(user_id=None, username=None)

    try:
        identity = await verify_session_use_case.execute(VerifySessionQuery(sid=session_id))
    except (SessionExpired, SessionInvalid):
        mark_session_cookie_for_clear(request)
        return AuthIdentity(user_id=None, username=None)

    return identity


def extract_api_key(request: Request) -> str | None:
    value = request.headers.get("X-API-Key")
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


async def get_optional_session_auth(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    verify_session_use_case: VerifySessionUseCase = Depends(get_verify_session_use_case),
) -> AuthIdentity:
    return await authenticate_with_session(
        request=request,
        settings=settings,
        verify_session_use_case=verify_session_use_case,
    )


__all__ = [
    "authenticate_with_session",
    "extract_api_key",
    "get_optional_session_auth",
    "session_cookie_clear_pending",
]
