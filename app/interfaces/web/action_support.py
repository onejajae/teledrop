from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import RedirectResponse

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.core.config import Settings
from app.interfaces.web.presenters.common import csrf_is_valid, unauthorized_ui_response


def is_hx_request(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def redirect_home() -> RedirectResponse:
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


async def require_auth_and_csrf(
    *,
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    csrf_token: str,
    on_csrf_failure: Callable[[], Awaitable[Response]],
) -> Response | None:
    if not auth_data.is_authenticated:
        return unauthorized_ui_response(request, settings)

    if not csrf_is_valid(request, settings, csrf_service, csrf_token):
        return await on_csrf_failure()

    return None
