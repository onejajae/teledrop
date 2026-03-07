from fastapi import Request, status

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.bootstrap.container import DropUseCaseCollection
from app.core.config import Settings
from app.interfaces.web.presenters.common import drop_manage_page_url, templates
from app.interfaces.web.presenters.detail_panel import detail_panel_context


def _status_from_selected_drop(selected_drop) -> str | None:
    if selected_drop is None:
        return None
    if selected_drop.access_scope == "private":
        return "비공개"
    if selected_drop.requires_password:
        return "비밀번호 보호"
    return "공유 중"


async def shared_page_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    drop_use_cases: DropUseCaseCollection,
    settings: Settings,
    slug: str,
    password: str | None = None,
) -> dict:
    context = await detail_panel_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        selected_key=slug,
        selected_password=password,
    )
    selected_drop = context.get("selected_drop")
    context.update(
        {
            "active_nav": None,
            "auth_username": auth_data.username,
            "detail_mode": "shared",
            "selected_manage_page_url": drop_manage_page_url(slug, password),
            "show_owner_actions": False,
            "selected_can_copy_link": bool(
                selected_drop and selected_drop.access_scope == "public"
            ),
            "selected_status_label": _status_from_selected_drop(selected_drop),
            "show_shared_admin_bar": bool(auth_data.username and selected_drop),
            "locked_form_action": context.get("selected_page_preview_url"),
            "locked_form_use_hx": False,
            "locked_form_include_slug": False,
        }
    )
    return context


async def render_shared_page(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    drop_use_cases: DropUseCaseCollection,
    settings: Settings,
    slug: str,
    password: str | None = None,
    status_code: int = status.HTTP_200_OK,
):
    context = await shared_page_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        slug=slug,
        password=password,
    )
    return templates(settings).TemplateResponse(
        request=request,
        name="pages/shared_drop.html",
        context=context,
        status_code=status_code,
    )


__all__ = ["render_shared_page", "shared_page_context"]
