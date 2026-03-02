from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response
from fastapi import Request

from app.domain.auth.errors import SessionExpired, SessionInvalid
from app.interfaces.api.deps.auth import Authenticator


class _FakeVerifySessionUseCase:
    def __init__(self, *, username: str = "tester", exc: Exception | None = None):
        self.username = username
        self.exc = exc
        self.queries = []

    async def execute(self, query):
        self.queries.append(query)
        if self.exc is not None:
            raise self.exc
        return self.username


def _request(cookies: dict[str, str] | None = None) -> Request:
    raw_headers: list[tuple[bytes, bytes]] = []
    if cookies:
        cookie_header = "; ".join(f"{key}={value}" for key, value in cookies.items())
        raw_headers.append((b"cookie", cookie_header.encode("utf-8")))

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


def _settings():
    return SimpleNamespace(SESSION_COOKIE_NAME="session_id", SESSION_COOKIE_PATH="/")


class TestAuthenticator:
    async def test_auto_error_true_without_session_raises_401_with_cookie_header(self):
        authenticator = Authenticator(auto_error=True)
        request = _request()
        response = Response()

        with pytest.raises(HTTPException) as exc_info:
            await authenticator(
                request=request,
                response=response,
                settings=_settings(),
                verify_session_use_case=_FakeVerifySessionUseCase(),
            )

        headers = {key.lower(): value for key, value in (exc_info.value.headers or {}).items()}
        assert exc_info.value.status_code == 401
        assert headers.get("www-authenticate") == "Session"
        assert "session_id=" in headers.get("set-cookie", "")

    async def test_auto_error_false_without_session_returns_anonymous(self):
        authenticator = Authenticator(auto_error=False)
        identity = await authenticator(
            request=_request(),
            response=Response(),
            settings=_settings(),
            verify_session_use_case=_FakeVerifySessionUseCase(),
        )

        assert identity.username is None

    @pytest.mark.parametrize("raised", [SessionExpired(), SessionInvalid()])
    async def test_invalid_or_expired_session_clears_cookie_and_raises_401(self, raised: Exception):
        authenticator = Authenticator(auto_error=True)
        request = _request({"session_id": "sid-1"})
        response = Response()
        verify_use_case = _FakeVerifySessionUseCase(exc=raised)

        with pytest.raises(HTTPException) as exc_info:
            await authenticator(
                request=request,
                response=response,
                settings=_settings(),
                verify_session_use_case=verify_use_case,
            )

        headers = {key.lower(): value for key, value in (exc_info.value.headers or {}).items()}
        assert exc_info.value.status_code == 401
        assert verify_use_case.queries[0].sid == "sid-1"
        assert "session_id=" in headers.get("set-cookie", "")

    async def test_valid_session_returns_username(self):
        authenticator = Authenticator(auto_error=True)
        verify_use_case = _FakeVerifySessionUseCase(username="alice")

        identity = await authenticator(
            request=_request({"session_id": "sid-2"}),
            response=Response(),
            settings=_settings(),
            verify_session_use_case=verify_use_case,
        )

        assert identity.username == "alice"
        assert verify_use_case.queries[0].sid == "sid-2"
