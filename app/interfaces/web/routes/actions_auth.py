from fastapi import APIRouter, Form, Request, Response, status
from fastapi.responses import RedirectResponse

from app.application.auth.models import PasswordLoginCommand
from app.bootstrap.container import SettingsDep
from app.core.auth import clear_session_cookie, get_session_id_from_request, set_session_cookie
from app.domain.auth.errors import LoginInvalid
from app.application.auth.types import AuthIdentity
from app.interfaces.api.deps import (
    CsrfTokenServiceDep,
    OptionalAuthDep,
    PasswordLoginUseCaseDep,
    RevokeSessionUseCaseDep,
)
from app.interfaces.web.action_support import is_hx_request, redirect_home
from app.interfaces.web.presenters.auth_panel import render_auth_panel


router = APIRouter(prefix="/actions/auth")


@router.post("/login")
async def ui_login(
    request: Request,
    settings: SettingsDep,
    password_login_use_case: PasswordLoginUseCaseDep,
    csrf_service: CsrfTokenServiceDep,
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
    settings: SettingsDep,
    _auth_data: OptionalAuthDep,
    csrf_service: CsrfTokenServiceDep,
    revoke_session_use_case: RevokeSessionUseCaseDep,
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
