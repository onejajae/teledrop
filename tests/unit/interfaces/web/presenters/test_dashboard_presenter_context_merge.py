import pytest
from app.interfaces.web.presenters.dashboard import merge_panel_contexts

class TestDashboardPresenterContextMerge:

    def test_allows_duplicate_shared_keys(self):
        merged = merge_panel_contexts({'request': object(), 'is_login': True, 'csrf_token': 'a'}, {'is_login': True, 'csrf_token': 'a', 'selected_key': 'k1'}, {'selected_key': 'k1'})
        assert merged['is_login']
        assert merged['csrf_token'] == 'a'
        assert merged['selected_key'] == 'k1'

    def test_raises_on_duplicate_non_shared_key(self):
        with pytest.raises(ValueError):
            merge_panel_contexts({'drop_error_message': 'x'}, {'drop_error_message': 'y'})
