from types import SimpleNamespace
from app.interfaces.web.presenters.upload_panel import upload_panel_context

class _FakeCsrfService:

    def generate(self, _session_id: str) -> str:
        return 'csrf'

class TestUploadPanelPresenter:

    def test_upload_panel_context_does_not_include_drop_list(self):

        class _Request:
            cookies = {}
        request = _Request()
        auth_data = SimpleNamespace(username='tester')
        settings = SimpleNamespace(SESSION_COOKIE_NAME='session_id')
        context = upload_panel_context(request=request, auth_data=auth_data, csrf_service=_FakeCsrfService(), settings=settings, selected_key='k1', upload_status_message='ok')
        assert 'selected_key' in context
        assert 'drops' not in context
        assert 'drop_preview_urls' not in context
