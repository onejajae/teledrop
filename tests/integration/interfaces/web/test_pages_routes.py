from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.bootstrap.container import get_app_settings, get_csrf_token_service
from app.bootstrap.providers.auth import get_list_api_keys_use_case, get_verify_session_use_case
from app.domain.auth.errors import SessionInvalid
from app.interfaces.web.router import router as web_router


class _FakeVerifySessionUseCase:
    async def execute(self, _query) -> str:
        return "tester"


class _FakeInvalidVerifySessionUseCase:
    async def execute(self, _query) -> str:
        raise SessionInvalid()


class _FakeCsrfService:
    def verify(self, _session_id: str, _csrf_token: str | None) -> bool:
        return True

    def generate(self, _session_id: str) -> str:
        return "csrf"


class _FakeListApiKeysUseCase:
    async def execute(self):
        return []


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(web_router)
    fake_settings = SimpleNamespace(
        SESSION_COOKIE_NAME="session_id",
        SESSION_COOKIE_PATH="/",
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_SAMESITE="lax",
        SESSION_TTL_SECONDS=86400,
        CSRF_SECRET_KEY="csrf-secret",
        DEFAULT_PAGE_SIZE=10,
        MAX_PAGE_SIZE=200,
    )
    app.dependency_overrides[get_app_settings] = lambda: fake_settings
    app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
    app.dependency_overrides[get_csrf_token_service] = lambda: _FakeCsrfService()
    app.dependency_overrides[get_list_api_keys_use_case] = lambda: _FakeListApiKeysUseCase()
    return TestClient(app)


class TestWebPagesRoutes:
    def test_home_renders_for_anonymous_user(self):
        client = _client()

        response = client.get("/")

        assert response.status_code == 200

    def test_home_renders_for_logged_in_user(self):
        client = _client()
        client.cookies.set("session_id", "sid")

        response = client.get("/")

        assert response.status_code == 200

    def test_dev_components_renders_for_anonymous_user(self):
        client = _client()

        response = client.get("/dev/components")

        assert response.status_code == 200
        assert "Web Components" in response.text
        assert "Drop Composites" in response.text

    def test_settings_api_keys_requires_login(self):
        client = _client()

        response = client.get("/settings/api-keys", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "/"

    def test_settings_api_keys_renders_for_logged_in_user(self):
        client = _client()
        client.cookies.set("session_id", "sid")

        response = client.get("/settings/api-keys")

        assert response.status_code == 200
        assert "API Keys" in response.text
        assert "API key 생성" in response.text

    def test_home_renders_auth_error_banner_from_query(self):
        client = _client()

        response = client.get("/?auth_error=login_invalid")

        assert response.status_code == 200
        assert "아이디 또는 비밀번호가 올바르지 않습니다." in response.text

    def test_home_clears_stale_session_cookie(self):
        app = FastAPI()
        app.include_router(web_router)
        fake_settings = SimpleNamespace(
            SESSION_COOKIE_NAME="session_id",
            SESSION_COOKIE_PATH="/",
            SESSION_COOKIE_SECURE=False,
            SESSION_COOKIE_SAMESITE="lax",
            SESSION_TTL_SECONDS=86400,
            CSRF_SECRET_KEY="csrf-secret",
            DEFAULT_PAGE_SIZE=10,
            MAX_PAGE_SIZE=200,
        )
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = (
            lambda: _FakeInvalidVerifySessionUseCase()
        )
        app.dependency_overrides[get_csrf_token_service] = lambda: _FakeCsrfService()
        app.dependency_overrides[get_list_api_keys_use_case] = lambda: _FakeListApiKeysUseCase()
        client = TestClient(app)
        client.cookies.set("session_id", "stale")

        response = client.get("/")

        assert response.status_code == 200
        assert "session_id=" in response.headers.get("set-cookie", "")
