from fastapi import Request, status

from app.application.auth.use_cases.csrf import CsrfTokenService
from app.core.config import Settings
from app.application.auth.types import AuthIdentity
from app.interfaces.web.presenters.common import csrf_token_for_request, templates


# Upload panel context intentionally avoids drop list queries.
def upload_panel_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    selected_key: str | None = None,
    upload_error_message: str | None = None,
    upload_status_message: str | None = None,
) -> dict:
    return {
        "request": request,
        "is_login": bool(auth_data.username),
        "selected_key": selected_key,
        "csrf_token": csrf_token_for_request(request, settings, csrf_service),
        "upload_error_message": upload_error_message,
        "upload_status_message": upload_status_message,
    }


def render_upload_panel(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    status_code: int = status.HTTP_200_OK,
    selected_key: str | None = None,
    upload_error_message: str | None = None,
    upload_status_message: str | None = None,
):
    context = upload_panel_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        selected_key=selected_key,
        upload_error_message=upload_error_message,
        upload_status_message=upload_status_message,
    )
    return templates(settings).TemplateResponse(
        request=request,
        name="panels/upload.html",
        context=context,
        status_code=status_code,
    )
