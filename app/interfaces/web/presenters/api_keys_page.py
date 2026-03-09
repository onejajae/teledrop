from datetime import datetime, timezone

from fastapi import Request, status

from app.application.auth.models import ApiKeyDTO, CreatedApiKeyDTO
from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases import CsrfTokenService, ListApiKeysUseCase
from app.core.config import Settings
from app.interfaces.web.presenters.common import csrf_token_for_request, templates


def _as_template_api_key(item: ApiKeyDTO) -> dict:
    now = datetime.now(tz=timezone.utc)
    expires_at = item.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    return {
        "public_id": item.public_id,
        "name": item.name,
        "created_by_username": item.created_by_username,
        "created_at": item.created_at,
        "expires_at": expires_at,
        "last_used_at": item.last_used_at,
        "revoked_at": item.revoked_at,
        "is_active": item.revoked_at is None and (expires_at is None or expires_at > now),
    }


async def api_keys_page_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    list_api_keys_use_case: ListApiKeysUseCase,
    settings: Settings,
    status_message: str | None = None,
    error_message: str | None = None,
    created_api_key: CreatedApiKeyDTO | None = None,
) -> dict:
    items = await list_api_keys_use_case.execute()
    return {
        "request": request,
        "is_login": bool(auth_data.username),
        "active_nav": "api_keys",
        "auth_username": auth_data.username,
        "csrf_token": csrf_token_for_request(request, settings, csrf_service),
        "api_keys": [_as_template_api_key(item) for item in items],
        "api_keys_status_message": status_message,
        "api_keys_error_message": error_message,
        "created_api_key": created_api_key,
    }


async def render_api_keys_page(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    list_api_keys_use_case: ListApiKeysUseCase,
    settings: Settings,
    status_code: int = status.HTTP_200_OK,
    status_message: str | None = None,
    error_message: str | None = None,
    created_api_key: CreatedApiKeyDTO | None = None,
):
    context = await api_keys_page_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        list_api_keys_use_case=list_api_keys_use_case,
        settings=settings,
        status_message=status_message,
        error_message=error_message,
        created_api_key=created_api_key,
    )

    return templates(settings).TemplateResponse(
        request=request,
        name="pages/api_keys.html",
        context=context,
        status_code=status_code,
    )


__all__ = ["api_keys_page_context", "render_api_keys_page"]
