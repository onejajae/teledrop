from fastapi import Request, status

from app.application.auth.models import CreatedApiKeyDTO, ListApiKeysQuery
from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases import CsrfTokenService, ListApiKeysUseCase
from app.core.config import Settings
from app.interfaces.web.presenters.common import (
    as_api_key_vm,
    as_created_api_key_vm,
    base_template_context,
    finalize_ui_response,
    templates,
)


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
    query = ListApiKeysQuery(owner_user_id=auth_data.user_id or "")
    items = await list_api_keys_use_case.execute(query)
    return base_template_context(
        request=request,
        auth_data=auth_data,
        settings=settings,
        csrf_service=csrf_service,
        active_nav="api_keys",
        api_keys=[as_api_key_vm(item) for item in items],
        api_keys_status_message=status_message,
        api_keys_error_message=error_message,
        created_api_key=(
            as_created_api_key_vm(created_api_key)
            if created_api_key is not None
            else None
        ),
    )


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

    return finalize_ui_response(
        request,
        templates().TemplateResponse(
            request=request,
            name="pages/api_keys.html",
            context=context,
            status_code=status_code,
        ),
        settings,
    )


__all__ = ["api_keys_page_context", "render_api_keys_page"]
