from fastapi import Request, status

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.drop.use_cases import GetDropMetaUseCase
from app.core.config import Settings
from app.interfaces.web.presenters.common import (
    drop_access_status_badge,
    drop_manage_page_url,
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
    password: str | None = None,
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
        selected_password=password,
        detail_error_message=detail_error_message,
        detail_status_message=detail_status_message,
    )
    selected_drop = context.get("selected_drop")
    status_label, status_tone, status_appearance = drop_access_status_badge(selected_drop)
    context.update(
        {
            "active_nav": "drops",
            "detail_mode": "manage",
            "selected_manage_page_url": drop_manage_page_url(slug),
            "selected_can_copy_link": bool(
                selected_drop and selected_drop.access_scope == "public"
            ),
            "selected_status_label": status_label,
            "selected_status_tone": status_tone,
            "selected_status_appearance": status_appearance,
            "locked_form_action": drop_manage_page_url(slug),
        }
    )
    return context


async def render_manage_page(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    get_drop_meta_use_case: GetDropMetaUseCase,
    settings: Settings,
    slug: str,
    password: str | None = None,
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
        password=password,
        detail_error_message=detail_error_message,
        detail_status_message=detail_status_message,
    )
    return templates().TemplateResponse(
        request=request,
        name="pages/manage_drop.html",
        context=context,
        status_code=status_code,
    )


__all__ = ["manage_page_context", "render_manage_page"]
