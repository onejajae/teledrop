from fastapi import APIRouter, Depends
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from sqlalchemy.orm import Session
from db.core import get_db

from .service import *

from .schema import UserCreate, AccessToken

from config import Settings, get_settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login/", auto_error=False)


@router.post("/register/", response_model=AccessToken)
async def register(
    user_in: UserCreate = Depends(),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if settings.register_code and settings.register_code != user_in.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    if is_user_exist(user_in.username, db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    return AccessToken(
        access_token=create_user(user_in.username, user_in.password, db, settings),
        username=user_in.username,
    )


@router.post("/login/", response_model=AccessToken)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not is_user_exist(form_data.username, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if not authenticate_user(form_data.username, form_data.password, db):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return AccessToken(
        access_token=generate_token(username=form_data.username, settings=settings),
        username=form_data.username,
    )


async def get_current_user(
    access_token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not access_token:
        return None

    try:
        payload = validate_access_token(access_token, settings)
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("username")
    user = get_user(username, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.get("/refresh/", response_model=AccessToken)
async def refresh(
    current_user: str = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    if settings.need_login:
        if current_user is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        else:
            return AccessToken(
                access_token=generate_token(
                    username=current_user.username, settings=settings
                ),
                username=current_user.username,
            )
    else:
        if current_user is None:
            return AccessToken(
                access_token="",
                username="",
            )
        else:
            return AccessToken(
                access_token=generate_token(
                    username=current_user.username, settings=settings
                ),
                username=current_user.username,
            )
