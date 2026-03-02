import re

from pathlib import Path

from app.core.utils.slug_generator import DEFAULT_PATTERNS, REQUIRED_WORD_POOL_CATEGORIES


_WORD_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _load_word_list_file(path: Path) -> tuple[str, ...]:
    if not path.is_file():
        raise FileNotFoundError(f"Slug word file not found: {path}")

    values: list[str] = []
    seen: set[str] = set()
    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        normalized = line.lower()
        if not _WORD_RE.fullmatch(normalized):
            raise ValueError(f"Invalid slug word '{line}' in {path}:{lineno}")
        if normalized in seen:
            continue
        seen.add(normalized)
        values.append(normalized)

    if not values:
        raise ValueError(f"No valid slug words found in {path}")
    return tuple(values)


def load_slug_word_pools_from_dir(path: Path) -> dict[str, tuple[str, ...]]:
    if not path.is_dir():
        raise FileNotFoundError(f"Slug words directory not found: {path}")

    loaded: dict[str, tuple[str, ...]] = {}
    for category in REQUIRED_WORD_POOL_CATEGORIES:
        loaded[category] = _load_word_list_file(path / f"{category}.txt")

    pattern_categories = {token_type for pattern in DEFAULT_PATTERNS for token_type in pattern}
    for category in pattern_categories:
        if not loaded.get(category):
            raise ValueError(f"Slug word category '{category}' is empty")

    return loaded
