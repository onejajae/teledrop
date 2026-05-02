from fastapi import HTTPException, Request

from app.application.auth.types import AuthIdentity
from app.domain.auth.errors import ApiKeyInvalid
from app.interfaces.api.deps.auth import ApiKeyOnlyAuthenticator


class _FakeVerifyApiKeyUseCase:
    def __init__(self, *, identity: AuthIdentity | None = None, exc: Exception | None = None):
        self.identity = identity or AuthIdentity(user_id="user-1", username="tester")
        self.exc = exc
        self.queries = []

    async def execute(self, query):
        self.queries.append(query)
        if self.exc is not None:
            raise self.exc
        return self.identity


def _request(api_key: str | None = None) -> Request:
    raw_headers: list[tuple[bytes, bytes]] = []
    if api_key:
        raw_headers.append((b"x-api-key", api_key.encode("utf-8")))

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": raw_headers,
        "scheme": "http",
        "http_version": "1.1",
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    return Request(scope)


class TestApiKeyOnlyAuthenticator:
    async def test_auto_error_false_without_credentials_returns_anonymous(self):
        authenticator = ApiKeyOnlyAuthenticator(auto_error=False)

        identity = await authenticator(
            request=_request(),
            verify_api_key_use_case=_FakeVerifyApiKeyUseCase(),
        )

        assert identity.username is None
        assert identity.user_id is None

    async def test_valid_api_key_returns_identity(self):
        authenticator = ApiKeyOnlyAuthenticator(auto_error=True)

        identity = await authenticator(
            request=_request(api_key="tdpk_public_secret"),
            verify_api_key_use_case=_FakeVerifyApiKeyUseCase(
                identity=AuthIdentity(user_id="user-api", username="api-user")
            ),
        )

        assert identity.username == "api-user"
        assert identity.user_id == "user-api"

    async def test_invalid_api_key_raises_api_key_auth_error(self):
        authenticator = ApiKeyOnlyAuthenticator(auto_error=True)

        try:
            await authenticator(
                request=_request(api_key="bad"),
                verify_api_key_use_case=_FakeVerifyApiKeyUseCase(exc=ApiKeyInvalid()),
            )
        except HTTPException as exc:
            headers = {key.lower(): value for key, value in (exc.headers or {}).items()}
            assert exc.status_code == 401
            assert headers.get("www-authenticate") == "ApiKey"
        else:
            raise AssertionError("Expected HTTPException")
