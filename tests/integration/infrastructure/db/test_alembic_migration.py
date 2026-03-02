import tempfile
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _alembic_config(sqlite_url: str) -> Config:
    root_dir = Path(__file__).resolve().parents[4]
    config = Config(str(root_dir / "alembic.ini"))
    config.set_main_option("script_location", str(root_dir / "migrations"))
    config.set_main_option("sqlalchemy.url", sqlite_url)
    return config


def test_alembic_upgrade_and_downgrade_manage_auth_api_keys_table():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "alembic.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        config = _alembic_config(sqlite_url)
        previous_sqlite_host = os.environ.get("SQLITE_HOST")
        os.environ["SQLITE_HOST"] = sqlite_url

        try:
            command.upgrade(config, "head")

            engine = create_engine(sqlite_url)
            table_names = set(inspect(engine).get_table_names())
            assert "auth_api_keys" in table_names

            command.downgrade(config, "20260221_01")

            table_names_after_downgrade = set(inspect(engine).get_table_names())
            assert "auth_api_keys" not in table_names_after_downgrade
            engine.dispose()
        finally:
            if previous_sqlite_host is None:
                os.environ.pop("SQLITE_HOST", None)
            else:
                os.environ["SQLITE_HOST"] = previous_sqlite_host
