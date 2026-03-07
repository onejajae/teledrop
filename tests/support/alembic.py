import os

from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.bootstrap.runtime_paths import sqlite_parent_dir_from_url
from app.core.config import get_settings


def alembic_config(sqlite_url: str) -> Config:
    root_dir = Path(__file__).resolve().parents[2]
    config = Config(str(root_dir / "alembic.ini"))
    config.set_main_option("script_location", str(root_dir / "migrations"))
    config.set_main_option("sqlalchemy.url", sqlite_url)
    return config


@contextmanager
def _sqlite_host_override(sqlite_url: str):
    previous_sqlite_host = os.environ.get("SQLITE_HOST")
    os.environ["SQLITE_HOST"] = sqlite_url
    get_settings.cache_clear()
    try:
        yield
    finally:
        if previous_sqlite_host is None:
            os.environ.pop("SQLITE_HOST", None)
        else:
            os.environ["SQLITE_HOST"] = previous_sqlite_host
        get_settings.cache_clear()


def upgrade_sqlite_db(sqlite_url: str) -> None:
    sqlite_parent = sqlite_parent_dir_from_url(sqlite_url)
    if sqlite_parent is not None:
        sqlite_parent.mkdir(parents=True, exist_ok=True)
    with _sqlite_host_override(sqlite_url):
        command.upgrade(alembic_config(sqlite_url), "head")


def downgrade_sqlite_db(sqlite_url: str, revision: str) -> None:
    sqlite_parent = sqlite_parent_dir_from_url(sqlite_url)
    if sqlite_parent is not None:
        sqlite_parent.mkdir(parents=True, exist_ok=True)
    with _sqlite_host_override(sqlite_url):
        command.downgrade(alembic_config(sqlite_url), revision)
