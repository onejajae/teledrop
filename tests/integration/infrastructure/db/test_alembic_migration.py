import os
import tempfile
from pathlib import Path

from alembic import command
from argon2 import PasswordHasher
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings
from tests.support.alembic import alembic_config, downgrade_sqlite_db, upgrade_sqlite_db


def test_alembic_upgrade_and_downgrade_manage_auth_tables():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "alembic.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        engine = create_engine(sqlite_url)

        try:
            upgrade_sqlite_db(sqlite_url)
            table_names = set(inspect(engine).get_table_names())
            assert "users" in table_names
            assert "auth_api_keys" in table_names
            assert "auth_sessions" in table_names

            downgrade_sqlite_db(sqlite_url, "20260221_01")

            table_names_after_downgrade = set(inspect(engine).get_table_names())
            assert "users" not in table_names_after_downgrade
            assert "auth_api_keys" not in table_names_after_downgrade
            assert "auth_sessions" not in table_names_after_downgrade
        finally:
            engine.dispose()


def test_alembic_upgrade_backfills_bootstrap_user_owned_records():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "backfill.db"
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        engine = create_engine(sqlite_url)

        previous_sqlite_host = os.environ.get("SQLITE_HOST")
        previous_web_username = os.environ.get("WEB_USERNAME")
        previous_web_password = os.environ.get("WEB_PASSWORD")
        bootstrap_password_hash = PasswordHasher().hash("bootstrap-password")
        os.environ["SQLITE_HOST"] = sqlite_url
        os.environ["WEB_USERNAME"] = "bootstrap-admin"
        os.environ["WEB_PASSWORD"] = bootstrap_password_hash
        get_settings.cache_clear()

        try:
            command.upgrade(alembic_config(sqlite_url), "20260307_01")

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
                        "id": "11111111111111111111111111111111",
                        "slug": "legacy-drop",
                        "access_scope": "private",
                        "is_favorite": 0,
                        "drop_password": None,
                        "file_name": "legacy.txt",
                        "mime_type": "text/plain",
                        "size_bytes": 5,
                        "sha256": "drop-sha",
                        "storage_key": "legacy-storage",
                        "title": "Legacy",
                        "description": None,
                        "created_at": "2026-01-01T00:00:00",
                        "updated_at": None,
                    },
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO auth_api_keys (
                            id, public_id, name, created_by_username, key_hash,
                            created_at, expires_at, last_used_at, revoked_at
                        ) VALUES (
                            :id, :public_id, :name, :created_by_username, :key_hash,
                            :created_at, :expires_at, :last_used_at, :revoked_at
                        )
                        """
                    ),
                    {
                        "id": "22222222222222222222222222222222",
                        "public_id": "pub1",
                        "name": "legacy-key",
                        "created_by_username": "legacy-admin",
                        "key_hash": "key-hash",
                        "created_at": "2026-01-01T00:00:00",
                        "expires_at": None,
                        "last_used_at": None,
                        "revoked_at": None,
                    },
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO auth_sessions (
                            sid, username, created_at, expires_at, revoked_at
                        ) VALUES (
                            :sid, :username, :created_at, :expires_at, :revoked_at
                        )
                        """
                    ),
                    {
                        "sid": "session-1",
                        "username": "legacy-admin",
                        "created_at": "2026-01-01T00:00:00",
                        "expires_at": "2026-01-02T00:00:00",
                        "revoked_at": None,
                    },
                )

            command.upgrade(alembic_config(sqlite_url), "head")

            inspector = inspect(engine)
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            drop_columns = {column["name"] for column in inspector.get_columns("drops")}
            api_key_columns = {column["name"] for column in inspector.get_columns("auth_api_keys")}
            session_columns = {column["name"] for column in inspector.get_columns("auth_sessions")}

            assert {"id", "username", "password_hash"} <= user_columns
            assert "owner_user_id" in drop_columns
            assert "created_by_username" not in api_key_columns
            assert "owner_user_id" in api_key_columns
            assert "username" not in session_columns
            assert "user_id" in session_columns

            with engine.begin() as conn:
                user = conn.execute(
                    text(
                        """
                        SELECT id, username, password_hash
                        FROM users
                        WHERE username = :username
                        """
                    ),
                    {"username": "bootstrap-admin"},
                ).one()
                drop = conn.execute(
                    text(
                        """
                        SELECT slug, owner_user_id
                        FROM drops
                        WHERE slug = :slug
                        """
                    ),
                    {"slug": "legacy-drop"},
                ).one()
                api_key = conn.execute(
                    text(
                        """
                        SELECT public_id, owner_user_id
                        FROM auth_api_keys
                        WHERE public_id = :public_id
                        """
                    ),
                    {"public_id": "pub1"},
                ).one()
                session = conn.execute(
                    text(
                        """
                        SELECT sid, user_id
                        FROM auth_sessions
                        WHERE sid = :sid
                        """
                    ),
                    {"sid": "session-1"},
                ).one()

            assert user.username == "bootstrap-admin"
            assert user.password_hash
            assert drop.owner_user_id == user.id
            assert api_key.owner_user_id == user.id
            assert session.user_id == user.id
            assert user.password_hash == bootstrap_password_hash
        finally:
            if previous_sqlite_host is None:
                os.environ.pop("SQLITE_HOST", None)
            else:
                os.environ["SQLITE_HOST"] = previous_sqlite_host
            if previous_web_username is None:
                os.environ.pop("WEB_USERNAME", None)
            else:
                os.environ["WEB_USERNAME"] = previous_web_username
            if previous_web_password is None:
                os.environ.pop("WEB_PASSWORD", None)
            else:
                os.environ["WEB_PASSWORD"] = previous_web_password
            get_settings.cache_clear()
            engine.dispose()
