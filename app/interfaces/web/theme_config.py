import json
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.bootstrap.runtime_paths import static_files_dir


def theme_tokens_path() -> Path:
    return static_files_dir() / "theme" / "theme_tokens.json"


def _as_namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{key: _as_namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_as_namespace(item) for item in value]
    return value


@lru_cache(maxsize=1)
def load_web_theme_payload() -> dict[str, Any]:
    return json.loads(theme_tokens_path().read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def web_theme() -> SimpleNamespace:
    return _as_namespace(load_web_theme_payload())
