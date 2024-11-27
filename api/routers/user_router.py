from fastapi import APIRouter, Depends, Form
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from api.services.user_service import UserService
from api.schemas.user.service import UserServiceCreate, TokenPayload
from api.schemas.user.router import (
    UserCreateRequest,
    UserAccessTokenResponse,
    UserInfoResponse,
)
from api.routers.dependencies import get_user_service, get_current_user_id

from api.exceptions.user_exceptions import *


router = APIRouter()


@router.post("/register", response_model=UserAccessTokenResponse)
async def register(
    user_data: UserCreateRequest = Form(),
    user_service: UserService = Depends(get_user_service),
):
    try:
        user = user_service.create(UserServiceCreate(**user_data.model_dump()))
    except RegisterNotAllowedError as e:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
    except RegisterCodeNotMatchedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    except DuplicateUserError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    access_token = user_service.create_token(
        TokenPayload(user_id=user.id, username=user.username)
    )

    return UserAccessTokenResponse(
        access_token=access_token.token, username=user.username
    )


@router.post("/login", response_model=UserAccessTokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service),
):
    try:
        user = user_service.authenticate(
            username=form_data.username, password=form_data.password
        )
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except PasswordInvlaidError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    access_token = user_service.create_token(
        TokenPayload(user_id=user.id, username=user.username)
    )

    return UserAccessTokenResponse(
        access_token=access_token.token, username=user.username
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_user_info(
    user_id: int = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
):
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return user_service.get_by_id(user_id)


@router.post("/refresh", response_model=UserAccessTokenResponse)
async def refresh(
    user_id: int = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
):
    user = user_service.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = user_service.create_token(
        TokenPayload(user_id=user.id, username=user.username)
    )

    return UserAccessTokenResponse(
        access_token=access_token.token, username=user.username
    )
