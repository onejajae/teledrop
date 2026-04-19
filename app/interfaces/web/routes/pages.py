from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases import CsrfTokenService, ListApiKeysUseCase
from app.application.drop.use_cases import GetDropMetaUseCase, ListDropsUseCase
from app.bootstrap.container import get_app_settings, get_csrf_token_service
from app.bootstrap.providers.auth import get_list_api_keys_use_case
from app.bootstrap.providers.drop import get_get_drop_meta_use_case, get_list_drops_use_case
from app.core.config import Settings
from app.interfaces.deps.auth import get_optional_session_auth
from app.interfaces.web.presenters.api_keys_page import render_api_keys_page
from app.interfaces.web.presenters.component_catalog import render_component_catalog_page
from app.interfaces.web.presenters.home_page import render_home_page
from app.interfaces.web.presenters.library_page import render_library_page
from app.interfaces.web.presenters.manage_page import render_manage_page
from app.interfaces.web.presenters.common import unauthorized_ui_response
from app.interfaces.web.presenters.shared_page import render_shared_page


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def ui(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    auth_error: str | None = Query(default=None),
):
    return render_home_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        auth_error_code=auth_error,
    )


@router.get("/drops", response_class=HTMLResponse)
async def ui_library(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    list_drops_use_case: ListDropsUseCase = Depends(get_list_drops_use_case),
    sortby: str | None = Query(default="created_at"),
    orderby: str | None = Query(default="desc"),
):
    if not auth_data.is_authenticated:
        return unauthorized_ui_response(request, settings)

    return await render_library_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        list_drops_use_case=list_drops_use_case,
        settings=settings,
        sortby=sortby,
        orderby=orderby,
    )


@router.get("/drops/{slug}", response_class=HTMLResponse)
async def ui_manage_drop(
    slug: str,
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    get_drop_meta_use_case: GetDropMetaUseCase = Depends(get_get_drop_meta_use_case),
):
    if not auth_data.is_authenticated:
        return unauthorized_ui_response(request, settings)

    return await render_manage_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        slug=slug,
    )


@router.get("/settings/api-keys", response_class=HTMLResponse)
async def ui_api_keys(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    list_api_keys_use_case: ListApiKeysUseCase = Depends(get_list_api_keys_use_case),
):
    if not auth_data.is_authenticated:
        return unauthorized_ui_response(request, settings)

    return await render_api_keys_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        list_api_keys_use_case=list_api_keys_use_case,
        settings=settings,
    )


@router.get("/dev/components", response_class=HTMLResponse)
async def ui_component_catalog(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
):
    return render_component_catalog_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
    )


@router.get("/{slug}", response_class=HTMLResponse)
async def ui_preview(
    request: Request,
    slug: str,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    get_drop_meta_use_case: GetDropMetaUseCase = Depends(get_get_drop_meta_use_case),
):
    return await render_shared_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        slug=slug,
    )
