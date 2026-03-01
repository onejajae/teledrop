from fastapi import APIRouter, Form, Request, Response

from app.application.auth.models import PasswordLoginCommand
from app.bootstrap.container import SettingsDep
from app.core.auth import clear_session_cookie, get_session_id_from_request, set_session_cookie
from app.domain.auth.errors import LoginInvalid
from app.interfaces.api.errors import login_invalid_exception
from app.interfaces.api.deps import (
    AuthDep,
    OptionalAuthDep,
    PasswordLoginUseCaseDep,
    RevokeSessionUseCaseDep,
)


router = APIRouter(tags=["Auth"])


@router.post("/login")
async def login(
    response: Response,
    settings: SettingsDep,
    password_login_use_case: PasswordLoginUseCaseDep,
    username: str = Form(),
    password: str = Form(),
):
    try:
        auth_session = await password_login_use_case.execute(
            PasswordLoginCommand(
                username=username,
                password=password,
            )
        )
    except LoginInvalid:
        raise login_invalid_exception()
    set_session_cookie(response, settings, auth_session.sid)


@router.get("/me")
async def get_user_info(
    auth_data: AuthDep,
):
    return auth_data.username


@router.get("/logout")
async def logout(
    request: Request,
    response: Response,
    settings: SettingsDep,
    _auth_data: OptionalAuthDep,
    revoke_session_use_case: RevokeSessionUseCaseDep,
):
    session_id = get_session_id_from_request(request, settings)
    if session_id:
        await revoke_session_use_case.execute(session_id)
    clear_session_cookie(response, settings)


@router.post("/logout")
async def logout_post(
    request: Request,
    response: Response,
    settings: SettingsDep,
    _auth_data: OptionalAuthDep,
    revoke_session_use_case: RevokeSessionUseCaseDep,
):
    session_id = get_session_id_from_request(request, settings)
    if session_id:
        await revoke_session_use_case.execute(session_id)
    clear_session_cookie(response, settings)
