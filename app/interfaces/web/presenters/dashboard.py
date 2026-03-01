from fastapi import Request, status

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.bootstrap.container import DropUseCaseCollection
from app.core.config import Settings
from app.interfaces.web.presenters.auth_panel import auth_panel_context
from app.interfaces.web.presenters.common import templates
from app.interfaces.web.presenters.detail_panel import detail_panel_context
from app.interfaces.web.presenters.drop_panel import drop_panel_context


PANEL_SHARED_CONTEXT_KEYS = frozenset({"request", "is_login", "csrf_token", "selected_key"})


def merge_panel_contexts(*contexts: dict) -> dict:
    merged: dict = {}
    for context in contexts:
        for key, value in context.items():
            if key in merged and key not in PANEL_SHARED_CONTEXT_KEYS:
                raise ValueError(f"Duplicate non-shared dashboard context key: {key}")
            merged[key] = value
    return merged


async def dashboard_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    drop_use_cases: DropUseCaseCollection,
    settings: Settings,
    selected_key: str | None,
    selected_password: str | None,
    sortby: str | None,
    orderby: str | None,
) -> dict:
    auth_context = auth_panel_context(
        request,
        auth_data,
        csrf_service,
        settings,
    )
    drop_context = await drop_panel_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        selected_key=selected_key,
        sortby=sortby,
        orderby=orderby,
    )
    detail_context = await detail_panel_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        selected_key=selected_key,
        selected_password=selected_password,
    )
    return merge_panel_contexts(auth_context, drop_context, detail_context)


async def render_dashboard_page(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    drop_use_cases: DropUseCaseCollection,
    settings: Settings,
    status_code: int = status.HTTP_200_OK,
    selected_key: str | None = None,
    selected_password: str | None = None,
    sortby: str | None = None,
    orderby: str | None = None,
):
    context = await dashboard_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        selected_key=selected_key,
        selected_password=selected_password,
        sortby=sortby,
        orderby=orderby,
    )
    return templates(settings).TemplateResponse(
        request=request,
        name="pages/dashboard.html",
        context=context,
        status_code=status_code,
    )


__all__ = [
    "dashboard_context",
    "merge_panel_contexts",
    "render_dashboard_page",
]
