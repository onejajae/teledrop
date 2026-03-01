from app.core.utils import normalize_pagination

class TestPaginationUtils:

    def test_applies_defaults(self):
        assert normalize_pagination(page=None, page_size=None, default_page_size=10, max_page_size=200) == (1, 10)

    def test_clamps_negative_values(self):
        assert normalize_pagination(page=-10, page_size=-1, default_page_size=10, max_page_size=200) == (1, 1)

    def test_clamps_page_size_to_max(self):
        assert normalize_pagination(page=2, page_size=500, default_page_size=10, max_page_size=200) == (2, 200)

    def test_keeps_valid_values(self):
        assert normalize_pagination(page=3, page_size=25, default_page_size=10, max_page_size=200) == (3, 25)
