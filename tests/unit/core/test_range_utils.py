import pytest
from app.core.exceptions import InvalidRangeHeader, RangeNotSatisfiable
from app.core.utils import parse_range_header

class TestRangeUtils:

    def test_parse_standard_range(self):
        assert parse_range_header('bytes=0-9', 100) == (0, 9)

    def test_parse_open_ended_range(self):
        assert parse_range_header('bytes=10-', 100) == (10, 99)

    def test_parse_suffix_range(self):
        assert parse_range_header('bytes=-10', 100) == (90, 99)

    def test_parse_range_clamps_end_to_file_size(self):
        assert parse_range_header('bytes=95-150', 100) == (95, 99)

    def test_invalid_headers(self):
        invalid_headers = ['', 'items=0-1', 'bytes=', 'bytes=abc-1', 'bytes=1-abc', 'bytes=-0', 'bytes=0-1,2-3']
        for header in invalid_headers:
            with pytest.raises(InvalidRangeHeader):
                parse_range_header(header, 100)

    def test_unsatisfiable_ranges(self):
        with pytest.raises(RangeNotSatisfiable):
            parse_range_header('bytes=100-120', 100)
        with pytest.raises(RangeNotSatisfiable):
            parse_range_header('bytes=20-10', 100)
        with pytest.raises(RangeNotSatisfiable):
            parse_range_header('bytes=0-0', 0)
