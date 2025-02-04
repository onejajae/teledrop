from fastapi import Depends, HTTPException, status, Response

from sqlmodel import Session

from api.db.core import get_session
from api.config import Settings, get_settings

from api.security import OAuth2PasswordBearerWithCookie
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


class Authenticator:
    def __init__(self, auto_error: bool = True, web_only: bool = False):
        self.auto_error = auto_error
        self.web_only = web_only

    def __call__(
        self,
        response: Response,
        access_token: str = Depends(
            OAuth2PasswordBearerWithCookie(
                name="access_token", tokenUrl="/api/auth/login", auto_error=False
            )
        ),
        auth_service: AuthService = Depends(get_auth_service),
        settings: Settings = Depends(get_settings),
    ):
        if access_token:
            try:
                payload = auth_service.verify_token(access_token)
            except TokenExpired:
                response.delete_cookie("access_token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    headers={
                        "WWW-Authenticate": "Bearer",
                        "set-cookie": response.headers["set-cookie"],
                    },
                    detail="Token has been expired or revoked",
                )
            except TokenInvalid:
                response.delete_cookie("access_token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    headers={
                        "WWW-Authenticate": "Bearer",
                        "set-cookie": response.headers["set-cookie"],
                    },
                    detail="Invalid Token",
                )

            if payload.username != settings.WEB_USERNAME:
                response.delete_cookie("access_token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    headers={
                        "WWW-Authenticate": "Bearer",
                        "set-cookie": response.headers["set-cookie"],
                    },
                    detail="Invalid User",
                )

            return payload.username

        if self.auto_error:
            response.delete_cookie("access_token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={
                    "WWW-Authenticate": "Bearer",
                    "set-cookie": response.headers["set-cookie"],
                },
                detail="Authentication credentials were not provided or are invalid.",
            )

        return None
