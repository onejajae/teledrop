from pathlib import Path
from urllib.parse import urlparse


def project_root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def static_files_dir() -> Path:
    return project_root_dir() / "app" / "interfaces" / "web" / "static"


def template_dir() -> Path:
    return project_root_dir() / "app" / "interfaces" / "web" / "templates"


def sqlite_file_path_from_url(database_url: str) -> Path | None:
    parsed = urlparse(database_url)
    if not parsed.scheme.startswith("sqlite"):
        return None
    if parsed.netloc:
        return None
    if not parsed.path:
        return None

    raw_path = parsed.path[1:] if parsed.path.startswith("/") else parsed.path
    if not raw_path or raw_path == ":memory:":
        return None

    return Path(raw_path)


def sqlite_parent_dir_from_url(database_url: str) -> Path | None:
    sqlite_path = sqlite_file_path_from_url(database_url)
    if sqlite_path is None:
        return None
    return sqlite_path.parent
