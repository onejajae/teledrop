import io
from datetime import datetime, timezone
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.application.drop.models import DropDetailDTO, DropListDTO, DropListItemDTO, UNSET
from app.bootstrap.container import get_app_settings
from app.domain.drop.errors import DropNotFoundError, DropPasswordInvalidError
from app.domain.drop.value_objects import AccessScope
from app.interfaces.api.dependencies import get_csrf_token_service, get_drop_use_cases, get_revoke_session_use_case, get_verify_session_use_case
from app.interfaces.web.router import router as web_router

class _FakeVerifySessionUseCase:

    async def execute(self, _query) -> str:
        return 'tester'

class _FakeCsrfService:

    def verify(self, _session_id: str, csrf_token: str | None) -> bool:
        return csrf_token == 'csrf'

    def generate(self, _session_id: str) -> str:
        return 'csrf'

class _FakeRevokeSessionUseCase:

    async def execute(self, _sid: str):
        return None

class _FakeDropUseCases:

    def __init__(self):
        self.items = {}
        self.check_slug_availability_use_case = self._CheckSlugAvailabilityUseCase(self)
        self.create_drop_use_case = self._CreateDropUseCase(self)
        self.list_drops_use_case = self._ListDropsUseCase(self)
        self.get_drop_meta_use_case = self._GetDropMetaUseCase(self)
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
            dto = DropDetailDTO(slug=command.slug, title=command.title, description=command.description, file_name=command.file_name, mime_type=command.mime_type, size_bytes=command.size_bytes, access_scope=command.access_scope, is_favorite=False, requires_password=bool(command.drop_password), created_at=datetime.now(timezone.utc), updated_at=None, sha256='sha')
            self.parent.items[dto.slug] = {'dto': dto, 'password': command.drop_password}
            return dto

    class _ListDropsUseCase:

        def __init__(self, parent):
            self.parent = parent

        async def execute(self, _query):
            items = [DropListItemDTO(slug=value['dto'].slug, title=value['dto'].title, description=value['dto'].description, file_name=value['dto'].file_name, mime_type=value['dto'].mime_type, size_bytes=value['dto'].size_bytes, access_scope=value['dto'].access_scope, is_favorite=value['dto'].is_favorite, requires_password=value['dto'].requires_password, created_at=value['dto'].created_at, updated_at=value['dto'].updated_at) for value in self.parent.items.values()]
            return DropListDTO(items=items, page=1, page_size=200, total=len(items))

    class _GetDropMetaUseCase:

        def __init__(self, parent):
            self.parent = parent

        async def execute_for_display(self, slug, _auth):
            item = self.parent.items.get(slug)
            if item is None:
                raise DropNotFoundError()
            return item['dto']

        async def execute(self, query):
            item = self.parent.items.get(query.slug)
            if item is None:
                raise DropNotFoundError()
            expected = item['password']
            if expected and expected != query.drop_password:
                raise DropPasswordInvalidError()
            return item['dto']

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

class TestWebActionsSmoke:

    def test_htmx_upload_update_delete_and_logout(self):
        app = FastAPI()
        app.include_router(web_router)
        fake_use_cases = _FakeDropUseCases()
        fake_settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id', SESSION_COOKIE_PATH='/', SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='lax', SESSION_TTL_SECONDS=86400, DEFAULT_PAGE_SIZE=10, MAX_PAGE_SIZE=200)
        app.dependency_overrides[get_drop_use_cases] = lambda: fake_use_cases
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
        app.dependency_overrides[get_csrf_token_service] = lambda: _FakeCsrfService()
        app.dependency_overrides[get_revoke_session_use_case] = lambda: _FakeRevokeSessionUseCase()
        client = TestClient(app)
        headers = {'HX-Request': 'true'}
        client.cookies.set('session_id', 'sid')
        upload = client.post('/actions/drop/upload', headers=headers, data={'csrf_token': 'csrf', 'slug': 'kweb', 'user_only': 'true'}, files={'file': ('hello.txt', io.BytesIO(b'hello'), 'text/plain')})
        assert upload.status_code == 200
        assert upload.headers.get('HX-Trigger') == 'drop-list-refresh'
        update = client.post('/actions/drop/kweb/detail', headers=headers, data={'csrf_token': 'csrf', 'title': 'new-title', 'password': ''})
        assert update.status_code == 200
        delete = client.post('/actions/drop/kweb/delete', headers=headers, data={'csrf_token': 'csrf', 'password': ''})
        assert delete.status_code == 200
        logout = client.post('/actions/auth/logout', headers=headers, data={'csrf_token': 'csrf'})
        assert logout.status_code == 204
        assert logout.headers.get('HX-Redirect') == '/'
