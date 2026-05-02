from types import SimpleNamespace

from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.application.auth.types import AuthIdentity
from app.bootstrap.container import get_app_settings, get_csrf_token_service
from app.bootstrap.providers.auth import get_list_api_keys_use_case, get_verify_session_use_case
from app.domain.auth.errors import SessionInvalid
from app.interfaces.deps.auth import get_optional_session_auth
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
    def __init__(self):
        self.items = []

    async def execute(self, query=None):
        if query is None:
            return list(self.items)
        return [item for item in self.items if item.owner_user_id == query.owner_user_id]


def _auth_identity() -> AuthIdentity:
    return AuthIdentity(user_id="user-1", username="tester")


def _anonymous_identity() -> AuthIdentity:
    return AuthIdentity(user_id=None, username=None)


async def _fake_optional_session_auth(request: Request) -> AuthIdentity:
    if request.cookies.get("session_id"):
        return _auth_identity()
    return _anonymous_identity()


def _client(
    list_api_keys_use_case: _FakeListApiKeysUseCase | None = None,
    *,
    enable_registration: bool = False,
) -> TestClient:
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
        ENABLE_REGISTRATION=enable_registration,
    )
    app.dependency_overrides[get_app_settings] = lambda: fake_settings
    app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
    app.dependency_overrides[get_optional_session_auth] = _fake_optional_session_auth
    app.dependency_overrides[get_csrf_token_service] = lambda: _FakeCsrfService()
    app.dependency_overrides[get_list_api_keys_use_case] = (
        lambda: list_api_keys_use_case or _FakeListApiKeysUseCase()
    )
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

    def test_settings_api_keys_only_shows_current_users_keys(self):
        api_keys_use_case = _FakeListApiKeysUseCase()
        api_keys_use_case.items.extend(
            [
                SimpleNamespace(
                    public_id="mine",
                    name="mine",
                    owner_user_id="user-1",
                    created_at=datetime.now(timezone.utc),
                    expires_at=None,
                    last_used_at=None,
                    revoked_at=None,
                ),
                SimpleNamespace(
                    public_id="foreign",
                    name="foreign",
                    owner_user_id="user-2",
                    created_at=datetime.now(timezone.utc),
                    expires_at=None,
                    last_used_at=None,
                    revoked_at=None,
                ),
            ]
        )
        client = _client(api_keys_use_case)
        client.cookies.set("session_id", "sid")

        response = client.get("/settings/api-keys")

        assert response.status_code == 200
        assert "mine" in response.text
        assert "foreign" not in response.text
        assert "생성자" not in response.text

    def test_home_renders_auth_error_banner_from_query(self):
        client = _client()

        response = client.get("/?auth_error=login_invalid")

        assert response.status_code == 200
        assert "아이디 또는 비밀번호가 올바르지 않습니다." in response.text

    def test_home_hides_registration_when_disabled(self):
        client = _client()

        response = client.get("/")

        assert response.status_code == 200
        assert 'action="/actions/auth/register"' not in response.text
        assert "회원가입" not in response.text

    def test_register_route_returns_404_when_registration_disabled(self):
        client = _client()

        response = client.get("/register")

        assert response.status_code == 404
        assert response.headers["content-type"].startswith("text/html")
        assert "존재하지 않습니다." in response.text
        assert "요청한 페이지를 찾을 수 없습니다." in response.text
        assert '{"detail":"Not Found"}' not in response.text
        assert 'action="/actions/auth/register"' not in response.text

    def test_register_route_renders_registration_form_when_enabled(self):
        client = _client(enable_registration=True)

        response = client.get("/register")

        assert response.status_code == 200
        assert "회원가입" in response.text
        assert 'action="/actions/auth/register"' in response.text
        assert 'name="confirm_password"' in response.text

    def test_register_route_redirects_authenticated_user_home(self):
        client = _client(enable_registration=True)
        client.cookies.set("session_id", "sid")

        response = client.get("/register", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "/"

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
        async def _stale_optional_session_auth(request: Request) -> AuthIdentity:
            if request.cookies.get("session_id"):
                request.state.clear_session_cookie_pending = True
            return _anonymous_identity()

        app.dependency_overrides[get_optional_session_auth] = _stale_optional_session_auth
        app.dependency_overrides[get_csrf_token_service] = lambda: _FakeCsrfService()
        app.dependency_overrides[get_list_api_keys_use_case] = lambda: _FakeListApiKeysUseCase()
        client = TestClient(app)
        client.cookies.set("session_id", "stale")

        response = client.get("/")

        assert response.status_code == 200
        assert "session_id=" in response.headers.get("set-cookie", "")
