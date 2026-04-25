import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from argon2 import PasswordHasher
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.infrastructure.db.engine import create_db_engine
from app.infrastructure.db.schema import (
    DatabaseSchemaIncompatibleError,
    INCOMPATIBLE_DATABASE_HINT,
    initialize_database_schema,
)


def _settings(sqlite_url: str, *, password_hash: str | None = None):
    return SimpleNamespace(
        SQLITE_HOST=sqlite_url,
        WEB_USERNAME="admin",
        WEB_PASSWORD=password_hash or PasswordHasher().hash("password"),
    )


def _engine(db_path: Path):
    settings = _settings(f"sqlite:///{db_path.as_posix()}")
    return create_db_engine(settings)


def test_initialize_database_schema_creates_current_tables_and_bootstrap_user():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "init.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        engine = _engine(db_path)

        initialize_database_schema(engine, _settings(sqlite_url))

        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
        assert {"users", "drops", "auth_sessions", "auth_api_keys"} <= table_names
        assert "alembic_version" not in table_names

        drop_columns = {column["name"] for column in inspector.get_columns("drops")}
        assert {"owner_user_id", "slug"} <= drop_columns
        assert "key" not in drop_columns

        with engine.begin() as conn:
            user = conn.execute(
                text("SELECT username, password_hash FROM users WHERE username = :username"),
                {"username": "admin"},
            ).one()

        assert user.username == "admin"
        assert user.password_hash
        engine.dispose()


def test_initialize_database_schema_does_not_overwrite_existing_users():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "existing-user.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        engine = _engine(db_path)

        initialize_database_schema(engine, _settings(sqlite_url, password_hash="first-hash"))
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE users SET password_hash = :password_hash WHERE username = :username"),
                {"username": "admin", "password_hash": "custom-hash"},
            )

        initialize_database_schema(engine, _settings(sqlite_url, password_hash="second-hash"))

        with engine.begin() as conn:
            user = conn.execute(
                text("SELECT username, password_hash FROM users WHERE username = :username"),
                {"username": "admin"},
            ).one()

        assert user.password_hash == "custom-hash"
        engine.dispose()


def test_initialize_database_schema_rejects_alembic_version_table():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "alembic-leftover.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        engine = _engine(db_path)

        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR NOT NULL)"))

        with pytest.raises(DatabaseSchemaIncompatibleError, match=INCOMPATIBLE_DATABASE_HINT):
            initialize_database_schema(engine, _settings(sqlite_url))

        engine.dispose()


def test_initialize_database_schema_rejects_old_core_table_shape():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "old-schema.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        engine = _engine(db_path)

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE drops (
                        id CHAR(32) NOT NULL PRIMARY KEY,
                        slug VARCHAR NOT NULL UNIQUE
                    )
                    """
                )
            )

        with pytest.raises(DatabaseSchemaIncompatibleError, match="owner_user_id"):
            initialize_database_schema(engine, _settings(sqlite_url))

        engine.dispose()


def test_sqlite_engine_enables_foreign_keys():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "fk.db"
        engine = _engine(db_path)

        with engine.connect() as conn:
            assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1

        engine.dispose()


@pytest.mark.parametrize(
    "statement",
    [
        """
        INSERT INTO drops (
            id, owner_user_id, slug, access_scope, is_favorite, drop_password,
            file_name, mime_type, size_bytes, sha256, storage_key,
            title, description, created_at, updated_at
        ) VALUES (
            '11111111111111111111111111111111', 'missing-user', 'fk-drop',
            'private', 0, NULL, 'file.txt', 'text/plain', 4, 'sha', 'storage',
            NULL, NULL, '2026-01-01T00:00:00', NULL
        )
        """,
        """
        INSERT INTO auth_api_keys (
            id, public_id, name, owner_user_id, key_hash,
            created_at, expires_at, last_used_at, revoked_at
        ) VALUES (
            '22222222222222222222222222222222', 'pub1', 'key', 'missing-user',
            'hash', '2026-01-01T00:00:00', NULL, NULL, NULL
        )
        """,
        """
        INSERT INTO auth_sessions (
            sid, user_id, created_at, expires_at, revoked_at
        ) VALUES (
            'sid-1', 'missing-user', '2026-01-01T00:00:00',
            '2026-01-02T00:00:00', NULL
        )
        """,
    ],
)
def test_foreign_keys_reject_missing_owners(statement: str):
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "fk-reject.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        engine = _engine(db_path)
        initialize_database_schema(engine, _settings(sqlite_url))

        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(text(statement))

        engine.dispose()
