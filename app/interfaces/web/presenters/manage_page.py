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


def _status_description_from_selected_drop(selected_drop) -> str | None:
    if selected_drop is None:
        return None

    if selected_drop.access_scope == "private":
        if selected_drop.requires_password:
            return "외부 공유는 꺼져 있으며 비밀번호가 설정되어 있습니다."
        return "로그인된 관리자만 접근할 수 있습니다."

    if selected_drop.requires_password:
        return "공유 링크는 활성화되어 있고, 비밀번호를 아는 사용자만 열람할 수 있습니다."

    return "공유 링크가 활성화되어 있어 외부 사용자가 바로 열람할 수 있습니다."


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
    status_description = _status_description_from_selected_drop(selected_drop)
    context.update(
        {
            "active_nav": "drops",
            "auth_username": auth_data.username,
            "detail_mode": "manage",
            "selected_manage_page_url": drop_manage_page_url(slug),
            "selected_can_copy_link": bool(
                selected_drop and selected_drop.access_scope == "public"
            ),
            "selected_status_label": status_label,
            "selected_status_tone": status_tone,
            "selected_status_appearance": status_appearance,
            "selected_status_description": status_description,
            "locked_form_action": drop_manage_page_url(slug),
            "locked_form_use_hx": False,
            "locked_form_include_slug": False,
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
