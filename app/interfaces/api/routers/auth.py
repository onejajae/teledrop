from fastapi import APIRouter, Depends, Form, Request, Response

from app.application.auth.models import PasswordLoginCommand
from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases import PasswordLoginUseCase, RevokeSessionUseCase
from app.bootstrap.container import get_app_settings
from app.bootstrap.providers.auth import (
    get_password_login_use_case,
    get_revoke_session_use_case,
)
from app.core.auth import clear_session_cookie, get_session_id_from_request, set_session_cookie
from app.core.config import Settings
from app.core.drop_grants import clear_drop_grant_cookies
from app.domain.auth.errors import LoginInvalid
from app.interfaces.api.deps.auth import get_required_api_auth
from app.interfaces.api.errors import login_invalid_exception
from app.interfaces.deps.auth import get_optional_session_auth


router = APIRouter(tags=["Auth"])


@router.post("/login")
async def login(
    response: Response,
    settings: Settings = Depends(get_app_settings),
    password_login_use_case: PasswordLoginUseCase = Depends(get_password_login_use_case),
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
    auth_data: AuthIdentity = Depends(get_required_api_auth),
):
    return auth_data.username


@router.get("/logout")
async def logout(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_app_settings),
    _auth_data: AuthIdentity = Depends(get_optional_session_auth),
    revoke_session_use_case: RevokeSessionUseCase = Depends(get_revoke_session_use_case),
):
    session_id = get_session_id_from_request(request, settings)
    if session_id:
        await revoke_session_use_case.execute(session_id)
    clear_session_cookie(response, settings)
    clear_drop_grant_cookies(response, request, settings)


@router.post("/logout")
async def logout_post(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_app_settings),
    _auth_data: AuthIdentity = Depends(get_optional_session_auth),
    revoke_session_use_case: RevokeSessionUseCase = Depends(get_revoke_session_use_case),
):
    session_id = get_session_id_from_request(request, settings)
    if session_id:
        await revoke_session_use_case.execute(session_id)
    clear_session_cookie(response, settings)
    clear_drop_grant_cookies(response, request, settings)
