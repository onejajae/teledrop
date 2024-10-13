import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from sqlmodel import Session

from api.db.core import engine
from api.db.model import User
from api.config import Settings, get_settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep: Session = Depends(get_session)
TokenDep: str = Depends(oauth2_scheme)
SettingsDep: Settings = Depends(get_settings)


async def get_current_user(
    token: str = TokenDep,
    session: Session = SessionDep,
    settings: Settings = SettingsDep,
) -> User:
    if token is None:
        return None

    try:
        payload = jwt.decode(
            token, key=settings.JWT_SECRET, algorithms=settings.JWT_ALGORITHM
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    user = session.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


CurrentUser: User = Depends(get_current_user)
