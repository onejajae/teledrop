from fastapi import Request, status

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.core.config import Settings
from app.interfaces.web.presenters.common import finalize_ui_response, templates
from app.interfaces.web.presenters.auth_panel import auth_panel_context
from app.interfaces.web.presenters.upload_panel import upload_panel_context

_AUTH_ERROR_MESSAGES = {
    "login_invalid": "아이디 또는 비밀번호가 올바르지 않습니다.",
    "logout_csrf_invalid": "세션이 변경되었습니다. 다시 시도해 주세요.",
}


def home_page_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    auth_error_code: str | None = None,
) -> dict:
    if auth_data.is_authenticated:
        panel_context = upload_panel_context(
            request=request,
            auth_data=auth_data,
            csrf_service=csrf_service,
            settings=settings,
        )
    else:
        panel_context = auth_panel_context(
            request=request,
            auth_data=auth_data,
            csrf_service=csrf_service,
            settings=settings,
            auth_error_message=_AUTH_ERROR_MESSAGES.get(auth_error_code),
        )

    panel_context["active_nav"] = "home"
    return panel_context


def render_home_page(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    status_code: int = status.HTTP_200_OK,
    auth_error_code: str | None = None,
):
    context = home_page_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        auth_error_code=auth_error_code,
    )
    return finalize_ui_response(
        request,
        templates().TemplateResponse(
            request=request,
            name="pages/home.html",
            context=context,
            status_code=status_code,
        ),
        settings,
    )


__all__ = ["home_page_context", "render_home_page"]
