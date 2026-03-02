import random
from collections.abc import Mapping, Sequence


SlugPattern = tuple[str, str, str]


DEFAULT_PATTERNS: tuple[SlugPattern, ...] = (
    ("noun", "verb", "adjective"),
    ("adjective", "noun", "verb"),
    ("abstract", "noun", "verb"),
    ("sound", "noun", "adjective"),
    ("adjective", "sound", "noun"),
    ("abstract", "sound", "adjective"),
    ("sound", "abstract", "noun"),
    ("direction", "sound", "adjective"),
    ("direction", "abstract", "verb"),
    ("direction", "date", "noun"),
    ("direction", "number", "noun"),
    ("name", "noun", "verb"),
    ("noun", "name", "adjective"),
    ("name", "verb", "adjective"),
    ("adjective", "name", "noun"),
    ("date", "noun", "verb"),
    ("noun", "date", "adjective"),
    ("date", "verb", "adjective"),
    ("adjective", "date", "noun"),
    ("abstract", "date", "noun"),
    ("number", "noun", "verb"),
    ("noun", "number", "adjective"),
    ("number", "verb", "adjective"),
    ("adjective", "number", "noun"),
    ("abstract", "number", "noun"),
    ("phonetic", "noun", "verb"),
    ("noun", "phonetic", "adjective"),
    ("phonetic", "verb", "adjective"),
    ("adjective", "phonetic", "noun"),
    ("sound", "date", "noun"),
)

REQUIRED_WORD_POOL_CATEGORIES: tuple[str, ...] = tuple(
    sorted({token_type for pattern in DEFAULT_PATTERNS for token_type in pattern})
)


def generate_slug(
    *,
    word_pools: Mapping[str, Sequence[str]],
    patterns: Sequence[SlugPattern] | None = None,
    seed: int | None = None,
) -> str:
    pools = word_pools
    slug_patterns = patterns or DEFAULT_PATTERNS
    rng = random.Random(seed) if seed is not None else random

    missing_categories = [
        category for category in REQUIRED_WORD_POOL_CATEGORIES if not pools.get(category)
    ]
    if missing_categories:
        missing = ", ".join(sorted(missing_categories))
        raise ValueError(f"Missing slug word categories: {missing}")

    token_values = {name: rng.choice(words) for name, words in pools.items()}
    pattern = rng.choice(slug_patterns)
    return "-".join(token_values[token_type] for token_type in pattern)
