from fastapi import APIRouter, Depends, Form
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from bcrypt import hashpw, gensalt, checkpw
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from api.db.model import User
from api.schema import UserCreate, UserPublic, Token
from api.deps import SessionDep, CurrentUser, SettingsDep
from api.utils import create_access_token
from api.config import Settings


router = APIRouter()


@router.post("/register")
async def register(
    user: UserCreate = Form(),
    session: Session = SessionDep,
    settings: Settings = SettingsDep,
):
    if not settings.ALLOW_REGISTER:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

    if (
        settings.REGISTER_CODE is not None
        and settings.REGISTER_CODE != user.register_code
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    username = user.username
    password = user.password

    hashed_password = hashpw(password.encode("utf-8"), gensalt())
    hashed_password = hashed_password.decode("utf-8")

    new_user = User(username=username, password=hashed_password, created_at=datetime.now(timezone.utc))
    session.add(new_user)

    try:
        session.commit()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    session.refresh(new_user)

    return Token(
        access_token=create_access_token(
            user=new_user,
            settings=settings,
            expires_delta=timedelta(minutes=settings.JWT_EXP_MINUTES),
        ),
        token_type="Bearer",
        username=user.username,
    )


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = SessionDep,
    settings: Settings = SettingsDep,
) -> Token:
    username = form_data.username
    password = form_data.password

    statement = select(User).where(User.username == username)
    user = session.exec(statement).one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if not checkpw(password.encode("utf-8"), user.password.encode("utf-8")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return Token(
        access_token=create_access_token(
            user=user,
            settings=settings,
            expires_delta=timedelta(minutes=settings.JWT_EXP_MINUTES),
        ),
        token_type="Bearer",
        username=user.username,
    )


@router.post("/refresh")
async def refresh(user: User = CurrentUser, settings: Settings = SettingsDep) -> Token:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(
        access_token=create_access_token(
            user=user,
            settings=settings,
            expires_delta=timedelta(minutes=settings.JWT_EXP_MINUTES),
        ),
        token_type="Bearer",
        username=user.username,
    )


@router.get("/me", response_model=UserPublic)
async def get_user_info(user: User = CurrentUser, settings: Settings = SettingsDep):
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
