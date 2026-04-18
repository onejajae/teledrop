from fastapi import Request, status

from app.application.auth.use_cases.csrf import CsrfTokenService
from app.core.config import Settings
from app.application.auth.types import AuthIdentity
from app.interfaces.web.presenters.common import base_template_context, templates


# Upload panel context intentionally avoids drop list queries.
def upload_panel_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    upload_error_message: str | None = None,
) -> dict:
    return base_template_context(
        request=request,
        auth_data=auth_data,
        settings=settings,
        csrf_service=csrf_service,
        upload_error_message=upload_error_message,
    )


def render_upload_panel(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    status_code: int = status.HTTP_200_OK,
    upload_error_message: str | None = None,
):
    context = upload_panel_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        upload_error_message=upload_error_message,
    )
    return templates().TemplateResponse(
        request=request,
        name="panels/upload.html",
        context=context,
        status_code=status_code,
    )
