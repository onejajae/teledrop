from datetime import datetime, timezone
from types import SimpleNamespace
from app.application.auth.types import AuthIdentity
from app.domain.drop.errors import DropAccessDeniedError, DropNotFoundError, DropPasswordInvalidError
from app.interfaces.web.presenters.detail_panel import detail_panel_context

class _FakeCsrfService:

    def generate(self, _session_id: str) -> str:
        return 'csrf'

class _MetaUseCasePasswordProtected:

    def __init__(self):
        self.meta = SimpleNamespace(slug='locked', title='제목', description=None, file_name='locked.pdf', mime_type='application/pdf', size_bytes=2048, access_scope=SimpleNamespace(value='private'), is_favorite=False, requires_password=True, created_at=datetime.now(timezone.utc), updated_at=None)

    async def execute_for_display(self, slug, auth):
        _ = (slug, auth)
        return self.meta

    async def execute(self, query):
        _ = query
        raise DropPasswordInvalidError()

class _MetaUseCaseForbidden:

    async def execute_for_display(self, slug, auth):
        _ = (slug, auth)
        raise DropAccessDeniedError()

class _MetaUseCaseNotFound:

    async def execute_for_display(self, slug, auth):
        _ = (slug, auth)
        raise DropNotFoundError()

class _FakeDropUseCasesPasswordProtected:

    def __init__(self):
        self.get_drop_meta_use_case = _MetaUseCasePasswordProtected()

class _FakeDropUseCasesForbidden:

    def __init__(self):
        self.get_drop_meta_use_case = _MetaUseCaseForbidden()

class _FakeDropUseCasesNotFound:

    def __init__(self):
        self.get_drop_meta_use_case = _MetaUseCaseNotFound()

class TestDetailPanelPresenter:

    def setup_method(self):
        self.request = SimpleNamespace(cookies={})
        self.settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id')
        self.auth_data = AuthIdentity(username=None)
        self.csrf_service = _FakeCsrfService()
        self.drop_use_cases = _FakeDropUseCasesPasswordProtected()

    async def test_first_password_prompt_does_not_show_error_message(self):
        context = await detail_panel_context(request=self.request, auth_data=self.auth_data, csrf_service=self.csrf_service, get_drop_meta_use_case=self.drop_use_cases.get_drop_meta_use_case, settings=self.settings, selected_key='locked', selected_password=None)
        assert context['selected_requires_password']
        assert context['detail_error_message'] is None
        assert context['selected_drop'] is not None

    async def test_wrong_password_shows_invalid_password_message(self):
        context = await detail_panel_context(request=self.request, auth_data=self.auth_data, csrf_service=self.csrf_service, get_drop_meta_use_case=self.drop_use_cases.get_drop_meta_use_case, settings=self.settings, selected_key='locked', selected_password='bad-password')
        assert context['detail_error_message'] == '비밀번호가 올바르지 않습니다.'
        assert context['selected_requires_password']
        assert context['selected_drop'] is not None
        assert context['detail_error_code'] == 'password_invalid'

    async def test_access_denied_sets_forbidden_error_code(self):
        context = await detail_panel_context(request=self.request, auth_data=self.auth_data, csrf_service=self.csrf_service, get_drop_meta_use_case=_FakeDropUseCasesForbidden().get_drop_meta_use_case, settings=self.settings, selected_key='locked')
        assert context['detail_error_code'] == 'forbidden'
        assert '로그인이 필요' in context['detail_error_message']
        assert context['selected_drop'] is None

    async def test_not_found_sets_not_found_error_code(self):
        context = await detail_panel_context(request=self.request, auth_data=self.auth_data, csrf_service=self.csrf_service, get_drop_meta_use_case=_FakeDropUseCasesNotFound().get_drop_meta_use_case, settings=self.settings, selected_key='missing')
        assert context['detail_error_code'] == 'not_found'
        assert '존재하지 않습니다' in context['detail_error_message']
        assert context['selected_drop'] is None
