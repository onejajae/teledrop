from fastapi import APIRouter, Depends
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from api.models import TokenPayload, AccessToken

from api.services.auth_service import AuthService

from api.routers.dependencies import get_auth_service
from api.routers.dependencies import get_auth_service, authenticate

from api.exceptions import LoginInvalid


router = APIRouter()


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
) -> AccessToken:
    try:
        auth_service.authenticate(
            username=form_data.username, password=form_data.password
        )
    except LoginInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return auth_service.create_token(TokenPayload(username=form_data.username))


@router.get("/me", dependencies=[Depends(authenticate)])
async def get_user_info(
    auth_service: AuthService = Depends(get_auth_service),
):
    return
