import io
from datetime import datetime, timezone
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.auth.types import AuthIdentity
from app.application.drop.models import DropDetailDTO, DropListDTO, DropListItemDTO, UNSET
from app.bootstrap.container import get_app_settings
from app.bootstrap.providers.auth import get_verify_api_key_use_case, get_verify_session_use_case
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
from app.domain.drop.errors import DropAccessDeniedError, DropNotFoundError, DropPasswordInvalidError
from app.domain.drop.value_objects import AccessScope
from app.interfaces.api.router import api_router


def _credential_matches(expected: str | None, credential) -> bool:
    if expected is None:
        return credential is None or getattr(credential, 'password', None) in (None, '')
    if credential is None:
        return False
    raw_password = getattr(credential, 'password', credential)
    if raw_password == expected:
        return True
    return bool(getattr(credential, 'grant_token', None))


def _is_authenticated(auth) -> bool:
    return bool(auth and getattr(auth, 'user_id', None))


def _is_owner(auth, dto) -> bool:
    return bool(auth and getattr(auth, "user_id", None) == getattr(dto, "owner_user_id", None))


class _FakeVerifySessionUseCase:

    async def execute(self, _query) -> AuthIdentity:
        return AuthIdentity(user_id="user-1", username='tester')


class _FakeVerifyApiKeyUseCase:
    async def execute(self, query) -> AuthIdentity:
        if query.api_key == "tdpk_public_secret":
            return AuthIdentity(user_id="user-1", username="tester")
        raise ApiKeyInvalid()

class _FakeDropUseCases:

    def __init__(self):
        self.items = {}
        self.payloads = {}
        self.check_slug_availability_use_case = self._CheckSlugAvailabilityUseCase(self)
        self.create_drop_use_case = self._CreateDropUseCase(self)
        self.list_drops_use_case = self._ListDropsUseCase(self)
        self.get_drop_meta_use_case = self._GetDropMetaUseCase(self)
        self.get_drop_stream_source_use_case = self._GetDropStreamSourceUseCase(self)
        self.update_drop_use_case = self._UpdateDropUseCase(self)
        self.delete_drop_use_case = self._DeleteDropUseCase(self)

    class _CheckSlugAvailabilityUseCase:

        def __init__(self, parent):
            self.parent = parent

        async def execute(self, slug: str) -> bool:
            return slug not in self.parent.items

    class _CreateDropUseCase:

        def __init__(self, parent):
            self.parent = parent

        async def execute(self, command):
            slug = command.slug or 'generated-key'
            data = command.file_stream.read()
            dto = DropDetailDTO(owner_user_id=command.owner_user_id, slug=slug, title=command.title, description=command.description, file_name=command.file_name, mime_type=command.mime_type, size_bytes=command.size_bytes, access_scope=command.access_scope, is_favorite=False, requires_password=bool(command.drop_password), created_at=datetime.now(timezone.utc), updated_at=None, sha256='sha')
            self.parent.items[slug] = {'dto': dto, 'password': command.drop_password}
            self.parent.payloads[slug] = data
            return dto

    class _ListDropsUseCase:

        def __init__(self, parent):
            self.parent = parent

        async def execute(self, query):
            if not query.auth.user_id:
                raise DropAccessDeniedError()
            items = [DropListItemDTO(owner_user_id=value['dto'].owner_user_id, slug=value['dto'].slug, title=value['dto'].title, description=value['dto'].description, file_name=value['dto'].file_name, mime_type=value['dto'].mime_type, size_bytes=value['dto'].size_bytes, access_scope=value['dto'].access_scope, is_favorite=value['dto'].is_favorite, requires_password=value['dto'].requires_password, created_at=value['dto'].created_at, updated_at=value['dto'].updated_at) for value in self.parent.items.values() if value['dto'].owner_user_id == query.auth.user_id]
            return DropListDTO(items=items, page=query.page, page_size=query.page_size, total=len(items))

    class _GetDropMetaUseCase:

        def __init__(self, parent):
            self.parent = parent

        async def execute(self, query):
            item = self.parent.items.get(query.slug)
            if item is None:
                raise DropNotFoundError()
            expected = item['password']
            dto = item['dto']
            if dto.access_scope == AccessScope.PRIVATE and not _is_owner(query.auth, dto):
                raise DropAccessDeniedError()
            if not _is_owner(query.auth, dto) and not _credential_matches(expected, query.drop_password):
                raise DropPasswordInvalidError()
            return dto

    class _GetDropStreamSourceUseCase:

        def __init__(self, parent):
            self.parent = parent

        async def execute(self, query):
            dto = await self.parent.get_drop_meta_use_case.execute(query)
            return (dto, query.slug)

        async def iter_stream_range(self, storage_key, start, end):
            payload = self.parent.payloads[storage_key]
            yield payload[start:end + 1]

    class _UpdateDropUseCase:

        def __init__(self, parent):
            self.parent = parent

        async def execute(self, command):
            item = self.parent.items.get(command.slug)
            if item is None:
                raise DropNotFoundError()
            dto = item['dto']
            if not _is_owner(command.auth, dto):
                raise DropAccessDeniedError()
            if command.title is not UNSET:
                dto.title = command.title
            if command.description is not UNSET:
                dto.description = command.description
            if command.access_scope is not UNSET:
                dto.access_scope = command.access_scope
            if command.is_favorite is not UNSET:
                dto.is_favorite = command.is_favorite
            if command.new_password is not UNSET:
                item['password'] = command.new_password
            return dto

    class _DeleteDropUseCase:

        def __init__(self, parent):
            self.parent = parent

        async def execute(self, command):
            item = self.parent.items.get(command.slug)
            if item is None:
                raise DropNotFoundError()
            if not _is_owner(command.auth, item['dto']):
                raise DropAccessDeniedError()
            self.parent.items.pop(command.slug, None)
            self.parent.payloads.pop(command.slug, None)

class TestApiSmoke:

    def test_drop_crud_flow(self):
        app = FastAPI()
        app.include_router(api_router, prefix='/api')
        fake_use_cases = _FakeDropUseCases()
        fake_settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id', SESSION_COOKIE_PATH='/', SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='lax', SESSION_TTL_SECONDS=86400, DEFAULT_PAGE_SIZE=10, MAX_PAGE_SIZE=200, MAX_UPLOAD_BYTES=1024 * 1024)
        app.dependency_overrides[get_check_slug_availability_use_case] = lambda: fake_use_cases.check_slug_availability_use_case
        app.dependency_overrides[get_create_drop_use_case] = lambda: fake_use_cases.create_drop_use_case
        app.dependency_overrides[get_delete_drop_use_case] = lambda: fake_use_cases.delete_drop_use_case
        app.dependency_overrides[get_get_drop_meta_use_case] = lambda: fake_use_cases.get_drop_meta_use_case
        app.dependency_overrides[get_get_drop_stream_source_use_case] = lambda: fake_use_cases.get_drop_stream_source_use_case
        app.dependency_overrides[get_list_drops_use_case] = lambda: fake_use_cases.list_drops_use_case
        app.dependency_overrides[get_update_drop_use_case] = lambda: fake_use_cases.update_drop_use_case
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
        app.dependency_overrides[get_verify_api_key_use_case] = lambda: _FakeVerifyApiKeyUseCase()
        client = TestClient(app)
        client.cookies.set('session_id', 'sid')
        headers = {"X-API-Key": "tdpk_public_secret"}
        available_before_upload = client.get('/api/drop/availability/k1')
        assert available_before_upload.status_code == 200
        assert available_before_upload.json()['available']
        upload = client.post('/api/drop', headers=headers, data={'slug': 'k1', 'access_scope': 'private', 'drop_password': 'pw'}, files={'file': ('hello.txt', io.BytesIO(b'hello world'), 'text/plain')})
        assert upload.status_code == 200
        assert upload.json()['slug'] == 'k1'
        assert 'key' not in upload.json()
        available_after_upload = client.get('/api/drop/availability/k1')
        assert available_after_upload.status_code == 200
        assert not available_after_upload.json()['available']
        listed = client.get('/api/drop')
        assert listed.status_code == 200
        assert listed.json()['total'] == 1
        assert listed.json()['items'][0]['slug'] == 'k1'
        assert 'key' not in listed.json()['items'][0]
        patched = client.patch('/api/drop/k1', headers=headers, json={'title': 'updated'})
        assert patched.status_code == 200
        assert patched.json()['title'] == 'updated'
        assert patched.json()['slug'] == 'k1'
        streamed = client.get('/api/drop/k1', headers={'X-Drop-Password': 'pw'})
        assert streamed.status_code == 200
        assert streamed.content == b'hello world'
        assert streamed.headers['content-disposition'].startswith('attachment;')
        assert streamed.headers['x-content-type-options'] == 'nosniff'
        deleted = client.delete('/api/drop/k1', headers=headers)
        assert deleted.status_code == 200

    def test_auth_unauthorized_response_includes_session_headers(self):
        app = FastAPI()
        app.include_router(api_router, prefix='/api')
        fake_use_cases = _FakeDropUseCases()
        fake_settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id', SESSION_COOKIE_PATH='/', SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='lax', SESSION_TTL_SECONDS=86400, DEFAULT_PAGE_SIZE=10, MAX_PAGE_SIZE=200, MAX_UPLOAD_BYTES=1024 * 1024)
        app.dependency_overrides[get_check_slug_availability_use_case] = lambda: fake_use_cases.check_slug_availability_use_case
        app.dependency_overrides[get_create_drop_use_case] = lambda: fake_use_cases.create_drop_use_case
        app.dependency_overrides[get_delete_drop_use_case] = lambda: fake_use_cases.delete_drop_use_case
        app.dependency_overrides[get_get_drop_meta_use_case] = lambda: fake_use_cases.get_drop_meta_use_case
        app.dependency_overrides[get_get_drop_stream_source_use_case] = lambda: fake_use_cases.get_drop_stream_source_use_case
        app.dependency_overrides[get_list_drops_use_case] = lambda: fake_use_cases.list_drops_use_case
        app.dependency_overrides[get_update_drop_use_case] = lambda: fake_use_cases.update_drop_use_case
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
        app.dependency_overrides[get_verify_api_key_use_case] = lambda: _FakeVerifyApiKeyUseCase()
        client = TestClient(app)
        response = client.get('/api/drop')
        assert response.status_code == 401
        assert response.headers.get('www-authenticate') == 'Session, ApiKey'
        assert 'session_id=' in response.headers.get('set-cookie', '')

    def test_owner_delete_bypasses_drop_password(self):
        app = FastAPI()
        app.include_router(api_router, prefix='/api')
        fake_use_cases = _FakeDropUseCases()
        fake_settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id', SESSION_COOKIE_PATH='/', SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='lax', SESSION_TTL_SECONDS=86400, DEFAULT_PAGE_SIZE=10, MAX_PAGE_SIZE=200, MAX_UPLOAD_BYTES=1024 * 1024)
        app.dependency_overrides[get_check_slug_availability_use_case] = lambda: fake_use_cases.check_slug_availability_use_case
        app.dependency_overrides[get_create_drop_use_case] = lambda: fake_use_cases.create_drop_use_case
        app.dependency_overrides[get_delete_drop_use_case] = lambda: fake_use_cases.delete_drop_use_case
        app.dependency_overrides[get_get_drop_meta_use_case] = lambda: fake_use_cases.get_drop_meta_use_case
        app.dependency_overrides[get_get_drop_stream_source_use_case] = lambda: fake_use_cases.get_drop_stream_source_use_case
        app.dependency_overrides[get_list_drops_use_case] = lambda: fake_use_cases.list_drops_use_case
        app.dependency_overrides[get_update_drop_use_case] = lambda: fake_use_cases.update_drop_use_case
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
        app.dependency_overrides[get_verify_api_key_use_case] = lambda: _FakeVerifyApiKeyUseCase()
        client = TestClient(app)
        client.cookies.set('session_id', 'sid')
        headers = {"X-API-Key": "tdpk_public_secret"}
        upload = client.post('/api/drop', headers=headers, data={'slug': 'k-grant', 'access_scope': 'private', 'drop_password': 'pw'}, files={'file': ('hello.txt', io.BytesIO(b'hello world'), 'text/plain')})
        assert upload.status_code == 200
        client.cookies.set(drop_grant_cookie_name('k-grant'), 'grant-token')

        deleted = client.delete('/api/drop/k-grant', headers=headers)

        assert deleted.status_code == 200

    def test_owner_read_bypasses_drop_password(self):
        app = FastAPI()
        app.include_router(api_router, prefix='/api')
        fake_use_cases = _FakeDropUseCases()
        fake_settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id', SESSION_COOKIE_PATH='/', SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='lax', SESSION_TTL_SECONDS=86400, DEFAULT_PAGE_SIZE=10, MAX_PAGE_SIZE=200, MAX_UPLOAD_BYTES=1024 * 1024)
        app.dependency_overrides[get_check_slug_availability_use_case] = lambda: fake_use_cases.check_slug_availability_use_case
        app.dependency_overrides[get_create_drop_use_case] = lambda: fake_use_cases.create_drop_use_case
        app.dependency_overrides[get_delete_drop_use_case] = lambda: fake_use_cases.delete_drop_use_case
        app.dependency_overrides[get_get_drop_meta_use_case] = lambda: fake_use_cases.get_drop_meta_use_case
        app.dependency_overrides[get_get_drop_stream_source_use_case] = lambda: fake_use_cases.get_drop_stream_source_use_case
        app.dependency_overrides[get_list_drops_use_case] = lambda: fake_use_cases.list_drops_use_case
        app.dependency_overrides[get_update_drop_use_case] = lambda: fake_use_cases.update_drop_use_case
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
        app.dependency_overrides[get_verify_api_key_use_case] = lambda: _FakeVerifyApiKeyUseCase()
        client = TestClient(app)
        client.cookies.set('session_id', 'sid')
        upload = client.post('/api/drop', headers={"X-API-Key": "tdpk_public_secret"}, data={'slug': 'k-auth', 'access_scope': 'private', 'drop_password': 'pw'}, files={'file': ('hello.txt', io.BytesIO(b'hello world'), 'text/plain')})
        assert upload.status_code == 200

        meta = client.get('/api/drop/k-auth/meta')
        streamed = client.get('/api/drop/k-auth')

        assert meta.status_code == 200
        assert streamed.status_code == 200
        assert streamed.content == b'hello world'

    def test_drop_crud_flow_with_api_key(self):
        app = FastAPI()
        app.include_router(api_router, prefix='/api')
        fake_use_cases = _FakeDropUseCases()
        fake_settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id', SESSION_COOKIE_PATH='/', SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='lax', SESSION_TTL_SECONDS=86400, DEFAULT_PAGE_SIZE=10, MAX_PAGE_SIZE=200, MAX_UPLOAD_BYTES=1024 * 1024)
        app.dependency_overrides[get_check_slug_availability_use_case] = lambda: fake_use_cases.check_slug_availability_use_case
        app.dependency_overrides[get_create_drop_use_case] = lambda: fake_use_cases.create_drop_use_case
        app.dependency_overrides[get_delete_drop_use_case] = lambda: fake_use_cases.delete_drop_use_case
        app.dependency_overrides[get_get_drop_meta_use_case] = lambda: fake_use_cases.get_drop_meta_use_case
        app.dependency_overrides[get_get_drop_stream_source_use_case] = lambda: fake_use_cases.get_drop_stream_source_use_case
        app.dependency_overrides[get_list_drops_use_case] = lambda: fake_use_cases.list_drops_use_case
        app.dependency_overrides[get_update_drop_use_case] = lambda: fake_use_cases.update_drop_use_case
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
        app.dependency_overrides[get_verify_api_key_use_case] = lambda: _FakeVerifyApiKeyUseCase()
        client = TestClient(app)

        headers = {"X-API-Key": "tdpk_public_secret"}
        upload = client.post('/api/drop', headers=headers, data={'slug': 'k2', 'access_scope': 'private', 'drop_password': 'pw'}, files={'file': ('hello.txt', io.BytesIO(b'hello world'), 'text/plain')})
        assert upload.status_code == 200

        listed = client.get('/api/drop', headers=headers)
        assert listed.status_code == 200
        assert listed.json()['total'] == 1

        patched = client.patch('/api/drop/k2', headers=headers, json={'title': 'updated'})
        assert patched.status_code == 200

        deleted = client.delete('/api/drop/k2', headers=headers)
        assert deleted.status_code == 200

    def test_auth_me_accepts_api_key(self):
        app = FastAPI()
        app.include_router(api_router, prefix='/api')
        fake_settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id', SESSION_COOKIE_PATH='/', SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='lax', SESSION_TTL_SECONDS=86400, DEFAULT_PAGE_SIZE=10, MAX_PAGE_SIZE=200, MAX_UPLOAD_BYTES=1024 * 1024)
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
        app.dependency_overrides[get_verify_api_key_use_case] = lambda: _FakeVerifyApiKeyUseCase()
        client = TestClient(app)

        response = client.get('/api/auth/me', headers={"X-API-Key": "tdpk_public_secret"})
        assert response.status_code == 200
        assert response.json() == {"user_id": "user-1", "username": "tester"}
