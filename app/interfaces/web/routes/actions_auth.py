from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import RedirectResponse

from app.application.auth.models import (
    CreateApiKeyCommand,
    DeleteApiKeyCommand,
    PasswordLoginCommand,
    RevokeApiKeyCommand,
)
from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases import (
    CsrfTokenService,
    CreateApiKeyUseCase,
    DeleteApiKeyUseCase,
    ListApiKeysUseCase,
    PasswordLoginUseCase,
    RevokeApiKeyUseCase,
    RevokeSessionUseCase,
)
from app.bootstrap.container import get_app_settings, get_csrf_token_service
from app.bootstrap.providers.auth import (
    get_create_api_key_use_case,
    get_delete_api_key_use_case,
    get_list_api_keys_use_case,
    get_password_login_use_case,
    get_revoke_api_key_use_case,
    get_revoke_session_use_case,
)
from app.core.auth import clear_session_cookie, get_session_id_from_request, set_session_cookie
from app.core.config import Settings
from app.domain.auth.errors import ApiKeyNotFound, LoginInvalid
from app.interfaces.deps.auth import get_optional_session_auth
from app.interfaces.web.action_support import (
    is_hx_request,
    redirect_home,
    require_auth_and_csrf,
)
from app.interfaces.web.presenters.api_keys_page import render_api_keys_page
from app.interfaces.web.presenters.auth_panel import render_auth_panel


router = APIRouter(prefix="/actions/auth")


@router.post("/login")
async def ui_login(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    password_login_use_case: PasswordLoginUseCase = Depends(get_password_login_use_case),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    username: str = Form(),
    password: str = Form(),
):
    try:
        auth_session = await password_login_use_case.execute(
            PasswordLoginCommand(username=username, password=password)
        )
    except LoginInvalid:
        if is_hx_request(request):
            return render_auth_panel(
                request=request,
                auth_data=AuthIdentity(username=None),
                csrf_service=csrf_service,
                settings=settings,
                status_code=status.HTTP_401_UNAUTHORIZED,
                auth_error_message="아이디 또는 비밀번호가 올바르지 않습니다.",
            )
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    if is_hx_request(request):
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        response.headers["HX-Redirect"] = "/"
    else:
        response = redirect_home()

    set_session_cookie(response, settings, auth_session.sid)
    return response


@router.post("/logout")
async def ui_logout(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    _auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    revoke_session_use_case: RevokeSessionUseCase = Depends(get_revoke_session_use_case),
    csrf_token: str = Form(default=""),
):
    session_id = get_session_id_from_request(request, settings)
    if session_id and not csrf_service.verify(session_id, csrf_token):
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    if session_id:
        await revoke_session_use_case.execute(session_id)

    if is_hx_request(request):
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        response.headers["HX-Redirect"] = "/"
        clear_session_cookie(response, settings)
        return response

    response = redirect_home()
    clear_session_cookie(response, settings)
    return response


async def _api_key_guard(
    *,
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    csrf_token: str,
    list_api_keys_use_case: ListApiKeysUseCase,
):
    async def on_csrf_failure() -> Response:
        return await render_api_keys_page(
            request=request,
            auth_data=auth_data,
            csrf_service=csrf_service,
            list_api_keys_use_case=list_api_keys_use_case,
            settings=settings,
            status_code=status.HTTP_403_FORBIDDEN,
            error_message="유효하지 않은 CSRF 토큰입니다.",
        )

    return await require_auth_and_csrf(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        csrf_token=csrf_token,
        on_csrf_failure=on_csrf_failure,
    )


@router.post("/api-keys/create")
async def ui_create_api_key(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    create_api_key_use_case: CreateApiKeyUseCase = Depends(get_create_api_key_use_case),
    list_api_keys_use_case: ListApiKeysUseCase = Depends(get_list_api_keys_use_case),
    name: str = Form(),
    expires_at: str = Form(default=""),
    csrf_token: str = Form(default=""),
):
    guard_response = await _api_key_guard(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        csrf_token=csrf_token,
        list_api_keys_use_case=list_api_keys_use_case,
    )
    if guard_response is not None:
        return guard_response

    parsed_expires_at: datetime | None = None
    expires_at_value = (expires_at or "").strip()
    if expires_at_value:
        try:
            parsed_expires_at = datetime.fromisoformat(expires_at_value)
        except ValueError:
            return await render_api_keys_page(
                request=request,
                auth_data=auth_data,
                csrf_service=csrf_service,
                list_api_keys_use_case=list_api_keys_use_case,
                settings=settings,
                status_code=status.HTTP_400_BAD_REQUEST,
                error_message="만료 시각 형식이 올바르지 않습니다.",
            )

    try:
        created = await create_api_key_use_case.execute(
            CreateApiKeyCommand(
                name=name,
                created_by_username=auth_data.username or "",
                expires_at=parsed_expires_at,
            )
        )
    except ValueError as exc:
        return await render_api_keys_page(
            request=request,
            auth_data=auth_data,
            csrf_service=csrf_service,
            list_api_keys_use_case=list_api_keys_use_case,
            settings=settings,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_message=str(exc),
        )

    return await render_api_keys_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        list_api_keys_use_case=list_api_keys_use_case,
        settings=settings,
        status_message="API key가 생성되었습니다. 지금 복사해 주세요.",
        created_api_key=created,
    )


@router.post("/api-keys/{public_id}/revoke")
async def ui_revoke_api_key(
    public_id: str,
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    list_api_keys_use_case: ListApiKeysUseCase = Depends(get_list_api_keys_use_case),
    revoke_api_key_use_case: RevokeApiKeyUseCase = Depends(get_revoke_api_key_use_case),
    csrf_token: str = Form(default=""),
):
    guard_response = await _api_key_guard(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        csrf_token=csrf_token,
        list_api_keys_use_case=list_api_keys_use_case,
    )
    if guard_response is not None:
        return guard_response

    try:
        await revoke_api_key_use_case.execute(RevokeApiKeyCommand(public_id=public_id))
    except ApiKeyNotFound:
        return await render_api_keys_page(
            request=request,
            auth_data=auth_data,
            csrf_service=csrf_service,
            list_api_keys_use_case=list_api_keys_use_case,
            settings=settings,
            status_code=status.HTTP_404_NOT_FOUND,
            error_message="존재하지 않는 API key 입니다.",
        )

    return await render_api_keys_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        list_api_keys_use_case=list_api_keys_use_case,
        settings=settings,
        status_message="API key가 폐기되었습니다.",
    )


@router.post("/api-keys/{public_id}/delete")
async def ui_delete_api_key(
    public_id: str,
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    list_api_keys_use_case: ListApiKeysUseCase = Depends(get_list_api_keys_use_case),
    delete_api_key_use_case: DeleteApiKeyUseCase = Depends(get_delete_api_key_use_case),
    csrf_token: str = Form(default=""),
):
    guard_response = await _api_key_guard(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        csrf_token=csrf_token,
        list_api_keys_use_case=list_api_keys_use_case,
    )
    if guard_response is not None:
        return guard_response

    try:
        await delete_api_key_use_case.execute(DeleteApiKeyCommand(public_id=public_id))
    except ApiKeyNotFound:
        return await render_api_keys_page(
            request=request,
            auth_data=auth_data,
            csrf_service=csrf_service,
            list_api_keys_use_case=list_api_keys_use_case,
            settings=settings,
            status_code=status.HTTP_404_NOT_FOUND,
            error_message="존재하지 않는 API key 입니다.",
        )

    return await render_api_keys_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        list_api_keys_use_case=list_api_keys_use_case,
        settings=settings,
        status_message="API key가 삭제되었습니다.",
    )
