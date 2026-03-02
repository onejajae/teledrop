import tempfile
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.infrastructure.db.init import init_db


def _create_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path.as_posix()}")


def test_init_db_creates_current_tables():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "init.db"
        engine = _create_engine(db_path)

        init_db(engine)

        table_names = set(inspect(engine).get_table_names())
        assert "drops" in table_names
        assert "auth_sessions" in table_names
        assert "auth_api_keys" in table_names


def test_init_db_creates_slug_column_in_drops_table():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "schema.db"
        engine = _create_engine(db_path)

        init_db(engine)

        drop_columns = {column["name"] for column in inspect(engine).get_columns("drops")}
        assert "slug" in drop_columns
        assert "key" not in drop_columns


def test_init_db_is_idempotent_and_keeps_existing_rows():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "idempotent.db"
        engine = _create_engine(db_path)

        init_db(engine)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO drops (
                        id, slug, access_scope, is_favorite, drop_password,
                        file_name, mime_type, size_bytes, sha256, storage_key,
                        title, description, created_at, updated_at
                    ) VALUES (
                        :id, :slug, :access_scope, :is_favorite, :drop_password,
                        :file_name, :mime_type, :size_bytes, :sha256, :storage_key,
                        :title, :description, :created_at, :updated_at
                    )
                    """
                ),
                {
                    "id": "11111111-1111-1111-1111-111111111111",
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

        init_db(engine)

        with engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT slug, file_name, storage_key
                    FROM drops
                    WHERE slug = :slug
                    """
                ),
                {"slug": "legacy-drop"},
            ).one()

        assert row.slug == "legacy-drop"
        assert row.file_name == "legacy.txt"
        assert row.storage_key == "legacy-storage"
