from fastapi import Depends, Request

from app.application.auth.models import VerifyApiKeyQuery
from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases import VerifyApiKeyUseCase
from app.bootstrap.providers.auth import get_verify_api_key_use_case
from app.domain.auth.errors import ApiKeyInvalid
from app.interfaces.api.errors import api_auth_unauthorized_exception
from app.interfaces.deps.auth import extract_api_key


class ApiKeyOnlyAuthenticator:
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(
        self,
        request: Request,
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


async def get_required_api_key_auth(
    auth_data: AuthIdentity = Depends(ApiKeyOnlyAuthenticator(auto_error=True)),
) -> AuthIdentity:
    return auth_data


__all__ = [
    "ApiKeyOnlyAuthenticator",
    "get_required_api_key_auth",
]
