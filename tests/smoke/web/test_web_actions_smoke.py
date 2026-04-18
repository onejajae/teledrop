from datetime import datetime, timezone
import io
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.drop.models import DropDetailDTO, DropListDTO, DropListItemDTO, UNSET
from app.bootstrap.container import get_app_settings, get_csrf_token_service
from app.bootstrap.providers.auth import get_revoke_session_use_case, get_verify_session_use_case
from app.bootstrap.providers.drop import (
    get_create_drop_use_case,
    get_delete_drop_use_case,
    get_get_drop_meta_use_case,
    get_list_drops_use_case,
    get_update_drop_use_case,
)
from app.domain.drop.errors import DropNotFoundError, DropPasswordInvalidError
from app.domain.drop.value_objects import AccessScope
from app.interfaces.web.router import router as web_router


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
    return bool(auth and getattr(auth, 'username', None))


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

        async def execute_for_display(self, slug, auth=None):
            _ = auth
            item = self.parent.items.get(slug)
            if item is None:
                raise DropNotFoundError()
            return item['dto']

        async def execute(self, query):
            item = self.parent.items.get(query.slug)
            if item is None:
                raise DropNotFoundError()
            expected = item['password']
            if not _is_authenticated(query.auth) and not _credential_matches(expected, query.drop_password):
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
            if not getattr(command, 'bypass_password_check', False) and not _credential_matches(expected, command.current_password):
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
                dto.requires_password = bool(command.new_password)
            return dto

    class _DeleteDropUseCase:

        def __init__(self, parent):
            self.parent = parent

        async def execute(self, command):
            item = self.parent.items.get(command.slug)
            if item is None:
                raise DropNotFoundError()
            expected = item['password']
            if not getattr(command, 'bypass_password_check', False) and not _credential_matches(expected, command.current_password):
                raise DropPasswordInvalidError()
            self.parent.items.pop(command.slug, None)

class TestWebActionsSmoke:

    def test_htmx_upload_update_delete_and_logout(self):
        app = FastAPI()
        app.include_router(web_router)
        fake_use_cases = _FakeDropUseCases()
        fake_settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id', SESSION_COOKIE_PATH='/', SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='lax', SESSION_TTL_SECONDS=86400, CSRF_SECRET_KEY='csrf-secret', DEFAULT_PAGE_SIZE=10, MAX_PAGE_SIZE=200)
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
        app.dependency_overrides[get_csrf_token_service] = lambda: _FakeCsrfService()
        app.dependency_overrides[get_revoke_session_use_case] = lambda: _FakeRevokeSessionUseCase()
        app.dependency_overrides[get_create_drop_use_case] = lambda: fake_use_cases.create_drop_use_case
        app.dependency_overrides[get_delete_drop_use_case] = lambda: fake_use_cases.delete_drop_use_case
        app.dependency_overrides[get_get_drop_meta_use_case] = lambda: fake_use_cases.get_drop_meta_use_case
        app.dependency_overrides[get_list_drops_use_case] = lambda: fake_use_cases.list_drops_use_case
        app.dependency_overrides[get_update_drop_use_case] = lambda: fake_use_cases.update_drop_use_case
        client = TestClient(app)
        headers = {'HX-Request': 'true'}
        client.cookies.set('session_id', 'sid')
        upload = client.post('/actions/drop/upload', headers=headers, data={'csrf_token': 'csrf', 'slug': 'kweb', 'user_only': 'true'}, files={'file': ('hello.txt', io.BytesIO(b'hello'), 'text/plain')})
        assert upload.status_code == 204
        assert upload.headers.get('HX-Redirect') == '/drops/kweb'
        update = client.post('/actions/drop/kweb/detail', headers=headers, data={'csrf_token': 'csrf', 'title': 'new-title'})
        assert update.status_code == 200
        assert '메타데이터가 수정되었습니다.' in update.text
        delete = client.post('/actions/drop/kweb/delete', headers=headers, data={'csrf_token': 'csrf'})
        assert delete.status_code == 204
        assert delete.headers.get('HX-Redirect') == '/drops'
        logout = client.post('/actions/auth/logout', headers=headers, data={'csrf_token': 'csrf'})
        assert logout.status_code == 204
        assert logout.headers.get('HX-Redirect') == '/'

    def test_manage_password_clear_allows_logged_in_user_without_current_password(self):
        app = FastAPI()
        app.include_router(web_router)
        fake_use_cases = _FakeDropUseCases()
        fake_settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id', SESSION_COOKIE_PATH='/', SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='lax', SESSION_TTL_SECONDS=86400, CSRF_SECRET_KEY='csrf-secret', DEFAULT_PAGE_SIZE=10, MAX_PAGE_SIZE=200)
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
        app.dependency_overrides[get_csrf_token_service] = lambda: _FakeCsrfService()
        app.dependency_overrides[get_revoke_session_use_case] = lambda: _FakeRevokeSessionUseCase()
        app.dependency_overrides[get_create_drop_use_case] = lambda: fake_use_cases.create_drop_use_case
        app.dependency_overrides[get_delete_drop_use_case] = lambda: fake_use_cases.delete_drop_use_case
        app.dependency_overrides[get_get_drop_meta_use_case] = lambda: fake_use_cases.get_drop_meta_use_case
        app.dependency_overrides[get_list_drops_use_case] = lambda: fake_use_cases.list_drops_use_case
        app.dependency_overrides[get_update_drop_use_case] = lambda: fake_use_cases.update_drop_use_case
        client = TestClient(app)
        client.cookies.set('session_id', 'sid')

        fake_use_cases.items['locked'] = {
            'dto': DropDetailDTO(slug='locked', title='locked', description=None, file_name='locked.txt', mime_type='text/plain', size_bytes=5, access_scope=AccessScope.PRIVATE, is_favorite=False, requires_password=True, created_at=datetime.now(timezone.utc), updated_at=None, sha256='sha'),
            'password': 'pw',
        }

        cleared = client.post('/actions/drop/locked/password', data={'csrf_token': 'csrf', 'new_password': '', 'confirm_password': ''})

        assert cleared.status_code == 200
        assert '드롭 비밀번호가 해제되었습니다.' in cleared.text
        assert fake_use_cases.items['locked']['password'] is None
        assert fake_use_cases.items['locked']['dto'].requires_password is False

    def test_manage_password_set_renders_manage_page_with_new_password(self):
        app = FastAPI()
        app.include_router(web_router)
        fake_use_cases = _FakeDropUseCases()
        fake_settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id', SESSION_COOKIE_PATH='/', SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='lax', SESSION_TTL_SECONDS=86400, CSRF_SECRET_KEY='csrf-secret', DEFAULT_PAGE_SIZE=10, MAX_PAGE_SIZE=200)
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
        app.dependency_overrides[get_csrf_token_service] = lambda: _FakeCsrfService()
        app.dependency_overrides[get_revoke_session_use_case] = lambda: _FakeRevokeSessionUseCase()
        app.dependency_overrides[get_create_drop_use_case] = lambda: fake_use_cases.create_drop_use_case
        app.dependency_overrides[get_delete_drop_use_case] = lambda: fake_use_cases.delete_drop_use_case
        app.dependency_overrides[get_get_drop_meta_use_case] = lambda: fake_use_cases.get_drop_meta_use_case
        app.dependency_overrides[get_list_drops_use_case] = lambda: fake_use_cases.list_drops_use_case
        app.dependency_overrides[get_update_drop_use_case] = lambda: fake_use_cases.update_drop_use_case
        client = TestClient(app)
        client.cookies.set('session_id', 'sid')

        fake_use_cases.items['fresh'] = {
            'dto': DropDetailDTO(slug='fresh', title='fresh', description=None, file_name='fresh.txt', mime_type='text/plain', size_bytes=5, access_scope=AccessScope.PRIVATE, is_favorite=False, requires_password=False, created_at=datetime.now(timezone.utc), updated_at=None, sha256='sha'),
            'password': None,
        }

        updated = client.post(
            '/actions/drop/fresh/password',
            data={
                'csrf_token': 'csrf',
                'new_password': 'newpw',
                'confirm_password': 'newpw',
            },
        )

        assert updated.status_code == 200
        assert '드롭 비밀번호가 설정되었습니다.' in updated.text
        assert fake_use_cases.items['fresh']['password'] == 'newpw'
        assert fake_use_cases.items['fresh']['dto'].requires_password is True
        assert '비밀번호 입력' not in updated.text
        assert 'name="current_password" value=' not in updated.text
        assert 'password=newpw' not in updated.text
        assert 'set-cookie' in {k.lower(): v for k, v in updated.headers.items()}

    def test_manage_password_change_requires_clear_before_reset(self):
        app = FastAPI()
        app.include_router(web_router)
        fake_use_cases = _FakeDropUseCases()
        fake_settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id', SESSION_COOKIE_PATH='/', SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='lax', SESSION_TTL_SECONDS=86400, CSRF_SECRET_KEY='csrf-secret', DEFAULT_PAGE_SIZE=10, MAX_PAGE_SIZE=200)
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
        app.dependency_overrides[get_csrf_token_service] = lambda: _FakeCsrfService()
        app.dependency_overrides[get_revoke_session_use_case] = lambda: _FakeRevokeSessionUseCase()
        app.dependency_overrides[get_create_drop_use_case] = lambda: fake_use_cases.create_drop_use_case
        app.dependency_overrides[get_delete_drop_use_case] = lambda: fake_use_cases.delete_drop_use_case
        app.dependency_overrides[get_get_drop_meta_use_case] = lambda: fake_use_cases.get_drop_meta_use_case
        app.dependency_overrides[get_list_drops_use_case] = lambda: fake_use_cases.list_drops_use_case
        app.dependency_overrides[get_update_drop_use_case] = lambda: fake_use_cases.update_drop_use_case
        client = TestClient(app)
        client.cookies.set('session_id', 'sid')

        fake_use_cases.items['locked'] = {
            'dto': DropDetailDTO(slug='locked', title='locked', description=None, file_name='locked.txt', mime_type='text/plain', size_bytes=5, access_scope=AccessScope.PRIVATE, is_favorite=False, requires_password=True, created_at=datetime.now(timezone.utc), updated_at=None, sha256='sha'),
            'password': 'oldpw',
        }

        updated = client.post(
            '/actions/drop/locked/password',
            data={
                'csrf_token': 'csrf',
                'new_password': 'newpw',
                'confirm_password': 'newpw',
            },
        )

        assert updated.status_code == 200
        assert '비밀번호를 변경하려면 먼저 해제한 뒤 다시 설정해 주세요.' in updated.text
        assert fake_use_cases.items['locked']['password'] == 'oldpw'

    def test_manage_password_set_rejects_mismatched_confirmation(self):
        app = FastAPI()
        app.include_router(web_router)
        fake_use_cases = _FakeDropUseCases()
        fake_settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id', SESSION_COOKIE_PATH='/', SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='lax', SESSION_TTL_SECONDS=86400, CSRF_SECRET_KEY='csrf-secret', DEFAULT_PAGE_SIZE=10, MAX_PAGE_SIZE=200)
        app.dependency_overrides[get_app_settings] = lambda: fake_settings
        app.dependency_overrides[get_verify_session_use_case] = lambda: _FakeVerifySessionUseCase()
        app.dependency_overrides[get_csrf_token_service] = lambda: _FakeCsrfService()
        app.dependency_overrides[get_revoke_session_use_case] = lambda: _FakeRevokeSessionUseCase()
        app.dependency_overrides[get_create_drop_use_case] = lambda: fake_use_cases.create_drop_use_case
        app.dependency_overrides[get_delete_drop_use_case] = lambda: fake_use_cases.delete_drop_use_case
        app.dependency_overrides[get_get_drop_meta_use_case] = lambda: fake_use_cases.get_drop_meta_use_case
        app.dependency_overrides[get_list_drops_use_case] = lambda: fake_use_cases.list_drops_use_case
        app.dependency_overrides[get_update_drop_use_case] = lambda: fake_use_cases.update_drop_use_case
        client = TestClient(app)
        client.cookies.set('session_id', 'sid')

        fake_use_cases.items['fresh'] = {
            'dto': DropDetailDTO(slug='fresh', title='fresh', description=None, file_name='fresh.txt', mime_type='text/plain', size_bytes=5, access_scope=AccessScope.PRIVATE, is_favorite=False, requires_password=False, created_at=datetime.now(timezone.utc), updated_at=None, sha256='sha'),
            'password': None,
        }

        updated = client.post(
            '/actions/drop/fresh/password',
            data={
                'csrf_token': 'csrf',
                'new_password': 'newpw',
                'confirm_password': 'wrong',
            },
        )

        assert updated.status_code == 200
        assert '비밀번호 확인이 일치하지 않습니다.' in updated.text
        assert fake_use_cases.items['fresh']['password'] is None
