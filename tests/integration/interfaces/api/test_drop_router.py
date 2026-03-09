from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.drop.models import DropDetailDTO, UNSET
from app.bootstrap.container import get_app_settings
from app.domain.auth.errors import ApiKeyInvalid
from app.domain.drop.errors import (
    DropAccessDeniedError,
    DropNotFoundError,
    DropPasswordInvalidError,
)
from app.domain.drop.value_objects import AccessScope
from app.interfaces.api.deps import get_verify_api_key_use_case, get_verify_session_use_case
from app.interfaces.deps.drop import (
    get_check_slug_availability_use_case,
    get_create_drop_use_case,
    get_delete_drop_use_case,
    get_get_drop_meta_use_case,
    get_get_drop_stream_source_use_case,
    get_list_drops_use_case,
    get_update_drop_use_case,
)
from app.interfaces.api.router import api_router


class _FakeVerifySessionUseCase:
    async def execute(self, _query) -> str:
        return "tester"


class _FakeVerifyApiKeyUseCase:
    async def execute(self, query) -> str:
        if query.api_key == "tdpk_public_secret":
            return "tester"
        raise ApiKeyInvalid()


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


def _client(fake_use_cases: _FakeDropUseCases) -> TestClient:
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

        assert explicit_null.status_code == 200
        assert explicit_null.json()["title"] is None
        assert fake_use_cases.update_commands[1].title is None
