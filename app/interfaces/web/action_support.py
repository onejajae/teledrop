from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import RedirectResponse

from app.application.drop.use_cases import ListDropsUseCase
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.core.config import Settings
from app.domain.drop.errors import DropNotFoundError, DropPasswordInvalidError
from app.application.auth.types import AuthIdentity
from app.interfaces.web.presenters.common import csrf_is_valid, unauthorized_ui_response
from app.interfaces.web.presenters.drop_panel import render_drop_panel


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
    if not auth_data.username:
        return unauthorized_ui_response(request)

    if not csrf_is_valid(request, settings, csrf_service, csrf_token):
        return await on_csrf_failure()

    return None


async def render_drop_panel_error(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    list_drops_use_case: ListDropsUseCase,
    settings: Settings,
    exc: Exception,
) -> Response:
    if isinstance(exc, DropNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
        error_message = "File does not exist."
    elif isinstance(exc, DropPasswordInvalidError):
        status_code = status.HTTP_401_UNAUTHORIZED
        error_message = "Invalid drop password."
    else:
        raise exc

    return await render_drop_panel(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        list_drops_use_case=list_drops_use_case,
        settings=settings,
        status_code=status_code,
        drop_error_message=error_message,
    )


async def drop_panel_success_or_redirect(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    list_drops_use_case: ListDropsUseCase,
    settings: Settings,
    slug: str,
    status_message: str,
) -> Response:
    if is_hx_request(request):
        return await render_drop_panel(
            request=request,
            auth_data=auth_data,
            csrf_service=csrf_service,
            list_drops_use_case=list_drops_use_case,
            settings=settings,
            selected_key=slug,
            drop_status_message=status_message,
        )

    return redirect_home()
