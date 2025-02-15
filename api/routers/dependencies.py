from fastapi import Depends, Response, Security
from fastapi import HTTPException, status
from fastapi.security import APIKeyHeader

from sqlmodel import Session

from api.db.core import get_session
from api.config import Settings, get_settings

from api.models import AuthData, ContentRead
from api.exceptions import *
from api.services import AuthService, ContentService, APIKeyService
from api.repositories import SQLAlchemyContentRepository, SQLAlchemyAPIKeyRepository
from api.security import OAuth2PasswordBearerWithCookie


def get_auth_service(settings: Settings = Depends(get_settings)) -> AuthService:
    return AuthService(settings=settings)


def get_content_service(
    db: Session = Depends(get_session), settings: Settings = Depends(get_settings)
) -> ContentService:
    return ContentService(
        content_repository=SQLAlchemyContentRepository(db), settings=settings
    )


def get_api_key_service(
    db: Session = Depends(get_session), settings: Settings = Depends(get_settings)
) -> APIKeyService:
    return APIKeyService(
        api_key_repository=SQLAlchemyAPIKeyRepository(db), settings=settings
    )


class AccessTokenAuthenticator:
    def __call__(
        self,
        response: Response,
        access_token: str = Depends(
            OAuth2PasswordBearerWithCookie(
                name="access_token", tokenUrl="/api/auth/login", auto_error=False
            )
        ),
        auth_service: AuthService = Depends(get_auth_service),
    ) -> AuthData | None:
        if not access_token:
            return None

        try:
            payload = auth_service.verify_token(access_token)
            return AuthData(
                username=payload.username,
                read_permission=True,
                write_permission=True,
            )
        except TokenExpired:
            raise self.__handle_auth_error(
                response=response,
                detail="Token has been expired or revoked",
            )

        except TokenInvalid:
            raise self.__handle_auth_error(
                response=response,
                detail="Invalid Token",
            )

    def __handle_auth_error(self, response: Response, detail: str):
        response.delete_cookie("access_token")
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={
                "WWW-Authenticate": "Bearer",
                "set-cookie": response.headers["set-cookie"],
            },
            detail=detail,
        )


class ApiKeyAuthenticator:
    def __call__(
        self,
        api_key: str = Security(APIKeyHeader(name="X-API-KEY", auto_error=False)),
        api_key_service: APIKeyService = Depends(get_api_key_service),
        settings: Settings = Depends(get_settings),
    ) -> AuthData | None:
        if not api_key:
            return None

        try:
            api_key_data = api_key_service.get_by_key(api_key)
        except APIKeyNotExist:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        if not api_key_data.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API Key is not available now",
            )
        else:
            return AuthData(
                username=settings.WEB_USERNAME,
                read_permission=api_key_data.read_permission,
                write_permission=api_key_data.write_permission,
            )


class Authenticator:
    def __init__(self, auto_error: bool = True, web_only: bool = False):
        self.auto_error = auto_error
        self.web_only = web_only

    def __call__(
        self,
        token_auth_data: AuthData | None = Depends(AccessTokenAuthenticator()),
        api_key_auth_data: AuthData | None = Depends(ApiKeyAuthenticator()),
    ) -> AuthData:
        if token_auth_data and api_key_auth_data:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail="Provide either access token or API key, not both.",
            )

        if self.web_only and api_key_auth_data:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail="API key authentication is not allowed for web access.",
            )

        if token_auth_data:
            return token_auth_data

        if api_key_auth_data:
            return api_key_auth_data

        if self.auto_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided or are invalid.",
            )

        return None


class PermissionChecker:
    def __init__(
        self,
        read_required: bool = False,
        write_required: bool = False,
        auto_error: bool = True,
    ):
        self.read_required = read_required
        self.write_required = write_required
        self.auto_error = auto_error

    def __call__(
        self, auth_data: AuthData | None = Depends(Authenticator(auto_error=False))
    ):
        if auth_data is None:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication credential is required.",
                )
            else:
                return None

        if self.read_required and not auth_data.read_permission:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Read permission is required.",
            )

        if self.write_required and not auth_data.write_permission:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Write permission is required.",
            )

        return True


class ContentAccessChecker:
    def __call__(
        self,
        key: str,
        password: str | None = None,
        auth_data: AuthData | None = Depends(Authenticator(auto_error=False)),
        content_service: ContentService = Depends(get_content_service),
    ) -> ContentRead:
        try:
            content = content_service.check_access_permission_by_key(
                key=key, auth_data=auth_data
            )
        except (ContentNotExist, ContentNeedLogin):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        try:
            content = content_service.get_by_key(key=key, password=password)
        except ContentNotExist:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        except ContentPasswordInvalid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        return content
