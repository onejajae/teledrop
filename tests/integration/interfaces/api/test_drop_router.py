from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from app.application.auth.types import AuthIdentity
from app.application.drop.models import DropDetailDTO, UNSET
from app.bootstrap.container import get_app_settings
from app.bootstrap.providers.auth import (
    get_revoke_session_use_case,
    get_verify_api_key_use_case,
    get_verify_session_use_case,
)
from app.bootstrap.providers.drop import (
    get_check_slug_availability_use_case,
    get_create_drop_use_case,
    get_delete_drop_use_case,
    get_get_drop_meta_use_case,
    get_get_drop_stream_source_use_case,
    get_list_drops_use_case,
    get_update_drop_use_case,
)
from app.core.drop_grants import drop_grant_cookie_name
from app.domain.auth.errors import ApiKeyInvalid
from app.domain.drop.errors import (
    DropAccessDeniedError,
    DropNotFoundError,
    DropPasswordInvalidError,
)
from app.domain.drop.value_objects import AccessScope
from app.interfaces.api.deps.auth import get_required_api_auth
from app.interfaces.api.router import api_router
from app.interfaces.deps.auth import get_optional_api_auth, get_optional_session_auth


class _FakeVerifySessionUseCase:
    async def execute(self, _query) -> str:
        return "tester"


class _FakeVerifyApiKeyUseCase:
    async def execute(self, query) -> str:
        if query.api_key == "tdpk_public_secret":
            return "tester"
        raise ApiKeyInvalid()


class _FakeRevokeSessionUseCase:
    def __init__(self):
        self.calls: list[str] = []

    async def execute(self, sid: str):
        self.calls.append(sid)


def _auth_identity() -> AuthIdentity:
    return AuthIdentity(user_id="user-1", username="tester")


def _anonymous_identity() -> AuthIdentity:
    return AuthIdentity(user_id=None, username=None)


async def _fake_optional_api_auth(request: Request) -> AuthIdentity:
    if request.cookies.get("session_id") or request.headers.get("X-API-Key") == "tdpk_public_secret":
        return _auth_identity()
    return _anonymous_identity()


async def _fake_required_api_auth(request: Request) -> AuthIdentity:
    identity = await _fake_optional_api_auth(request)
    if not identity.is_authenticated:
        raise HTTPException(status_code=401)
    return identity


async def _fake_optional_session_auth(request: Request) -> AuthIdentity:
    if request.cookies.get("session_id"):
        return _auth_identity()
    return _anonymous_identity()


def _detail_dto(
    *,
    slug: str,
    title: str | None = "original",
    payload_size: int = 11,
    access_scope: AccessScope = AccessScope.PUBLIC,
    requires_password: bool = False,
) -> DropDetailDTO:
    now = datetime.now(timezone.utc)
    return DropDetailDTO(
        owner_user_id="user-1",
        slug=slug,
        title=title,
        description="desc",
        file_name=f"{slug}.txt",
        mime_type="text/plain",
        size_bytes=payload_size,
        access_scope=access_scope,
        is_favorite=False,
        requires_password=requires_password,
        created_at=now,
        updated_at=None,
        sha256=f"sha-{slug}",
    )


class _FakeDropUseCases:
    def __init__(self):
        self.items: dict[str, DropDetailDTO] = {}
        self.payloads: dict[str, bytes] = {}
        self.read_errors: dict[tuple[str, str], Exception] = {}
        self.update_commands = []

        self.check_slug_availability_use_case = self._NotUsedUseCase()
        self.create_drop_use_case = self._NotUsedUseCase()
        self.list_drops_use_case = self._NotUsedUseCase()
        self.delete_drop_use_case = self._NotUsedUseCase()
        self.get_drop_meta_use_case = self._GetDropMetaUseCase(self)
        self.get_drop_stream_source_use_case = self._GetDropStreamSourceUseCase(self)
        self.update_drop_use_case = self._UpdateDropUseCase(self)

    def add_drop(
        self,
        slug: str,
        *,
        payload: bytes = b"hello world",
        title: str | None = "original",
    ) -> None:
        self.items[slug] = _detail_dto(slug=slug, title=title, payload_size=len(payload))
        self.payloads[slug] = payload

    class _NotUsedUseCase:
        async def execute(self, *_args, **_kwargs):
            raise AssertionError("Unexpected use case invocation")

    class _GetDropMetaUseCase:
        def __init__(self, parent: "_FakeDropUseCases"):
            self.parent = parent

        async def execute(self, query):
            maybe_error = self.parent.read_errors.get(("meta", query.slug))
            if maybe_error is not None:
                raise maybe_error

            item = self.parent.items.get(query.slug)
            if item is None:
                raise DropNotFoundError()
            return item

    class _GetDropStreamSourceUseCase:
        def __init__(self, parent: "_FakeDropUseCases"):
            self.parent = parent

        async def execute(self, query):
            maybe_error = self.parent.read_errors.get(("stream", query.slug))
            if maybe_error is not None:
                raise maybe_error

            item = self.parent.items.get(query.slug)
            if item is None:
                raise DropNotFoundError()
            return item, query.slug

        async def iter_stream_range(self, storage_key: str, start: int, end: int):
            payload = self.parent.payloads[storage_key]
            yield payload[start : end + 1]

    class _UpdateDropUseCase:
        def __init__(self, parent: "_FakeDropUseCases"):
            self.parent = parent

        async def execute(self, command):
            self.parent.update_commands.append(command)
            item = self.parent.items.get(command.slug)
            if item is None:
                raise DropNotFoundError()

            if command.title is not UNSET:
                item.title = command.title
            if command.description is not UNSET:
                item.description = command.description
            if command.access_scope is not UNSET:
                item.access_scope = command.access_scope
            if command.is_favorite is not UNSET:
                item.is_favorite = command.is_favorite
            if command.new_password is not UNSET:
                item.requires_password = bool(command.new_password)

            return item


def _client(
    fake_use_cases: _FakeDropUseCases,
    revoke_use_case: _FakeRevokeSessionUseCase | None = None,
) -> TestClient:
    app = FastAPI()
    app.include_router(api_router, prefix="/api")
    fake_settings = SimpleNamespace(
        SESSION_COOKIE_NAME="session_id",
        SESSION_COOKIE_PATH="/",
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_SAMESITE="lax",
        SESSION_TTL_SECONDS=86400,
        DEFAULT_PAGE_SIZE=10,
        MAX_PAGE_SIZE=200,
    )
    app.dependency_overrides[get_check_slug_availability_use_case] = (
        lambda: fake_use_cases.check_slug_availability_use_case
    )
    app.dependency_overrides[get_create_drop_use_case] = (
        lambda: fake_use_cases.create_drop_use_case
    )
    app.dependency_overrides[get_delete_drop_use_case] = (
        lambda: fake_use_cases.delete_drop_use_case
    )
    app.dependency_overrides[get_get_drop_meta_use_case] = (
        lambda: fake_use_cases.get_drop_meta_use_case
    )
    app.dependency_overrides[get_get_drop_stream_source_use_case] = (
        lambda: fake_use_cases.get_drop_stream_source_use_case
    )
    app.dependency_overrides[get_list_drops_use_case] = (
        lambda: fake_use_cases.list_drops_use_case
    )
    app.dependency_overrides[get_update_drop_use_case] = (
        lambda: fake_use_cases.update_drop_use_case
    )
    app.dependency_overrides[get_app_settings] = lambda: fake_settings
    app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
    app.dependency_overrides[get_verify_api_key_use_case] = lambda: _FakeVerifyApiKeyUseCase()
    app.dependency_overrides[get_optional_api_auth] = _fake_optional_api_auth
    app.dependency_overrides[get_required_api_auth] = _fake_required_api_auth
    app.dependency_overrides[get_optional_session_auth] = _fake_optional_session_auth
    app.dependency_overrides[get_revoke_session_use_case] = (
        lambda: revoke_use_case or _FakeRevokeSessionUseCase()
    )
    return TestClient(app)


class TestDropRouterIntegration:
    def test_drop_stream_valid_range_returns_partial_content(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop("k1", payload=b"hello world")
        client = _client(fake_use_cases)

        response = client.get("/api/drop/k1", headers={"Range": "bytes=0-4"})

        assert response.status_code == 206
        assert response.headers["content-range"] == "bytes 0-4/11"
        assert response.headers["content-length"] == "5"
        assert response.content == b"hello"

    def test_drop_stream_invalid_range_returns_400(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop("k1")
        client = _client(fake_use_cases)

        response = client.get("/api/drop/k1", headers={"Range": "items=0-1"})

        assert response.status_code == 400

    def test_drop_stream_unsatisfiable_range_returns_416(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop("k1")
        client = _client(fake_use_cases)

        response = client.get("/api/drop/k1", headers={"Range": "bytes=99-120"})

        assert response.status_code == 416

    def test_drop_stream_invalid_disposition_falls_back_to_attachment(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop("k1")
        client = _client(fake_use_cases)

        response = client.get("/api/drop/k1?disposition=unexpected")

        assert response.status_code == 200
        assert response.headers["content-disposition"].startswith("attachment;")

    @pytest.mark.parametrize(
        ("error", "expected_status"),
        [
            (DropPasswordInvalidError(), 401),
            (DropNotFoundError(), 404),
            (DropAccessDeniedError(), 404),
        ],
    )
    def test_drop_meta_maps_read_errors(self, error: Exception, expected_status: int):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.read_errors[("meta", "k-err")] = error
        client = _client(fake_use_cases)

        response = client.get("/api/drop/k-err/meta")

        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        ("error", "expected_status"),
        [
            (DropPasswordInvalidError(), 401),
            (DropNotFoundError(), 404),
            (DropAccessDeniedError(), 404),
        ],
    )
    def test_drop_stream_maps_read_errors(self, error: Exception, expected_status: int):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.read_errors[("stream", "k-err")] = error
        client = _client(fake_use_cases)

        response = client.get("/api/drop/k-err")

        assert response.status_code == expected_status

    def test_patch_distinguishes_omitted_field_and_explicit_null(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop("k1", title="original")
        client = _client(fake_use_cases)
        client.cookies.set("session_id", "sid")

        omitted = client.patch("/api/drop/k1", json={})
        explicit_null = client.patch("/api/drop/k1", json={"title": None})

        assert omitted.status_code == 200
        assert omitted.json()["title"] == "original"
        assert fake_use_cases.update_commands[0].title is UNSET
        assert fake_use_cases.update_commands[0].auth.user_id == "user-1"

        assert explicit_null.status_code == 200
        assert explicit_null.json()["title"] is None
        assert fake_use_cases.update_commands[1].title is None
        assert fake_use_cases.update_commands[1].auth.user_id == "user-1"

    def test_upload_attaches_authenticated_owner_user_id(self):
        class _CapturingCreateDropUseCase:
            def __init__(self):
                self.command = None

            async def execute(self, command):
                self.command = command
                return _detail_dto(slug=command.slug or "generated")

        fake_use_cases = _FakeDropUseCases()
        create_drop_use_case = _CapturingCreateDropUseCase()
        app = FastAPI()
        app.include_router(api_router, prefix="/api")
        fake_settings = SimpleNamespace(
            SESSION_COOKIE_NAME="session_id",
            SESSION_COOKIE_PATH="/",
            SESSION_COOKIE_SECURE=False,
            SESSION_COOKIE_SAMESITE="lax",
            SESSION_TTL_SECONDS=86400,
            DEFAULT_PAGE_SIZE=10,
            MAX_PAGE_SIZE=200,
        )
        app.dependency_overrides[get_check_slug_availability_use_case] = (
            lambda: fake_use_cases.check_slug_availability_use_case
        )
        app.dependency_overrides[get_create_drop_use_case] = lambda: create_drop_use_case
        app.dependency_overrides[get_delete_drop_use_case] = (
            lambda: fake_use_cases.delete_drop_use_case
        )
        app.dependency_overrides[get_get_drop_meta_use_case] = (
            lambda: fake_use_cases.get_drop_meta_use_case
        )
        app.dependency_overrides[get_get_drop_stream_source_use_case] = (
            lambda: fake_use_cases.get_drop_stream_source_use_case
        )
        app.dependency_overrides[get_list_drops_use_case] = (
            lambda: fake_use_cases.list_drops_use_case
        )
        app.dependency_overrides[get_update_drop_use_case] = (
            lambda: fake_use_cases.update_drop_use_case
        )
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = (
            lambda: _FakeVerifySessionUseCase()
        )
        app.dependency_overrides[get_verify_api_key_use_case] = (
            lambda: _FakeVerifyApiKeyUseCase()
        )
        app.dependency_overrides[get_optional_api_auth] = _fake_optional_api_auth
        app.dependency_overrides[get_required_api_auth] = _fake_required_api_auth
        app.dependency_overrides[get_optional_session_auth] = _fake_optional_session_auth
        client = TestClient(app)
        client.cookies.set("session_id", "sid")

        response = client.post(
            "/api/drop",
            data={"slug": "upload-1", "access_scope": "private"},
            files={"file": ("hello.txt", b"hello", "text/plain")},
        )

        assert response.status_code == 200
        assert create_drop_use_case.command is not None
        assert create_drop_use_case.command.owner_user_id == "user-1"

    def test_delete_ignores_drop_grant_cookie(self):
        class _CapturingDeleteDropUseCase:
            def __init__(self):
                self.command = None

            async def execute(self, command):
                self.command = command

        fake_use_cases = _FakeDropUseCases()
        delete_drop_use_case = _CapturingDeleteDropUseCase()
        app = FastAPI()
        app.include_router(api_router, prefix="/api")
        fake_settings = SimpleNamespace(
            SESSION_COOKIE_NAME="session_id",
            SESSION_COOKIE_PATH="/",
            SESSION_COOKIE_SECURE=False,
            SESSION_COOKIE_SAMESITE="lax",
            SESSION_TTL_SECONDS=86400,
            DEFAULT_PAGE_SIZE=10,
            MAX_PAGE_SIZE=200,
        )
        app.dependency_overrides[get_check_slug_availability_use_case] = (
            lambda: fake_use_cases.check_slug_availability_use_case
        )
        app.dependency_overrides[get_create_drop_use_case] = (
            lambda: fake_use_cases.create_drop_use_case
        )
        app.dependency_overrides[get_delete_drop_use_case] = lambda: delete_drop_use_case
        app.dependency_overrides[get_get_drop_meta_use_case] = (
            lambda: fake_use_cases.get_drop_meta_use_case
        )
        app.dependency_overrides[get_get_drop_stream_source_use_case] = (
            lambda: fake_use_cases.get_drop_stream_source_use_case
        )
        app.dependency_overrides[get_list_drops_use_case] = (
            lambda: fake_use_cases.list_drops_use_case
        )
        app.dependency_overrides[get_update_drop_use_case] = (
            lambda: fake_use_cases.update_drop_use_case
        )
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = (
            lambda: _FakeVerifySessionUseCase()
        )
        app.dependency_overrides[get_verify_api_key_use_case] = (
            lambda: _FakeVerifyApiKeyUseCase()
        )
        app.dependency_overrides[get_optional_api_auth] = _fake_optional_api_auth
        app.dependency_overrides[get_required_api_auth] = _fake_required_api_auth
        app.dependency_overrides[get_optional_session_auth] = _fake_optional_session_auth
        client = TestClient(app)
        client.cookies.set("session_id", "sid")
        client.cookies.set(drop_grant_cookie_name("k1"), "grant-token")

        response = client.delete("/api/drop/k1")

        assert response.status_code == 200
        assert delete_drop_use_case.command is not None
        assert delete_drop_use_case.command.current_password is None
        assert delete_drop_use_case.command.auth.user_id == "user-1"

    @pytest.mark.parametrize("method", ["GET", "POST"])
    def test_logout_clears_session_and_drop_grant_cookies(self, method: str):
        fake_use_cases = _FakeDropUseCases()
        revoke_use_case = _FakeRevokeSessionUseCase()
        client = _client(fake_use_cases, revoke_use_case=revoke_use_case)
        client.cookies.set("session_id", "sid")
        client.cookies.set("tdg_drop_1", "grant-1")
        client.cookies.set("tdg_drop_2", "grant-2")
        client.cookies.set("unrelated", "keep")

        response = client.request(method, "/api/auth/logout")
        set_cookie_headers = response.headers.get_list("set-cookie")

        assert response.status_code == 200
        assert revoke_use_case.calls == ["sid"]
        assert any(header.startswith("session_id=") for header in set_cookie_headers)
        assert any(header.startswith("tdg_drop_1=") for header in set_cookie_headers)
        assert any(header.startswith("tdg_drop_2=") for header in set_cookie_headers)
        assert not any(header.startswith("unrelated=") for header in set_cookie_headers)
