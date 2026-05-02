from fastapi import Request, status

from app.application.auth.use_cases.csrf import CsrfTokenService
from app.core.config import Settings
from app.application.auth.types import AuthIdentity
from app.interfaces.web.presenters.common import (
    base_template_context,
    finalize_ui_response,
    templates,
)


def auth_panel_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    auth_error_message: str | None = None,
    auth_mode: str = "login",
    username_value: str = "",
) -> dict:
    registration_enabled = bool(getattr(settings, "ENABLE_REGISTRATION", False))
    selected_auth_mode = "register" if registration_enabled and auth_mode == "register" else "login"
    return base_template_context(
        request=request,
        auth_data=auth_data,
        settings=settings,
        csrf_service=csrf_service,
        auth_error_message=auth_error_message,
        auth_mode=selected_auth_mode,
        registration_enabled=registration_enabled,
        username_value=username_value,
    )


def render_auth_panel(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    status_code: int = status.HTTP_200_OK,
    auth_error_message: str | None = None,
    auth_mode: str = "login",
    username_value: str = "",
):
    context = auth_panel_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        auth_error_message=auth_error_message,
        auth_mode=auth_mode,
        username_value=username_value,
    )
    return finalize_ui_response(
        request,
        templates().TemplateResponse(
            request=request,
            name="panels/auth.html",
            context=context,
            status_code=status_code,
        ),
        settings,
    )
