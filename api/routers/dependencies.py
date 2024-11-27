from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from sqlmodel import Session

from api.db.core import get_session
from api.config import Settings, get_settings

from api.services.user_service import UserService
from api.repositories.user_repository import SQLAlchemyUserRepository

from api.services.post_service import PostService
from api.repositories.post_repository import SQLAlchemyPostRepository

from api.exceptions.user_exceptions import TokenExpiredError, TokenInvalidError


def get_user_service(
    db: Session = Depends(get_session), settings: Settings = Depends(get_settings)
) -> UserService:
    return UserService(user_repository=SQLAlchemyUserRepository(db), settings=settings)


def get_current_user_id(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)),
    user_service: UserService = Depends(get_user_service),
) -> int:
    if token is None:
        return None

    try:
        payload = user_service.verify_token(token)
    except TokenExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
            detail="Token has been expired or revoked",
        )
    except TokenInvalidError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
            detail="Invalid Token",
        )

    return payload.user_id


def get_post_service(
    db: Session = Depends(get_session), settings: Settings = Depends(get_settings)
) -> PostService:
    return PostService(post_repository=SQLAlchemyPostRepository(db), settings=settings)
