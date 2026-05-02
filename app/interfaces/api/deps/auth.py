from fastapi import Depends, Request, Response

from app.application.auth.models import VerifyApiKeyQuery
from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases import VerifyApiKeyUseCase, VerifySessionUseCase
from app.bootstrap.container import get_app_settings
from app.bootstrap.providers.auth import (
    get_verify_api_key_use_case,
    get_verify_session_use_case,
)
from app.core.auth import clear_session_cookie
from app.core.config import Settings
from app.domain.auth.errors import ApiKeyInvalid
from app.interfaces.api.errors import (
    api_auth_unauthorized_exception,
    response_set_cookie_header,
)
from app.interfaces.deps.auth import (
    authenticate_with_session,
    extract_api_key,
    session_cookie_clear_pending,
)

def _clear_stale_session_cookie_if_needed(
    request: Request,
    response: Response,
    settings: Settings,
):
    if session_cookie_clear_pending(request):
        clear_session_cookie(response, settings)


class SessionOrApiKeyAuthenticator:
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(
        self,
        request: Request,
        response: Response,
        settings: Settings = Depends(get_app_settings),
        verify_session_use_case: VerifySessionUseCase = Depends(get_verify_session_use_case),
        verify_api_key_use_case: VerifyApiKeyUseCase = Depends(get_verify_api_key_use_case),
    ) -> AuthIdentity:
        identity = await authenticate_with_session(
            request=request,
            settings=settings,
            verify_session_use_case=verify_session_use_case,
        )
        _clear_stale_session_cookie_if_needed(request, response, settings)
        if identity.is_authenticated:
            return identity

        api_key = extract_api_key(request)
        if api_key:
            try:
                return await verify_api_key_use_case.execute(
                    VerifyApiKeyQuery(api_key=api_key)
                )
            except ApiKeyInvalid:
                pass

        if self.auto_error:
            clear_session_cookie(response, settings)
            raise api_auth_unauthorized_exception(
                detail="Authentication credentials were not provided or are invalid.",
                set_cookie=response_set_cookie_header(response),
            )

        return AuthIdentity(user_id=None, username=None)


class ApiKeyOnlyAuthenticator:
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(
        self,
        request: Request,
        response: Response,
        settings: Settings = Depends(get_app_settings),
        verify_api_key_use_case: VerifyApiKeyUseCase = Depends(get_verify_api_key_use_case),
    ) -> AuthIdentity:
        api_key = extract_api_key(request)
        if api_key:
            try:
                return await verify_api_key_use_case.execute(
                    VerifyApiKeyQuery(api_key=api_key)
                )
            except ApiKeyInvalid:
                pass

        if self.auto_error:
            raise api_auth_unauthorized_exception(
                detail="A valid API key is required for this endpoint.",
            )

        return AuthIdentity(user_id=None, username=None)


async def get_required_api_auth(
    auth_data: AuthIdentity = Depends(SessionOrApiKeyAuthenticator(auto_error=True)),
) -> AuthIdentity:
    return auth_data


async def get_required_api_key_auth(
    auth_data: AuthIdentity = Depends(ApiKeyOnlyAuthenticator(auto_error=True)),
) -> AuthIdentity:
    return auth_data

__all__ = [
    "ApiKeyOnlyAuthenticator",
    "SessionOrApiKeyAuthenticator",
    "get_required_api_key_auth",
    "get_required_api_auth",
]
