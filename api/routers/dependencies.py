from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from sqlmodel import Session

from api.db.core import get_session
from api.config import Settings, get_settings

from api.services.content_service import ContentService
from api.services.auth_service import AuthService
from api.repositories.content_repository import SQLAlchemyContentRepository

from api.exceptions import TokenExpired, TokenInvalid


def get_auth_service(settings: Settings = Depends(get_settings)) -> AuthService:
    return AuthService(settings=settings)


def get_content_service(
    db: Session = Depends(get_session), settings: Settings = Depends(get_settings)
) -> ContentService:
    return ContentService(
        content_repository=SQLAlchemyContentRepository(db), settings=settings
    )


# def authenticate(
#     token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/auth/login")),
#     auth_service: AuthService = Depends(get_auth_service),
#     settings: Settings = Depends(get_settings),
# ):
#     try:
#         payload = auth_service.verify_token(token)
#     except TokenExpired:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             headers={"WWW-Authenticate": "Bearer"},
#             detail="Token has been expired or revoked",
#         )
#     except TokenInvalid:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             headers={"WWW-Authenticate": "Bearer"},
#             detail="Invalid Token",
#         )

#     if payload.username != settings.WEB_USERNAME:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


# def authenticate_optional(
#     token: str = Depends(
#         OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
#     ),
#     auth_service: AuthService = Depends(get_auth_service),
#     settings: Settings = Depends(get_settings),
# ):
#     if token is None:
#         return None

#     try:
#         payload = auth_service.verify_token(token)
#     except TokenExpired:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             headers={"WWW-Authenticate": "Bearer"},
#             detail="Token has been expired or revoked",
#         )
#     except TokenInvalid:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             headers={"WWW-Authenticate": "Bearer"},
#             detail="Invalid Token",
#         )

#     if payload.username != settings.WEB_USERNAME:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

#     return payload.username


from api.security import OAuth2PasswordBearerWithCookie
from fastapi.security import OAuth2PasswordBearer

from sqlmodel import Session

from api.db.core import get_session
from api.config import Settings, get_settings
from api.exceptions import TokenExpired, TokenInvalid


def validate_token(token: str, auth_service: AuthService, settings: Settings):
    try:
        payload = auth_service.verify_token(token)
    except TokenExpired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
            detail="Token has been expired or revoked",
        )
    except TokenInvalid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
            detail="Invalid Token",
        )

    if payload.username != settings.WEB_USERNAME:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return payload


class Authenticator:
    def __init__(self, auto_error: bool = True, web_only: bool = False):
        self.auto_error = auto_error
        self.web_only = web_only

    def __call__(
        self,
        access_token: str = Depends(
            OAuth2PasswordBearerWithCookie(
                name="access_token", tokenUrl="/api/auth/login", auto_error=False
            )
        ),
        auth_service: AuthService = Depends(get_auth_service),
        settings: Settings = Depends(get_settings),
    ):
        if access_token:
            payload = validate_token(
                token=access_token, auth_service=auth_service, settings=settings
            )

            return payload.username

        if self.auto_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided or are invalid.",
            )

        return None
