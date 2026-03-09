from fastapi import Request, status

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.core.config import Settings
from app.interfaces.web.presenters.common import templates
from app.interfaces.web.presenters.auth_panel import auth_panel_context
from app.interfaces.web.presenters.upload_panel import upload_panel_context


def home_page_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
) -> dict:
    if auth_data.username:
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
        )

    panel_context["active_nav"] = "home"
    return panel_context


def render_home_page(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    status_code: int = status.HTTP_200_OK,
):
    context = home_page_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
    )
    return templates(settings).TemplateResponse(
        request=request,
        name="pages/home.html",
        context=context,
        status_code=status_code,
    )


__all__ = ["home_page_context", "render_home_page"]
