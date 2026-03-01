from fastapi import Request, status

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.drop.models import DropListQuery
from app.bootstrap.container import DropUseCaseCollection
from app.core.config import Settings
from app.domain.drop.errors import DropAccessDeniedError
from app.domain.drop.value_objects import DropSortField
from app.interfaces.web.presenters.common import (
    as_template_drop,
    drop_preview_page_url,
    csrf_token_for_request,
    normalize_sort_value,
    templates,
)


SORT_MAP = {
    "created_at": DropSortField.CREATED_AT,
    "title": DropSortField.TITLE,
    "size_bytes": DropSortField.SIZE_BYTES,
    "file_size": DropSortField.SIZE_BYTES,
}


async def drop_panel_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    drop_use_cases: DropUseCaseCollection,
    settings: Settings,
    selected_key: str | None = None,
    sortby: str | None = "created_at",
    orderby: str | None = "desc",
    drop_error_message: str | None = None,
    drop_status_message: str | None = None,
) -> dict:
    drops = []
    drop_preview_urls: dict[str, str] = {}

    if auth_data.username:
        sort = SORT_MAP.get(normalize_sort_value(sortby), DropSortField.CREATED_AT)
        try:
            items = (
                await drop_use_cases.list_drops_use_case.execute(
                    DropListQuery(
                        page=1,
                        page_size=200,
                        sort=sort,
                        order=orderby or "desc",
                        auth=AuthIdentity(username=auth_data.username),
                    )
                )
            ).items
            drops = [as_template_drop(item) for item in items]
            drop_preview_urls = {
                item.slug: drop_preview_page_url(item.slug, None) for item in drops
            }
        except DropAccessDeniedError:
            drops = []

    return {
        "request": request,
        "is_login": bool(auth_data.username),
        "drops": drops,
        "drop_preview_urls": drop_preview_urls,
        "selected_key": selected_key,
        "drop_sortby": normalize_sort_value(sortby),
        "drop_orderby": orderby or "desc",
        "csrf_token": csrf_token_for_request(request, settings, csrf_service),
        "drop_error_message": drop_error_message,
        "drop_status_message": drop_status_message,
    }


async def render_drop_panel(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    drop_use_cases: DropUseCaseCollection,
    settings: Settings,
    status_code: int = status.HTTP_200_OK,
    selected_key: str | None = None,
    sortby: str | None = "created_at",
    orderby: str | None = "desc",
    drop_error_message: str | None = None,
    drop_status_message: str | None = None,
):
    context = await drop_panel_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        selected_key=selected_key,
        sortby=sortby,
        orderby=orderby,
        drop_error_message=drop_error_message,
        drop_status_message=drop_status_message,
    )
    return templates(settings).TemplateResponse(
        request=request,
        name="panels/drop.html",
        context=context,
        status_code=status_code,
    )
