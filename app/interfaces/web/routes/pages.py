from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from app.bootstrap.container import SettingsDep
from app.interfaces.web.deps import (
    CsrfTokenServiceDep,
    DropUseCasesDep,
    ListApiKeysUseCaseDep,
    OptionalSessionAuthDep,
)
from app.interfaces.web.presenters.api_keys_page import render_api_keys_page
from app.interfaces.web.presenters.auth_panel import render_auth_panel
from app.interfaces.web.presenters.home_page import render_home_page
from app.interfaces.web.presenters.library_page import render_library_page
from app.interfaces.web.presenters.manage_page import render_manage_page
from app.interfaces.web.presenters.common import unauthorized_ui_response
from app.interfaces.web.presenters.detail_panel import render_detail_panel
from app.interfaces.web.presenters.drop_panel import render_drop_panel
from app.interfaces.web.presenters.shared_page import render_shared_page
from app.interfaces.web.presenters.upload_panel import render_upload_panel


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def ui(
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalSessionAuthDep,
    csrf_service: CsrfTokenServiceDep,
):
    return render_home_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
    )


@router.get("/drops", response_class=HTMLResponse)
async def ui_library(
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalSessionAuthDep,
    csrf_service: CsrfTokenServiceDep,
    drop_use_cases: DropUseCasesDep,
    sortby: str | None = Query(default="created_at"),
    orderby: str | None = Query(default="desc"),
):
    if not auth_data.username:
        return unauthorized_ui_response(request)

    return await render_library_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        sortby=sortby,
        orderby=orderby,
    )


@router.get("/drops/{slug}", response_class=HTMLResponse)
async def ui_manage_drop(
    slug: str,
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalSessionAuthDep,
    csrf_service: CsrfTokenServiceDep,
    drop_use_cases: DropUseCasesDep,
    password: str | None = Query(default=None),
):
    if not auth_data.username:
        return unauthorized_ui_response(request)

    return await render_manage_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        slug=slug,
        password=password,
    )


@router.get("/auth-panel", response_class=HTMLResponse)
async def ui_auth_panel(
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalSessionAuthDep,
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
    auth_data: OptionalSessionAuthDep,
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
    auth_data: OptionalSessionAuthDep,
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
    auth_data: OptionalSessionAuthDep,
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


@router.get("/settings/api-keys", response_class=HTMLResponse)
async def ui_api_keys(
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalSessionAuthDep,
    csrf_service: CsrfTokenServiceDep,
    list_api_keys_use_case: ListApiKeysUseCaseDep,
):
    if not auth_data.username:
        return unauthorized_ui_response(request)

    return await render_api_keys_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        list_api_keys_use_case=list_api_keys_use_case,
        settings=settings,
    )


@router.get("/{slug}", response_class=HTMLResponse)
async def ui_preview(
    request: Request,
    slug: str,
    settings: SettingsDep,
    auth_data: OptionalSessionAuthDep,
    csrf_service: CsrfTokenServiceDep,
    drop_use_cases: DropUseCasesDep,
    password: str | None = Query(default=None),
):
    return await render_shared_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        slug=slug,
        password=password,
    )
