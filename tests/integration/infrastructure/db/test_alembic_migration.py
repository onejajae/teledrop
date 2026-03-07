import tempfile
from pathlib import Path

from sqlalchemy import create_engine, inspect

from tests.support.alembic import downgrade_sqlite_db, upgrade_sqlite_db


def test_alembic_upgrade_and_downgrade_manage_auth_tables():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "alembic.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        engine = create_engine(sqlite_url)

        try:
            upgrade_sqlite_db(sqlite_url)
            table_names = set(inspect(engine).get_table_names())
            assert "auth_api_keys" in table_names
            assert "auth_sessions" in table_names

            downgrade_sqlite_db(sqlite_url, "20260221_01")

            table_names_after_downgrade = set(inspect(engine).get_table_names())
            assert "auth_api_keys" not in table_names_after_downgrade
            assert "auth_sessions" not in table_names_after_downgrade
        finally:
            engine.dispose()
