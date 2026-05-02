from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.auth.types import AuthIdentity
from app.application.drop.models import DropDetailDTO
from app.bootstrap.container import get_app_settings
from app.bootstrap.providers.auth import (
    get_verify_api_key_use_case,
)
from app.bootstrap.providers.drop import (
    get_create_drop_use_case,
    get_get_drop_meta_use_case,
    get_get_drop_stream_source_use_case,
    get_list_drops_use_case,
)
from app.domain.auth.errors import ApiKeyInvalid
from app.domain.drop.errors import (
    DropAccessDeniedError,
    DropNotFoundError,
    DropPasswordInvalidError,
    DropUploadTooLargeError,
)
from app.domain.drop.value_objects import AccessScope
from app.interfaces.api.router import api_router


class _FakeVerifyApiKeyUseCase:
    async def execute(self, query) -> AuthIdentity:
        if query.api_key == "tdpk_public_secret":
            return _auth_identity()
        if query.api_key == "tdpk_other_secret":
            return AuthIdentity(user_id="user-2", username="other")
        raise ApiKeyInvalid()


def _auth_identity() -> AuthIdentity:
    return AuthIdentity(user_id="user-1", username="tester")


def _api_headers(token: str = "tdpk_public_secret") -> dict[str, str]:
    return {"X-API-Key": token}


def _credential_matches(expected: str | None, credential) -> bool:
    if expected is None:
        return True
    return bool(credential and getattr(credential, "password", None) == expected)


def _detail_dto(
    *,
    slug: str,
    title: str | None = "original",
    file_name: str | None = None,
    mime_type: str = "text/plain",
    payload_size: int = 11,
    access_scope: AccessScope = AccessScope.PUBLIC,
    requires_password: bool = False,
    owner_user_id: str = "user-1",
) -> DropDetailDTO:
    now = datetime.now(timezone.utc)
    return DropDetailDTO(
        owner_user_id=owner_user_id,
        slug=slug,
        title=title,
        description="desc",
        file_name=file_name or f"{slug}.txt",
        mime_type=mime_type,
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
        self.passwords: dict[str, str | None] = {}
        self.read_errors: dict[tuple[str, str], Exception] = {}

        self.check_slug_availability_use_case = self._NotUsedUseCase()
        self.create_drop_use_case = self._NotUsedUseCase()
        self.list_drops_use_case = self._NotUsedUseCase()
        self.get_drop_meta_use_case = self._GetDropMetaUseCase(self)
        self.get_drop_stream_source_use_case = self._GetDropStreamSourceUseCase(self)

    def add_drop(
        self,
        slug: str,
        *,
        payload: bytes = b"hello world",
        title: str | None = "original",
        file_name: str | None = None,
        mime_type: str = "text/plain",
        access_scope: AccessScope = AccessScope.PUBLIC,
        owner_user_id: str = "user-1",
        drop_password: str | None = None,
    ) -> None:
        self.items[slug] = _detail_dto(
            slug=slug,
            title=title,
            file_name=file_name,
            mime_type=mime_type,
            payload_size=len(payload),
            access_scope=access_scope,
            requires_password=drop_password is not None,
            owner_user_id=owner_user_id,
        )
        self.payloads[slug] = payload
        self.passwords[slug] = drop_password

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
            if item.access_scope == AccessScope.PRIVATE and query.auth.user_id != item.owner_user_id:
                raise DropAccessDeniedError()
            if query.auth.user_id != item.owner_user_id and not _credential_matches(
                self.parent.passwords.get(query.slug),
                query.drop_password,
            ):
                raise DropPasswordInvalidError()
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
            await self.parent.get_drop_meta_use_case.execute(query)
            return item, query.slug

        async def iter_stream_range(self, storage_key: str, start: int, end: int):
            payload = self.parent.payloads[storage_key]
            yield payload[start : end + 1]

def _client(
    fake_use_cases: _FakeDropUseCases,
    max_upload_bytes: int = 1024 * 1024,
    authenticated: bool = True,
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
        MAX_UPLOAD_BYTES=max_upload_bytes,
    )
    app.dependency_overrides[get_create_drop_use_case] = (
        lambda: fake_use_cases.create_drop_use_case
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
    app.dependency_overrides[get_app_settings] = lambda: fake_settings
    app.dependency_overrides[get_verify_api_key_use_case] = lambda: _FakeVerifyApiKeyUseCase()
    client = TestClient(app)
    if authenticated:
        client.headers.update(_api_headers())
    return client


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
        assert response.headers["content-range"] == "bytes */11"

    def test_drop_stream_uses_attachment_content_disposition(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop("k1")
        client = _client(fake_use_cases)

        response = client.get("/api/drop/k1")

        assert response.status_code == 200
        assert response.headers["content-disposition"] == (
            "attachment; filename=\"k1.txt\"; filename*=UTF-8''k1.txt"
        )
        assert "content-disposition" in response.headers["access-control-expose-headers"]

    def test_drop_stream_sanitizes_path_like_content_disposition_filename(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop("path", file_name="../secret\\report.pdf")
        client = _client(fake_use_cases)

        response = client.get("/api/drop/path")

        assert response.status_code == 200
        assert response.headers["content-disposition"] == (
            "attachment; filename=\"report.pdf\"; filename*=UTF-8''report.pdf"
        )

    def test_drop_stream_allows_inline_disposition_for_safe_image_preview(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop(
            "photo",
            payload=b"fake-png",
            file_name="photo.png",
            mime_type="image/png",
        )
        client = _client(fake_use_cases)

        response = client.get("/api/drop/photo?disposition=inline")

        assert response.status_code == 200
        assert response.headers["content-disposition"].startswith("inline;")
        assert response.headers["content-type"].startswith("image/png")

    def test_drop_stream_allows_inline_disposition_for_pdf_preview(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop(
            "guide",
            payload=b"%PDF-1.7",
            file_name="guide.pdf",
            mime_type="application/pdf",
        )
        client = _client(fake_use_cases)

        response = client.get("/api/drop/guide?disposition=inline")

        assert response.status_code == 200
        assert response.headers["content-disposition"].startswith("inline;")
        assert response.headers["content-type"].startswith("application/pdf")

    def test_drop_stream_allows_inline_disposition_for_video_preview(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop(
            "clip",
            payload=b"fake-mp4",
            file_name="clip.mp4",
            mime_type="video/mp4",
        )
        client = _client(fake_use_cases)

        response = client.get("/api/drop/clip?disposition=inline")

        assert response.status_code == 200
        assert response.headers["content-disposition"].startswith("inline;")
        assert response.headers["content-type"].startswith("video/mp4")

    def test_drop_stream_serves_video_preview_range_as_partial_content(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop(
            "clip",
            payload=b"fake-mp4",
            file_name="clip.mp4",
            mime_type="video/mp4",
        )
        client = _client(fake_use_cases)

        response = client.get(
            "/api/drop/clip?disposition=inline",
            headers={"Range": "bytes=0-3"},
        )

        assert response.status_code == 206
        assert response.headers["content-disposition"].startswith("inline;")
        assert response.headers["content-type"].startswith("video/mp4")
        assert response.headers["accept-ranges"] == "bytes"
        assert response.headers["content-range"] == "bytes 0-3/8"
        assert response.headers["content-length"] == "4"
        assert response.content == b"fake"

    def test_drop_stream_keeps_unsafe_inline_preview_requests_as_attachment(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop(
            "html",
            payload=b"<script>alert(1)</script>",
            file_name="index.html",
            mime_type="text/html",
        )
        client = _client(fake_use_cases)

        response = client.get("/api/drop/html?disposition=inline")

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

    @pytest.mark.parametrize(
        ("method", "path", "expected_status"),
        [
            ("get", "/api/drop/availability/k1", 404),
            ("patch", "/api/drop/k1", 405),
            ("delete", "/api/drop/k1", 405),
            ("post", "/api/auth/login", 404),
            ("get", "/api/auth/me", 404),
            ("post", "/api/auth/logout", 404),
        ],
    )
    def test_removed_rest_surface_is_not_registered(
        self,
        method: str,
        path: str,
        expected_status: int,
    ):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop("k1")
        client = _client(fake_use_cases)

        response = getattr(client, method)(path)

        assert response.status_code == expected_status

    @pytest.mark.parametrize("method", ["get", "post"])
    def test_rest_api_rejects_session_cookie_without_api_key(self, method: str):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop("k1")
        client = _client(fake_use_cases, authenticated=False)
        client.cookies.set("session_id", "sid")

        if method == "get":
            response = client.get("/api/drop")
        else:
            response = client.post(
                "/api/drop",
                data={"slug": "upload-1", "access_scope": "private"},
                files={"file": ("hello.txt", b"hello", "text/plain")},
            )

        assert response.status_code == 401
        assert response.headers.get("www-authenticate") == "ApiKey"
        assert response.headers.get("set-cookie") is None

    def test_rest_api_rejects_invalid_api_key_without_clearing_session_cookie(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop("k1")
        client = _client(fake_use_cases, authenticated=False)
        client.cookies.set("session_id", "sid")

        response = client.get(
            "/api/drop",
            headers={"X-API-Key": "tdpk_public_wrong"},
        )

        assert response.status_code == 401
        assert response.headers.get("www-authenticate") == "ApiKey"
        assert response.headers.get("set-cookie") is None

    def test_upload_rejects_file_larger_than_configured_limit(self):
        fake_use_cases = _FakeDropUseCases()
        client = _client(fake_use_cases, max_upload_bytes=4)

        response = client.post(
            "/api/drop",
            headers={"X-API-Key": "tdpk_public_secret"},
            data={"slug": "too-large", "access_scope": "private"},
            files={"file": ("hello.txt", b"hello", "text/plain")},
        )

        assert response.status_code == 413

    def test_upload_maps_stream_write_size_limit_error_to_413(self):
        class _TooLargeCreateDropUseCase:
            async def execute(self, _command):
                raise DropUploadTooLargeError()

        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.create_drop_use_case = _TooLargeCreateDropUseCase()
        client = _client(fake_use_cases)

        response = client.post(
            "/api/drop",
            headers={"X-API-Key": "tdpk_public_secret"},
            data={"slug": "too-large", "access_scope": "private"},
            files={"file": ("hello.txt", b"hello", "text/plain")},
        )

        assert response.status_code == 413

    def test_upload_attaches_authenticated_owner_user_id(self):
        class _CapturingCreateDropUseCase:
            def __init__(self):
                self.command = None

            async def execute(self, command):
                self.command = command
                return _detail_dto(slug=command.slug or "generated")

        fake_use_cases = _FakeDropUseCases()
        create_drop_use_case = _CapturingCreateDropUseCase()
        fake_use_cases.create_drop_use_case = create_drop_use_case
        client = _client(fake_use_cases)

        response = client.post(
            "/api/drop",
            data={"slug": "upload-1", "access_scope": "private"},
            files={"file": ("hello.txt", b"hello", "text/plain")},
        )

        assert response.status_code == 200
        assert create_drop_use_case.command is not None
        assert create_drop_use_case.command.owner_user_id == "user-1"

    def test_api_key_can_read_public_non_owner_drop(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop(
            "public-other",
            payload=b"public",
            access_scope=AccessScope.PUBLIC,
            owner_user_id="user-2",
        )
        client = _client(fake_use_cases)

        meta = client.get("/api/drop/public-other/meta")
        streamed = client.get("/api/drop/public-other")

        assert meta.status_code == 200
        assert meta.json()["slug"] == "public-other"
        assert streamed.status_code == 200
        assert streamed.content == b"public"

    def test_api_key_cannot_read_private_non_owner_drop(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop(
            "private-other",
            access_scope=AccessScope.PRIVATE,
            owner_user_id="user-2",
        )
        client = _client(fake_use_cases)

        response = client.get("/api/drop/private-other")

        assert response.status_code == 404

    def test_api_key_requires_drop_password_for_protected_public_non_owner_drop(self):
        fake_use_cases = _FakeDropUseCases()
        fake_use_cases.add_drop(
            "protected-public",
            payload=b"protected",
            access_scope=AccessScope.PUBLIC,
            owner_user_id="user-2",
            drop_password="pw",
        )
        client = _client(fake_use_cases)

        without_password = client.get("/api/drop/protected-public")
        with_password = client.get(
            "/api/drop/protected-public",
            headers=_api_headers() | {"X-Drop-Password": "pw"},
        )

        assert without_password.status_code == 401
        assert with_password.status_code == 200
        assert with_password.content == b"protected"
