from fastapi import APIRouter, Depends, Response
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from api.models import TokenPayload, AuthData
from api.exceptions import LoginInvalid
from api.services import AuthService

from .dependencies import get_auth_service, Authenticator


router = APIRouter()


@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        auth_service.authenticate(
            username=form_data.username, password=form_data.password
        )
    except LoginInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    token = auth_service.create_token(TokenPayload(username=form_data.username))
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token.access_token}",
        httponly=True,
        samesite="strict",
    )


@router.get("/me")
async def get_user_info(
    response: Response,
    auth_data: AuthData = Depends(Authenticator(web_only=True)),
    auth_service: AuthService = Depends(get_auth_service),
):
    token = auth_service.create_token(TokenPayload(username=auth_data.username))
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token.access_token}",
        httponly=True,
        samesite="strict",
    )

    return auth_data.username


@router.get("/logout")
async def logout(
    response: Response,
    auth_data: AuthData = Depends(Authenticator(auto_error=False, web_only=True)),
):
    response.delete_cookie(key="access_token")
