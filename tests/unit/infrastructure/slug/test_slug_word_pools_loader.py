import pytest
import tempfile
from pathlib import Path
from app.infrastructure.slug.file_word_pools_loader import load_slug_word_pools_from_dir
_CATEGORIES = ('noun', 'verb', 'adjective', 'abstract', 'direction', 'sound', 'name', 'date', 'number', 'phonetic')

def _write_minimal_valid_directory(base: Path):
    base.mkdir(parents=True, exist_ok=True)
    for category in _CATEGORIES:
        (base / f'{category}.txt').write_text(f'{category}-word\n', encoding='utf-8')

class TestSlugWordPoolsLoader:

    def test_loads_word_pools_from_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_minimal_valid_directory(root)
            pools = load_slug_word_pools_from_dir(root)
            assert set(pools.keys()) == set(_CATEGORIES)
            assert pools['noun'] == ('noun-word',)

    def test_ignores_comments_blank_lines_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_minimal_valid_directory(root)
            (root / 'noun.txt').write_text('# comment\n\nCat\ncat\ncat-dog\n', encoding='utf-8')
            pools = load_slug_word_pools_from_dir(root)
            assert pools['noun'] == ('cat', 'cat-dog')

    def test_invalid_line_raises(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_minimal_valid_directory(root)
            (root / 'verb.txt').write_text('run!\n', encoding='utf-8')
            with pytest.raises(ValueError):
                load_slug_word_pools_from_dir(root)

    def test_missing_category_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_minimal_valid_directory(root)
            (root / 'phonetic.txt').unlink()
            with pytest.raises(FileNotFoundError):
                load_slug_word_pools_from_dir(root)

    def test_empty_category_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_minimal_valid_directory(root)
            (root / 'number.txt').write_text('# no values\n\n', encoding='utf-8')
            with pytest.raises(ValueError):
                load_slug_word_pools_from_dir(root)
