from fastapi import Request, status

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.drop.use_cases import ListDropsUseCase
from app.core.config import Settings
from app.interfaces.web.presenters.common import drop_manage_page_url, templates
from app.interfaces.web.presenters.drop_panel import drop_panel_context


async def library_page_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    list_drops_use_case: ListDropsUseCase,
    settings: Settings,
    sortby: str | None = "created_at",
    orderby: str | None = "desc",
    drop_error_message: str | None = None,
    drop_status_message: str | None = None,
) -> dict:
    context = await drop_panel_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        list_drops_use_case=list_drops_use_case,
        settings=settings,
        sortby=sortby,
        orderby=orderby,
        drop_error_message=drop_error_message,
        drop_status_message=drop_status_message,
    )
    context["active_nav"] = "drops"
    context["auth_username"] = auth_data.username
    context["drop_manage_urls"] = {
        item.slug: drop_manage_page_url(item.slug) for item in context["drops"]
    }
    return context


async def render_library_page(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    list_drops_use_case: ListDropsUseCase,
    settings: Settings,
    status_code: int = status.HTTP_200_OK,
    sortby: str | None = "created_at",
    orderby: str | None = "desc",
    drop_error_message: str | None = None,
    drop_status_message: str | None = None,
):
    context = await library_page_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        list_drops_use_case=list_drops_use_case,
        settings=settings,
        sortby=sortby,
        orderby=orderby,
        drop_error_message=drop_error_message,
        drop_status_message=drop_status_message,
    )
    return templates().TemplateResponse(
        request=request,
        name="pages/library.html",
        context=context,
        status_code=status_code,
    )


__all__ = ["library_page_context", "render_library_page"]
