import io
from datetime import datetime, timezone
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.application.drop.models import DropDetailDTO, DropListDTO, DropListItemDTO, UNSET
from app.bootstrap.container import get_app_settings
from app.domain.drop.errors import DropAccessDeniedError, DropNotFoundError, DropPasswordInvalidError
from app.domain.drop.value_objects import AccessScope
from app.interfaces.api.dependencies import get_drop_use_cases, get_verify_session_use_case
from app.interfaces.api.router import api_router

class _FakeVerifySessionUseCase:

    async def execute(self, _query) -> str:
        return 'tester'

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
            dto = DropDetailDTO(slug=slug, title=command.title, description=command.description, file_name=command.file_name, mime_type=command.mime_type, size_bytes=command.size_bytes, access_scope=command.access_scope, is_favorite=False, requires_password=bool(command.drop_password), created_at=datetime.now(timezone.utc), updated_at=None, sha256='sha')
            self.parent.items[slug] = {'dto': dto, 'password': command.drop_password}
            self.parent.payloads[slug] = data
            return dto

    class _ListDropsUseCase:

        def __init__(self, parent):
            self.parent = parent

        async def execute(self, query):
            if not query.auth.username:
                raise DropAccessDeniedError()
            items = [DropListItemDTO(slug=value['dto'].slug, title=value['dto'].title, description=value['dto'].description, file_name=value['dto'].file_name, mime_type=value['dto'].mime_type, size_bytes=value['dto'].size_bytes, access_scope=value['dto'].access_scope, is_favorite=value['dto'].is_favorite, requires_password=value['dto'].requires_password, created_at=value['dto'].created_at, updated_at=value['dto'].updated_at) for value in self.parent.items.values()]
            return DropListDTO(items=items, page=query.page, page_size=query.page_size, total=len(items))

    class _GetDropMetaUseCase:

        def __init__(self, parent):
            self.parent = parent

        async def execute(self, query):
            item = self.parent.items.get(query.slug)
            if item is None:
                raise DropNotFoundError()
            expected = item['password']
            if expected and expected != query.drop_password:
                raise DropPasswordInvalidError()
            return item['dto']

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
            expected = item['password']
            if expected and expected != command.current_password:
                raise DropPasswordInvalidError()
            dto = item['dto']
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
            expected = item['password']
            if expected and expected != command.current_password:
                raise DropPasswordInvalidError()
            self.parent.items.pop(command.slug, None)
            self.parent.payloads.pop(command.slug, None)

class TestApiSmoke:

    def test_drop_crud_flow(self):
        app = FastAPI()
        app.include_router(api_router, prefix='/api')
        fake_use_cases = _FakeDropUseCases()
        fake_settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id', SESSION_COOKIE_PATH='/', SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='lax', SESSION_TTL_SECONDS=86400, DEFAULT_PAGE_SIZE=10, MAX_PAGE_SIZE=200)
        app.dependency_overrides[get_drop_use_cases] = lambda: fake_use_cases
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
        client = TestClient(app)
        client.cookies.set('session_id', 'sid')
        available_before_upload = client.get('/api/drop/availability/k1')
        assert available_before_upload.status_code == 200
        assert available_before_upload.json()['available']
        upload = client.post('/api/drop', data={'slug': 'k1', 'access_scope': 'private', 'drop_password': 'pw'}, files={'file': ('hello.txt', io.BytesIO(b'hello world'), 'text/plain')})
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
        patched = client.patch('/api/drop/k1', json={'title': 'updated', 'current_password': 'pw'})
        assert patched.status_code == 200
        assert patched.json()['title'] == 'updated'
        assert patched.json()['slug'] == 'k1'
        streamed = client.get('/api/drop/k1?disposition=inline&drop_password=pw')
        assert streamed.status_code == 200
        assert streamed.content == b'hello world'
        deleted = client.delete('/api/drop/k1?current_password=pw')
        assert deleted.status_code == 200

    def test_auth_unauthorized_response_includes_session_headers(self):
        app = FastAPI()
        app.include_router(api_router, prefix='/api')
        fake_use_cases = _FakeDropUseCases()
        fake_settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id', SESSION_COOKIE_PATH='/', SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='lax', SESSION_TTL_SECONDS=86400, DEFAULT_PAGE_SIZE=10, MAX_PAGE_SIZE=200)
        app.dependency_overrides[get_drop_use_cases] = lambda: fake_use_cases
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
        client = TestClient(app)
        response = client.get('/api/drop')
        assert response.status_code == 401
        assert response.headers.get('www-authenticate') == 'Session'
        assert 'session_id=' in response.headers.get('set-cookie', '')
