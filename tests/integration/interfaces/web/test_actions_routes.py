import io
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.application.auth.types import AuthIdentity
from app.application.drop.models import DropDetailDTO, DropListDTO
from app.bootstrap.container import get_app_settings, get_csrf_token_service
from app.bootstrap.providers.auth import (
    get_create_api_key_use_case,
    get_delete_api_key_use_case,
    get_list_api_keys_use_case,
    get_password_login_use_case,
    get_revoke_api_key_use_case,
    get_revoke_session_use_case,
    get_verify_session_use_case,
)
from app.bootstrap.providers.drop import (
    get_create_drop_use_case,
    get_delete_drop_use_case,
    get_get_drop_meta_use_case,
    get_list_drops_use_case,
    get_update_drop_use_case,
)
from app.domain.auth.errors import ApiKeyNotFound
from app.domain.auth.errors import LoginInvalid
from app.domain.drop.errors import DropAccessDeniedError, DropNotFoundError
from app.domain.drop.value_objects import AccessScope
from app.interfaces.deps.auth import get_optional_session_auth
from app.interfaces.web.router import router as web_router


class _FakeVerifySessionUseCase:
    async def execute(self, _query) -> AuthIdentity:
        return AuthIdentity(user_id="user-1", username="tester")


class _FakeInvalidVerifySessionUseCase:
    async def execute(self, _query) -> AuthIdentity:
        from app.domain.auth.errors import SessionInvalid

        raise SessionInvalid()


class _FakeCsrfService:
    def __init__(self, *, verify_result: bool):
        self.verify_result = verify_result
        self.verify_calls: list[tuple[str, str | None]] = []

    def verify(self, session_id: str, csrf_token: str | None) -> bool:
        self.verify_calls.append((session_id, csrf_token))
        return self.verify_result

    def generate(self, _session_id: str) -> str:
        return "csrf"


class _FakeRevokeSessionUseCase:
    def __init__(self):
        self.calls: list[str] = []

    async def execute(self, sid: str):
        self.calls.append(sid)


class _FakeDeleteApiKeyUseCase:
    def __init__(self, parent: "_FakeApiKeyUseCases"):
        self.parent = parent

    async def execute(self, command):
        for idx, item in enumerate(self.parent.items):
            if (
                item.public_id == command.public_id
                and item.owner_user_id == getattr(command, "owner_user_id", item.owner_user_id)
            ):
                self.parent.items.pop(idx)
                return None
        raise ApiKeyNotFound()


class _FakeApiKeyUseCases:
    def __init__(self):
        self.items = []
        self.create_api_key_use_case = self._CreateApiKeyUseCase(self)
        self.list_api_keys_use_case = self._ListApiKeysUseCase(self)
        self.revoke_api_key_use_case = self._RevokeApiKeyUseCase(self)
        self.delete_api_key_use_case = _FakeDeleteApiKeyUseCase(self)

    class _CreateApiKeyUseCase:
        def __init__(self, parent: "_FakeApiKeyUseCases"):
            self.parent = parent

        async def execute(self, command):
            now = datetime.now(timezone.utc)
            item = SimpleNamespace(
                public_id="p1",
                name=command.name,
                owner_user_id=command.owner_user_id,
                created_at=now,
                expires_at=command.expires_at,
                last_used_at=None,
                revoked_at=None,
                key="tdpk_p1_secret",
            )
            self.parent.items.append(item)
            return item

    class _ListApiKeysUseCase:
        def __init__(self, parent: "_FakeApiKeyUseCases"):
            self.parent = parent

        async def execute(self, query=None):
            if query is None:
                return list(self.parent.items)
            return [
                item for item in self.parent.items if item.owner_user_id == query.owner_user_id
            ]

    class _RevokeApiKeyUseCase:
        def __init__(self, parent: "_FakeApiKeyUseCases"):
            self.parent = parent

        async def execute(self, command):
            for item in self.parent.items:
                if (
                    item.public_id == command.public_id
                    and item.owner_user_id == getattr(command, "owner_user_id", item.owner_user_id)
                ):
                    item.revoked_at = datetime.now(timezone.utc)
                    return item
            raise ApiKeyNotFound()

class _FakePasswordLoginUseCase:
    async def execute(self, _command):
        raise LoginInvalid()


def _auth_identity() -> AuthIdentity:
    return AuthIdentity(user_id="user-1", username="tester")


def _anonymous_identity() -> AuthIdentity:
    return AuthIdentity(user_id=None, username=None)


async def _fake_optional_session_auth(request: Request) -> AuthIdentity:
    if request.cookies.get("session_id"):
        return _auth_identity()
    return _anonymous_identity()


def _detail_dto(slug: str) -> DropDetailDTO:
    now = datetime.now(timezone.utc)
    return DropDetailDTO(
        owner_user_id="user-1",
        slug=slug,
        title="title",
        description=None,
        file_name=f"{slug}.txt",
        mime_type="text/plain",
        size_bytes=5,
        access_scope=AccessScope.PRIVATE,
        is_favorite=False,
        requires_password=False,
        created_at=now,
        updated_at=None,
        sha256=f"sha-{slug}",
    )


class _FakeDropUseCases:
    def __init__(self):
        self.create_calls = []
        self.update_calls = []

        self.check_slug_availability_use_case = self._NotUsedUseCase()
        self.get_drop_meta_use_case = self._GetDropMetaUseCase()
        self.delete_drop_use_case = self._NotUsedUseCase()
        self.create_drop_use_case = self._CreateDropUseCase(self)
        self.update_drop_use_case = self._UpdateDropUseCase(self)
        self.list_drops_use_case = self._ListDropsUseCase()

    class _NotUsedUseCase:
        async def execute(self, *_args, **_kwargs):
            raise AssertionError("Unexpected use case invocation")

    class _CreateDropUseCase:
        def __init__(self, parent: "_FakeDropUseCases"):
            self.parent = parent

        async def execute(self, command):
            self.parent.create_calls.append(command)
            return _detail_dto(command.slug or "generated")

    class _UpdateDropUseCase:
        def __init__(self, parent: "_FakeDropUseCases"):
            self.parent = parent

        async def execute(self, command):
            self.parent.update_calls.append(command)
            return _detail_dto(command.slug)

    class _GetDropMetaUseCase:
        async def execute_for_display(self, slug, auth=None):
            _ = auth
            return _detail_dto(slug)

        async def execute(self, query):
            return _detail_dto(query.slug)

        async def issue_grant_token(self, query):
            await self.execute(query)
            return f"grant-{query.slug}"

    class _ListDropsUseCase:
        async def execute(self, _query):
            return DropListDTO(items=[], page=1, page_size=200, total=0)


def _client(
    *,
    drop_use_cases: _FakeDropUseCases,
    api_key_use_cases: _FakeApiKeyUseCases,
    csrf_service: _FakeCsrfService,
    revoke_use_case: _FakeRevokeSessionUseCase,
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
        MAX_UPLOAD_BYTES=10_000_000,
    )

    app.dependency_overrides[get_app_settings] = lambda: fake_settings
    app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
    app.dependency_overrides[get_optional_session_auth] = _fake_optional_session_auth
    app.dependency_overrides[get_csrf_token_service] = lambda: csrf_service
    app.dependency_overrides[get_revoke_session_use_case] = lambda: revoke_use_case
    app.dependency_overrides[get_create_drop_use_case] = lambda: drop_use_cases.create_drop_use_case
    app.dependency_overrides[get_delete_drop_use_case] = lambda: drop_use_cases.delete_drop_use_case
    app.dependency_overrides[get_get_drop_meta_use_case] = lambda: drop_use_cases.get_drop_meta_use_case
    app.dependency_overrides[get_list_drops_use_case] = lambda: drop_use_cases.list_drops_use_case
    app.dependency_overrides[get_update_drop_use_case] = lambda: drop_use_cases.update_drop_use_case
    app.dependency_overrides[get_create_api_key_use_case] = (
        lambda: api_key_use_cases.create_api_key_use_case
    )
    app.dependency_overrides[get_list_api_keys_use_case] = (
        lambda: api_key_use_cases.list_api_keys_use_case
    )
    app.dependency_overrides[get_revoke_api_key_use_case] = (
        lambda: api_key_use_cases.revoke_api_key_use_case
    )
    app.dependency_overrides[get_delete_api_key_use_case] = (
        lambda: api_key_use_cases.delete_api_key_use_case
    )
    app.dependency_overrides[get_password_login_use_case] = lambda: _FakePasswordLoginUseCase()
    return TestClient(app)


class TestWebActionRoutesIntegration:
    def test_unauthenticated_mutation_returns_hx_redirect_for_hx_request(self):
        drop_use_cases = _FakeDropUseCases()
        client = _client(
            drop_use_cases=drop_use_cases,
            api_key_use_cases=_FakeApiKeyUseCases(),
            csrf_service=_FakeCsrfService(verify_result=True),
            revoke_use_case=_FakeRevokeSessionUseCase(),
        )

        response = client.post(
            "/actions/drop/k1/detail",
            headers={"HX-Request": "true"},
            data={"csrf_token": "csrf", "title": "new"},
        )

        assert response.status_code == 204
        assert response.headers.get("HX-Redirect") == "/"
        assert drop_use_cases.update_calls == []

    def test_unauthenticated_mutation_returns_http_redirect_for_non_hx_request(self):
        drop_use_cases = _FakeDropUseCases()
        client = _client(
            drop_use_cases=drop_use_cases,
            api_key_use_cases=_FakeApiKeyUseCases(),
            csrf_service=_FakeCsrfService(verify_result=True),
            revoke_use_case=_FakeRevokeSessionUseCase(),
        )

        response = client.post(
            "/actions/drop/k1/detail",
            data={"csrf_token": "csrf", "title": "new"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["location"] == "/"
        assert drop_use_cases.update_calls == []

    def test_csrf_failure_returns_403_and_does_not_mutate(self):
        drop_use_cases = _FakeDropUseCases()
        csrf_service = _FakeCsrfService(verify_result=False)
        client = _client(
            drop_use_cases=drop_use_cases,
            api_key_use_cases=_FakeApiKeyUseCases(),
            csrf_service=csrf_service,
            revoke_use_case=_FakeRevokeSessionUseCase(),
        )
        client.cookies.set("session_id", "sid")

        response = client.post(
            "/actions/drop/k1/detail",
            headers={"HX-Request": "true"},
            data={"csrf_token": "wrong", "title": "new"},
        )

        assert response.status_code == 403
        assert "유효하지 않은 CSRF 토큰입니다." in response.text
        assert drop_use_cases.update_calls == []
        assert csrf_service.verify_calls == [("sid", "wrong")]

    def test_upload_non_hx_success_redirects_manage_page(self):
        drop_use_cases = _FakeDropUseCases()
        csrf_service = _FakeCsrfService(verify_result=True)
        client = _client(
            drop_use_cases=drop_use_cases,
            api_key_use_cases=_FakeApiKeyUseCases(),
            csrf_service=csrf_service,
            revoke_use_case=_FakeRevokeSessionUseCase(),
        )
        client.cookies.set("session_id", "sid")

        response = client.post(
            "/actions/drop/upload",
            data={"csrf_token": "csrf", "slug": "upload-1", "user_only": "true"},
            files={"file": ("hello.txt", io.BytesIO(b"hello"), "text/plain")},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/drops/upload-1"
        assert len(drop_use_cases.create_calls) == 1
        assert drop_use_cases.create_calls[0].access_scope == AccessScope.PRIVATE
        assert drop_use_cases.create_calls[0].owner_user_id == "user-1"

    def test_password_clear_uses_authenticated_owner_identity(self):
        drop_use_cases = _FakeDropUseCases()
        csrf_service = _FakeCsrfService(verify_result=True)
        client = _client(
            drop_use_cases=drop_use_cases,
            api_key_use_cases=_FakeApiKeyUseCases(),
            csrf_service=csrf_service,
            revoke_use_case=_FakeRevokeSessionUseCase(),
        )
        client.cookies.set("session_id", "sid")

        response = client.post(
            "/actions/drop/k1/password",
            data={
                "csrf_token": "csrf",
                "new_password": "",
                "confirm_password": "",
            },
        )

        assert response.status_code == 200
        assert "드롭 비밀번호가 해제되었습니다." in response.text
        assert len(drop_use_cases.update_calls) == 1
        assert drop_use_cases.update_calls[0].slug == "k1"
        assert drop_use_cases.update_calls[0].current_password is None
        assert drop_use_cases.update_calls[0].new_password is None
        assert drop_use_cases.update_calls[0].auth.user_id == "user-1"

    def test_detail_update_uses_authenticated_owner_identity(self):
        drop_use_cases = _FakeDropUseCases()
        client = _client(
            drop_use_cases=drop_use_cases,
            api_key_use_cases=_FakeApiKeyUseCases(),
            csrf_service=_FakeCsrfService(verify_result=True),
            revoke_use_case=_FakeRevokeSessionUseCase(),
        )
        client.cookies.set("session_id", "sid")

        response = client.post(
            "/actions/drop/k1/detail",
            data={"csrf_token": "csrf", "title": "new"},
        )

        assert response.status_code == 200
        assert len(drop_use_cases.update_calls) == 1
        assert drop_use_cases.update_calls[0].auth.user_id == "user-1"

    def test_delete_uses_authenticated_owner_identity(self):
        class _CapturingDeleteDropUseCase:
            def __init__(self):
                self.command = None

            async def execute(self, command):
                self.command = command

        drop_use_cases = _FakeDropUseCases()
        delete_drop_use_case = _CapturingDeleteDropUseCase()
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
            MAX_UPLOAD_BYTES=10_000_000,
        )
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = (
            lambda: _FakeVerifySessionUseCase()
        )
        app.dependency_overrides[get_optional_session_auth] = _fake_optional_session_auth
        app.dependency_overrides[get_csrf_token_service] = (
            lambda: _FakeCsrfService(verify_result=True)
        )
        app.dependency_overrides[get_revoke_session_use_case] = (
            lambda: _FakeRevokeSessionUseCase()
        )
        app.dependency_overrides[get_create_drop_use_case] = (
            lambda: drop_use_cases.create_drop_use_case
        )
        app.dependency_overrides[get_delete_drop_use_case] = lambda: delete_drop_use_case
        app.dependency_overrides[get_get_drop_meta_use_case] = (
            lambda: drop_use_cases.get_drop_meta_use_case
        )
        app.dependency_overrides[get_list_drops_use_case] = (
            lambda: drop_use_cases.list_drops_use_case
        )
        app.dependency_overrides[get_update_drop_use_case] = (
            lambda: drop_use_cases.update_drop_use_case
        )
        app.dependency_overrides[get_create_api_key_use_case] = (
            lambda: _FakeApiKeyUseCases().create_api_key_use_case
        )
        app.dependency_overrides[get_list_api_keys_use_case] = (
            lambda: _FakeApiKeyUseCases().list_api_keys_use_case
        )
        app.dependency_overrides[get_revoke_api_key_use_case] = (
            lambda: _FakeApiKeyUseCases().revoke_api_key_use_case
        )
        app.dependency_overrides[get_delete_api_key_use_case] = (
            lambda: _FakeApiKeyUseCases().delete_api_key_use_case
        )
        app.dependency_overrides[get_password_login_use_case] = lambda: _FakePasswordLoginUseCase()
        client = TestClient(app)
        client.cookies.set("session_id", "sid")

        response = client.post(
            "/actions/drop/k1/delete",
            data={"csrf_token": "csrf"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/drops"
        assert delete_drop_use_case.command is not None
        assert delete_drop_use_case.command.current_password is None
        assert delete_drop_use_case.command.auth.user_id == "user-1"

    def test_logout_csrf_failure_redirects_without_revoke_call(self):
        revoke_use_case = _FakeRevokeSessionUseCase()
        client = _client(
            drop_use_cases=_FakeDropUseCases(),
            api_key_use_cases=_FakeApiKeyUseCases(),
            csrf_service=_FakeCsrfService(verify_result=False),
            revoke_use_case=revoke_use_case,
        )
        client.cookies.set("session_id", "sid")

        response = client.post(
            "/actions/auth/logout",
            data={"csrf_token": "bad"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["location"] == "/?auth_error=logout_csrf_invalid"
        assert revoke_use_case.calls == []

    def test_logout_csrf_failure_returns_hx_redirect_for_htmx(self):
        revoke_use_case = _FakeRevokeSessionUseCase()
        client = _client(
            drop_use_cases=_FakeDropUseCases(),
            api_key_use_cases=_FakeApiKeyUseCases(),
            csrf_service=_FakeCsrfService(verify_result=False),
            revoke_use_case=revoke_use_case,
        )
        client.cookies.set("session_id", "sid")

        response = client.post(
            "/actions/auth/logout",
            headers={"HX-Request": "true"},
            data={"csrf_token": "bad"},
        )

        assert response.status_code == 204
        assert response.headers["HX-Redirect"] == "/?auth_error=logout_csrf_invalid"
        assert revoke_use_case.calls == []

    def test_logout_clears_session_and_drop_grant_cookies(self):
        revoke_use_case = _FakeRevokeSessionUseCase()
        client = _client(
            drop_use_cases=_FakeDropUseCases(),
            api_key_use_cases=_FakeApiKeyUseCases(),
            csrf_service=_FakeCsrfService(verify_result=True),
            revoke_use_case=revoke_use_case,
        )
        client.cookies.set("session_id", "sid")
        client.cookies.set("tdg_drop_1", "grant-1")
        client.cookies.set("tdg_drop_2", "grant-2")
        client.cookies.set("unrelated", "keep")

        response = client.post(
            "/actions/auth/logout",
            headers={"HX-Request": "true"},
            data={"csrf_token": "csrf"},
        )

        set_cookie_headers = response.headers.get_list("set-cookie")

        assert response.status_code == 204
        assert response.headers["HX-Redirect"] == "/"
        assert revoke_use_case.calls == ["sid"]
        assert any(header.startswith("session_id=") for header in set_cookie_headers)
        assert any(header.startswith("tdg_drop_1=") for header in set_cookie_headers)
        assert any(header.startswith("tdg_drop_2=") for header in set_cookie_headers)
        assert not any(header.startswith("unrelated=") for header in set_cookie_headers)

    def test_api_key_actions_require_login_and_csrf(self):
        api_key_use_cases = _FakeApiKeyUseCases()
        client = _client(
            drop_use_cases=_FakeDropUseCases(),
            api_key_use_cases=api_key_use_cases,
            csrf_service=_FakeCsrfService(verify_result=True),
            revoke_use_case=_FakeRevokeSessionUseCase(),
        )

        no_login = client.post(
            "/actions/auth/api-keys/create",
            data={"csrf_token": "csrf", "name": "mobile"},
            follow_redirects=False,
        )
        assert no_login.status_code == 302
        assert no_login.headers["location"] == "/"

        client = _client(
            drop_use_cases=_FakeDropUseCases(),
            api_key_use_cases=api_key_use_cases,
            csrf_service=_FakeCsrfService(verify_result=False),
            revoke_use_case=_FakeRevokeSessionUseCase(),
        )
        client.cookies.set("session_id", "sid")
        csrf_fail = client.post(
            "/actions/auth/api-keys/create",
            data={"csrf_token": "bad", "name": "mobile"},
        )
        assert csrf_fail.status_code == 403

    def test_api_key_create_revoke_delete_flow(self):
        api_key_use_cases = _FakeApiKeyUseCases()
        api_key_use_cases.items.append(
            SimpleNamespace(
                public_id="foreign",
                name="other",
                owner_user_id="user-2",
                created_at=datetime.now(timezone.utc),
                expires_at=None,
                last_used_at=None,
                revoked_at=None,
                key="tdpk_foreign_secret",
            )
        )
        client = _client(
            drop_use_cases=_FakeDropUseCases(),
            api_key_use_cases=api_key_use_cases,
            csrf_service=_FakeCsrfService(verify_result=True),
            revoke_use_case=_FakeRevokeSessionUseCase(),
        )
        client.cookies.set("session_id", "sid")

        created = client.post(
            "/actions/auth/api-keys/create",
            data={"csrf_token": "csrf", "name": "mobile"},
        )
        assert created.status_code == 200
        assert "tdpk_p1_secret" in created.text
        assert "foreign" not in created.text
        assert "tester" not in created.text
        assert len(api_key_use_cases.items) == 2
        assert api_key_use_cases.items[-1].owner_user_id == "user-1"

        revoked = client.post(
            "/actions/auth/api-keys/p1/revoke",
            data={"csrf_token": "csrf"},
        )
        assert revoked.status_code == 200
        assert "폐기되었습니다" in revoked.text
        assert any(
            item.public_id == "p1" and item.revoked_at is not None
            for item in api_key_use_cases.items
        )

        deleted = client.post(
            "/actions/auth/api-keys/p1/delete",
            data={"csrf_token": "csrf"},
        )
        assert deleted.status_code == 200
        assert "삭제되었습니다" in deleted.text
        assert [item.public_id for item in api_key_use_cases.items] == ["foreign"]

    def test_api_key_actions_mask_non_owned_key_as_404(self):
        api_key_use_cases = _FakeApiKeyUseCases()
        api_key_use_cases.items.append(
            SimpleNamespace(
                public_id="foreign",
                name="other",
                owner_user_id="user-2",
                created_at=datetime.now(timezone.utc),
                expires_at=None,
                last_used_at=None,
                revoked_at=None,
                key="tdpk_foreign_secret",
            )
        )
        client = _client(
            drop_use_cases=_FakeDropUseCases(),
            api_key_use_cases=api_key_use_cases,
            csrf_service=_FakeCsrfService(verify_result=True),
            revoke_use_case=_FakeRevokeSessionUseCase(),
        )
        client.cookies.set("session_id", "sid")

        response = client.post(
            "/actions/auth/api-keys/foreign/revoke",
            data={"csrf_token": "csrf"},
        )

        assert response.status_code == 404
        assert "존재하지 않는 API key 입니다." in response.text

    def test_api_key_create_normalizes_local_expiration_to_utc(self):
        api_key_use_cases = _FakeApiKeyUseCases()
        client = _client(
            drop_use_cases=_FakeDropUseCases(),
            api_key_use_cases=api_key_use_cases,
            csrf_service=_FakeCsrfService(verify_result=True),
            revoke_use_case=_FakeRevokeSessionUseCase(),
        )
        client.cookies.set("session_id", "sid")

        response = client.post(
            "/actions/auth/api-keys/create",
            data={
                "csrf_token": "csrf",
                "name": "mobile",
                "expires_at": "2026-04-20T09:30",
                "timezone_offset_minutes": "-540",
            },
        )

        assert response.status_code == 200
        assert api_key_use_cases.items[0].expires_at == datetime(
            2026, 4, 20, 0, 30, tzinfo=timezone.utc
        )

    def test_non_hx_login_failure_redirects_home_with_error_code(self):
        client = _client(
            drop_use_cases=_FakeDropUseCases(),
            api_key_use_cases=_FakeApiKeyUseCases(),
            csrf_service=_FakeCsrfService(verify_result=True),
            revoke_use_case=_FakeRevokeSessionUseCase(),
        )

        response = client.post(
            "/actions/auth/login",
            data={"username": "tester", "password": "wrong"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["location"] == "/?auth_error=login_invalid"

    def test_password_route_renders_404_for_stale_slug(self):
        class _MissingGetDropMetaUseCase:
            async def execute_for_display(self, slug, auth=None):
                _ = (slug, auth)
                raise DropNotFoundError()

            async def execute(self, _query):
                raise AssertionError("Unexpected execute call")

        drop_use_cases = _FakeDropUseCases()
        drop_use_cases.get_drop_meta_use_case = _MissingGetDropMetaUseCase()
        client = _client(
            drop_use_cases=drop_use_cases,
            api_key_use_cases=_FakeApiKeyUseCases(),
            csrf_service=_FakeCsrfService(verify_result=True),
            revoke_use_case=_FakeRevokeSessionUseCase(),
        )
        client.cookies.set("session_id", "sid")

        response = client.post(
            "/actions/drop/missing/password",
            data={"csrf_token": "csrf", "new_password": "", "confirm_password": ""},
        )

        assert response.status_code == 404
        assert "파일이 존재하지 않습니다." in response.text

    def test_shared_page_masks_private_non_owner_as_404(self):
        class _DeniedGetDropMetaUseCase:
            async def execute_for_display(self, slug, auth=None):
                _ = (slug, auth)
                raise DropAccessDeniedError()

            async def execute(self, _query):
                raise AssertionError("Unexpected execute call")

        drop_use_cases = _FakeDropUseCases()
        drop_use_cases.get_drop_meta_use_case = _DeniedGetDropMetaUseCase()
        client = _client(
            drop_use_cases=drop_use_cases,
            api_key_use_cases=_FakeApiKeyUseCases(),
            csrf_service=_FakeCsrfService(verify_result=True),
            revoke_use_case=_FakeRevokeSessionUseCase(),
        )
        client.cookies.set("session_id", "sid")

        response = client.get("/secret")

        assert response.status_code == 404
        assert "파일이 존재하지 않습니다." in response.text

    def test_stale_session_cookie_is_cleared_on_home_response(self):
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
            MAX_UPLOAD_BYTES=10_000_000,
        )
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = (
            lambda: _FakeInvalidVerifySessionUseCase()
        )
        app.dependency_overrides[get_csrf_token_service] = (
            lambda: _FakeCsrfService(verify_result=True)
        )
        app.dependency_overrides[get_revoke_session_use_case] = (
            lambda: _FakeRevokeSessionUseCase()
        )
        app.dependency_overrides[get_create_drop_use_case] = (
            lambda: _FakeDropUseCases().create_drop_use_case
        )
        app.dependency_overrides[get_delete_drop_use_case] = (
            lambda: _FakeDropUseCases().delete_drop_use_case
        )
        app.dependency_overrides[get_get_drop_meta_use_case] = (
            lambda: _FakeDropUseCases().get_drop_meta_use_case
        )
        app.dependency_overrides[get_list_drops_use_case] = (
            lambda: _FakeDropUseCases().list_drops_use_case
        )
        app.dependency_overrides[get_update_drop_use_case] = (
            lambda: _FakeDropUseCases().update_drop_use_case
        )
        app.dependency_overrides[get_create_api_key_use_case] = (
            lambda: _FakeApiKeyUseCases().create_api_key_use_case
        )
        app.dependency_overrides[get_list_api_keys_use_case] = (
            lambda: _FakeApiKeyUseCases().list_api_keys_use_case
        )
        app.dependency_overrides[get_revoke_api_key_use_case] = (
            lambda: _FakeApiKeyUseCases().revoke_api_key_use_case
        )
        app.dependency_overrides[get_delete_api_key_use_case] = (
            lambda: _FakeApiKeyUseCases().delete_api_key_use_case
        )
        async def _stale_optional_session_auth(request: Request) -> AuthIdentity:
            if request.cookies.get("session_id"):
                request.state.clear_session_cookie_pending = True
            return _anonymous_identity()

        app.dependency_overrides[get_optional_session_auth] = _stale_optional_session_auth
        app.dependency_overrides[get_password_login_use_case] = lambda: _FakePasswordLoginUseCase()
        client = TestClient(app)
        client.cookies.set("session_id", "stale-sid")

        response = client.get("/")

        assert response.status_code == 200
        assert "session_id=" in response.headers.get("set-cookie", "")
