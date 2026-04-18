from fastapi import Request, status

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.drop.models import DropListQuery
from app.application.drop.use_cases import ListDropsUseCase
from app.core.config import Settings
from app.domain.drop.errors import DropAccessDeniedError
from app.domain.drop.value_objects import DropSortField
from app.interfaces.web.presenters.common import (
    as_drop_vm,
    base_template_context,
    finalize_ui_response,
    drop_manage_page_url,
    normalize_sort_value,
    templates,
)


SORT_MAP = {
    "created_at": DropSortField.CREATED_AT,
    "title": DropSortField.TITLE,
    "size_bytes": DropSortField.SIZE_BYTES,
    "file_size": DropSortField.SIZE_BYTES,
}


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
    drops = []

    if auth_data.username:
        sort = SORT_MAP.get(normalize_sort_value(sortby), DropSortField.CREATED_AT)
        try:
            items = (
                await list_drops_use_case.execute(
                    DropListQuery(
                        page=1,
                        page_size=200,
                        sort=sort,
                        order=orderby or "desc",
                        auth=AuthIdentity(username=auth_data.username),
                    )
                )
            ).items
            drops = [as_drop_vm(item) for item in items]
        except DropAccessDeniedError:
            drops = []

    context = base_template_context(
        request=request,
        auth_data=auth_data,
        settings=settings,
        csrf_service=csrf_service,
        active_nav="drops",
        drops=drops,
        drop_sortby=normalize_sort_value(sortby),
        drop_orderby=orderby or "desc",
        drop_error_message=drop_error_message,
        drop_status_message=drop_status_message,
    )
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
    return finalize_ui_response(
        request,
        templates().TemplateResponse(
            request=request,
            name="pages/library.html",
            context=context,
            status_code=status_code,
        ),
        settings,
    )


__all__ = ["library_page_context", "render_library_page"]
