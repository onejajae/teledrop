from fastapi import Request, status

from app.application.auth.use_cases.csrf import CsrfTokenService
from app.core.config import Settings
from app.application.auth.types import AuthIdentity
from app.interfaces.web.presenters.common import csrf_token_for_request, templates


def auth_panel_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    auth_error_message: str | None = None,
) -> dict:
    return {
        "request": request,
        "is_login": bool(auth_data.username),
        "auth_username": auth_data.username,
        "csrf_token": csrf_token_for_request(request, settings, csrf_service),
        "auth_error_message": auth_error_message,
    }


def render_auth_panel(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    status_code: int = status.HTTP_200_OK,
    auth_error_message: str | None = None,
):
    context = auth_panel_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        auth_error_message=auth_error_message,
    )
    return templates(settings).TemplateResponse(
        request=request,
        name="panels/auth.html",
        context=context,
        status_code=status_code,
    )
