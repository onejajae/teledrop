from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from app.bootstrap.container import SettingsDep
from app.interfaces.api.deps import (
    CsrfTokenServiceDep,
    DropUseCasesDep,
    OptionalAuthDep,
)
from app.interfaces.web.presenters.auth_panel import render_auth_panel
from app.interfaces.web.presenters.dashboard import render_dashboard_page
from app.interfaces.web.presenters.detail_panel import render_detail_panel
from app.interfaces.web.presenters.drop_panel import render_drop_panel
from app.interfaces.web.presenters.upload_panel import render_upload_panel


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def ui(
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalAuthDep,
    csrf_service: CsrfTokenServiceDep,
    drop_use_cases: DropUseCasesDep,
    slug: str | None = Query(default=None),
    selected_password: str | None = Query(default=None),
    sortby: str | None = Query(default="created_at"),
    orderby: str | None = Query(default="desc"),
):
    return await render_dashboard_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        selected_key=slug,
        selected_password=selected_password,
        sortby=sortby,
        orderby=orderby,
    )


@router.get("/auth-panel", response_class=HTMLResponse)
async def ui_auth_panel(
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalAuthDep,
    csrf_service: CsrfTokenServiceDep,
):
    return render_auth_panel(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
    )


@router.get("/drop-panel", response_class=HTMLResponse)
async def ui_drop_panel(
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalAuthDep,
    csrf_service: CsrfTokenServiceDep,
    drop_use_cases: DropUseCasesDep,
    slug: str | None = Query(default=None),
    sortby: str | None = Query(default="created_at"),
    orderby: str | None = Query(default="desc"),
):
    return await render_drop_panel(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        selected_key=slug,
        sortby=sortby,
        orderby=orderby,
    )


@router.get("/upload-panel", response_class=HTMLResponse)
async def ui_upload_panel(
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalAuthDep,
    csrf_service: CsrfTokenServiceDep,
    slug: str | None = Query(default=None),
):
    return render_upload_panel(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        selected_key=slug,
    )


@router.get("/drop-detail", response_class=HTMLResponse)
async def ui_drop_detail(
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalAuthDep,
    csrf_service: CsrfTokenServiceDep,
    drop_use_cases: DropUseCasesDep,
    slug: str | None = Query(default=None),
    password: str | None = Query(default=None),
):
    return await render_detail_panel(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        selected_key=slug,
        selected_password=password,
    )


@router.get("/{slug}", response_class=HTMLResponse)
async def ui_preview(
    request: Request,
    slug: str,
    settings: SettingsDep,
    auth_data: OptionalAuthDep,
    csrf_service: CsrfTokenServiceDep,
    drop_use_cases: DropUseCasesDep,
    password: str | None = Query(default=None),
    sortby: str | None = Query(default="created_at"),
    orderby: str | None = Query(default="desc"),
):
    return await render_dashboard_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        selected_key=slug,
        selected_password=password,
        sortby=sortby,
        orderby=orderby,
    )
