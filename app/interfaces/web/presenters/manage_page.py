from dataclasses import replace

from fastapi import Request, status

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.drop.use_cases import GetDropMetaUseCase
from app.core.config import Settings
from app.core.drop_unlock_tokens import issue_drop_unlock_token
from app.core.drop_grants import clear_drop_grant_cookie
from app.domain.drop.grants import DropPasswordCredential
from app.interfaces.web.presenters.common import (
    drop_access_status_badge,
    drop_manage_page_url,
    drop_unlock_action_url,
    finalize_ui_response,
    templates,
)
from app.interfaces.web.presenters.detail_panel import detail_panel_context


async def manage_page_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    get_drop_meta_use_case: GetDropMetaUseCase,
    settings: Settings,
    slug: str,
    credential: DropPasswordCredential | None = None,
    use_request_grant: bool = True,
    detail_error_message: str | None = None,
    detail_status_message: str | None = None,
) -> dict:
    context = await detail_panel_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        selected_key=slug,
        credential=credential,
        use_request_grant=use_request_grant,
        detail_error_message=detail_error_message,
        detail_status_message=detail_status_message,
    )
    detail = context["detail"]
    selected_drop = detail.drop
    is_owner = bool(
        selected_drop
        and auth_data.user_id
        and selected_drop.owner_user_id == auth_data.user_id
    )
    status_label, status_tone, status_appearance = drop_access_status_badge(selected_drop)
    context["detail"] = replace(
        detail,
        mode="manage",
        urls=replace(
            detail.urls,
            manage=drop_manage_page_url(slug),
        ),
        badge=replace(
            detail.badge,
            label=status_label,
            tone=status_tone,
            appearance=status_appearance,
        ),
        actions=replace(
            detail.actions,
            can_copy_link=bool(selected_drop and selected_drop.access_scope == "public"),
            show_owner_actions=bool(is_owner and detail.access_granted),
        ),
        forms=replace(
            detail.forms,
            locked_prompt_action=drop_unlock_action_url(slug),
            unlock_target_view="manage",
            unlock_token=issue_drop_unlock_token(settings, slug, "manage"),
        ),
    )
    context["active_nav"] = "drops"
    return context


async def render_manage_page(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    get_drop_meta_use_case: GetDropMetaUseCase,
    settings: Settings,
    slug: str,
    credential: DropPasswordCredential | None = None,
    use_request_grant: bool = True,
    status_code: int = status.HTTP_200_OK,
    detail_error_message: str | None = None,
    detail_status_message: str | None = None,
):
    context = await manage_page_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        slug=slug,
        credential=credential,
        use_request_grant=use_request_grant,
        detail_error_message=detail_error_message,
        detail_status_message=detail_status_message,
    )
    effective_status_code = status_code
    if status_code == status.HTTP_200_OK and context["detail"].error.code == "not_found":
        effective_status_code = status.HTTP_404_NOT_FOUND
    response = finalize_ui_response(
        request,
        templates().TemplateResponse(
            request=request,
            name="pages/manage_drop.html",
            context=context,
            status_code=effective_status_code,
        ),
        settings,
    )
    if context["detail"].invalid_grant:
        clear_drop_grant_cookie(response, settings, slug)
    return response


__all__ = ["manage_page_context", "render_manage_page"]
