import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from app.infrastructure.db.schema import (
    ALEMBIC_UPGRADE_COMMAND,
    DatabaseSchemaOutOfDateError,
    assert_db_schema_current,
)
from tests.support.alembic import upgrade_sqlite_db


def _create_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path.as_posix()}")


def _bootstrap_user_id(engine) -> str:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id
                FROM users
                WHERE username = :username
                """
            ),
            {"username": "admin"},
        ).one()
    return row.id


def test_alembic_upgrade_head_creates_current_tables():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "init.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        engine = _create_engine(db_path)

        upgrade_sqlite_db(sqlite_url)

        table_names = set(inspect(engine).get_table_names())
        assert "users" in table_names
        assert "drops" in table_names
        assert "auth_sessions" in table_names
        assert "auth_api_keys" in table_names
        engine.dispose()


def test_alembic_upgrade_head_creates_owner_user_id_and_slug_columns():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "schema.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        engine = _create_engine(db_path)

        upgrade_sqlite_db(sqlite_url)

        drop_columns = {column["name"] for column in inspect(engine).get_columns("drops")}
        assert "owner_user_id" in drop_columns
        assert "slug" in drop_columns
        assert "key" not in drop_columns
        engine.dispose()


def test_alembic_upgrade_head_is_idempotent_and_keeps_existing_rows():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "idempotent.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        engine = _create_engine(db_path)

        upgrade_sqlite_db(sqlite_url)
        owner_user_id = _bootstrap_user_id(engine)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO drops (
                        id, owner_user_id, slug, access_scope, is_favorite, drop_password,
                        file_name, mime_type, size_bytes, sha256, storage_key,
                        title, description, created_at, updated_at
                    ) VALUES (
                        :id, :owner_user_id, :slug, :access_scope, :is_favorite, :drop_password,
                        :file_name, :mime_type, :size_bytes, :sha256, :storage_key,
                        :title, :description, :created_at, :updated_at
                    )
                    """
                ),
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "owner_user_id": owner_user_id,
                    "slug": "legacy-drop",
                    "access_scope": "private",
                    "is_favorite": 0,
                    "drop_password": None,
                    "file_name": "legacy.txt",
                    "mime_type": "text/plain",
                    "size_bytes": 5,
                    "sha256": "abc",
                    "storage_key": "legacy-storage",
                    "title": None,
                    "description": None,
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": None,
                },
            )

        upgrade_sqlite_db(sqlite_url)

        with engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT owner_user_id, slug, file_name, storage_key
                    FROM drops
                    WHERE slug = :slug
                    """
                ),
                {"slug": "legacy-drop"},
            ).one()

        assert row.owner_user_id == owner_user_id
        assert row.slug == "legacy-drop"
        assert row.file_name == "legacy.txt"
        assert row.storage_key == "legacy-storage"
        engine.dispose()


def test_schema_validation_rejects_missing_alembic_revision():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "missing-version.db"
        engine = _create_engine(db_path)

        with pytest.raises(DatabaseSchemaOutOfDateError, match=ALEMBIC_UPGRADE_COMMAND):
            assert_db_schema_current(engine)

        engine.dispose()


def test_schema_validation_rejects_outdated_revision():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "outdated.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        engine = _create_engine(db_path)

        upgrade_sqlite_db(sqlite_url)
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE alembic_version SET version_num = :revision"),
                {"revision": "20260302_01"},
            )

        with pytest.raises(DatabaseSchemaOutOfDateError, match="not current"):
            assert_db_schema_current(engine)

        engine.dispose()


def test_schema_validation_rejects_unknown_revision():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "unknown.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        engine = _create_engine(db_path)

        upgrade_sqlite_db(sqlite_url)
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE alembic_version SET version_num = :revision"),
                {"revision": "unknown_revision"},
            )

        with pytest.raises(DatabaseSchemaOutOfDateError, match="not recognized"):
            assert_db_schema_current(engine)

        engine.dispose()
