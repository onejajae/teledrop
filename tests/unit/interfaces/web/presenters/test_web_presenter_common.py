from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from app.interfaces.web.presenters.common import as_drop_vm, drop_access_status_badge

class TestWebPresenterCommon:

    def test_as_drop_vm_formats_size_and_dates(self):
        now = datetime.now(timezone.utc)
        item = SimpleNamespace(slug='k1', title='title', description=None, file_name='hello.pdf', mime_type='application/pdf', size_bytes=1536, access_scope=SimpleNamespace(value='public'), is_favorite=False, requires_password=True, created_at=now - timedelta(minutes=5), updated_at=now - timedelta(minutes=1))
        result = as_drop_vm(item)
        assert result.slug == 'k1'
        assert result.size_human == '1.50 KB'
        assert result.created_at_label is not None
        assert result.updated_at_label is not None
        assert result.created_at_relative.endswith('전')
        assert '(' in result.created_at_label

    def test_as_drop_vm_handles_missing_optional_values(self):
        item = SimpleNamespace(slug='k2', title=None, description=None, file_name='raw.bin', mime_type='application/octet-stream', size_bytes=0, access_scope=SimpleNamespace(value='private'), is_favorite=False, requires_password=False, created_at=None, updated_at=None)
        result = as_drop_vm(item)
        assert result.slug == 'k2'
        assert result.size_human == '0 B'
        assert result.created_at_label is None
        assert result.updated_at_label is None
        assert result.created_at_relative is None

    def test_drop_access_status_badge_for_private_drop(self):
        item = SimpleNamespace(access_scope='private')
        assert drop_access_status_badge(item) == ('비공개', 'warning', 'soft')

    def test_drop_access_status_badge_for_public_drop(self):
        item = SimpleNamespace(access_scope='public')
        assert drop_access_status_badge(item) == ('공유 중', 'success', 'soft')
