"""multi-user persistence

Revision ID: 20260419_01
Revises: 20260307_01
Create Date: 2026-04-19 18:00:00
"""

from datetime import datetime, timezone
from typing import Sequence, Union
import uuid

from alembic import op
from sqlalchemy import text

from app.core.config import get_settings


# revision identifiers, used by Alembic.
revision: str = "20260419_01"
down_revision: Union[str, Sequence[str], None] = "20260307_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _bootstrap_user() -> tuple[str, str]:
    bind = op.get_bind()
    settings = get_settings()
    now = datetime.now(timezone.utc)

    row = bind.execute(
        text(
            """
            SELECT id
            FROM users
            WHERE username = :username
            """
        ),
        {"username": settings.WEB_USERNAME},
    ).one_or_none()
    if row is not None:
        bind.execute(
            text(
                """
                UPDATE users
                SET password_hash = :password_hash,
                    updated_at = :updated_at
                WHERE id = :user_id
                """
            ),
            {
                "user_id": row.id,
                "password_hash": settings.WEB_PASSWORD,
                "updated_at": now,
            },
        )
        return row.id, settings.WEB_USERNAME

    user_id = uuid.uuid4().hex
    bind.execute(
        text(
            """
            INSERT INTO users (
                id,
                username,
                password_hash,
                created_at,
                updated_at,
                disabled_at
            ) VALUES (
                :id,
                :username,
                :password_hash,
                :created_at,
                :updated_at,
                NULL
            )
            """
        ),
        {
            "id": user_id,
            "username": settings.WEB_USERNAME,
            "password_hash": settings.WEB_PASSWORD,
            "created_at": now,
            "updated_at": now,
        },
    )
    return user_id, settings.WEB_USERNAME


def _rebuild_drops(owner_user_id: str) -> None:
    bind = op.get_bind()
    op.execute("ALTER TABLE drops RENAME TO drops_legacy")
    op.execute(
        """
        CREATE TABLE drops (
            id CHAR(32) NOT NULL PRIMARY KEY,
            owner_user_id CHAR(32) NOT NULL,
            slug VARCHAR NOT NULL UNIQUE,
            access_scope VARCHAR NOT NULL,
            is_favorite BOOLEAN NOT NULL DEFAULT 0,
            drop_password VARCHAR NULL,
            file_name VARCHAR NOT NULL,
            mime_type VARCHAR NOT NULL,
            size_bytes INTEGER NOT NULL,
            sha256 VARCHAR NOT NULL,
            storage_key VARCHAR NOT NULL,
            title VARCHAR NULL,
            description VARCHAR NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NULL,
            FOREIGN KEY(owner_user_id) REFERENCES users (id)
        )
        """
    )
    bind.execute(
        text(
            """
            INSERT INTO drops (
                id,
                owner_user_id,
                slug,
                access_scope,
                is_favorite,
                drop_password,
                file_name,
                mime_type,
                size_bytes,
                sha256,
                storage_key,
                title,
                description,
                created_at,
                updated_at
            )
            SELECT
                id,
                :owner_user_id,
                slug,
                access_scope,
                is_favorite,
                drop_password,
                file_name,
                mime_type,
                size_bytes,
                sha256,
                storage_key,
                title,
                description,
                created_at,
                updated_at
            FROM drops_legacy
            """
        ),
        {"owner_user_id": owner_user_id},
    )
    op.execute("DROP TABLE drops_legacy")
    op.execute(
        """
        CREATE INDEX ix_drops_owner_user_id
        ON drops (owner_user_id)
        """
    )


def _rebuild_auth_api_keys(owner_user_id: str) -> None:
    bind = op.get_bind()
    op.execute("DROP INDEX IF EXISTS ix_auth_api_keys_created_by_username")
    op.execute("DROP INDEX IF EXISTS ix_auth_api_keys_expires_at")
    op.execute("DROP INDEX IF EXISTS ix_auth_api_keys_revoked_at")
    op.execute("ALTER TABLE auth_api_keys RENAME TO auth_api_keys_legacy")
    op.execute(
        """
        CREATE TABLE auth_api_keys (
            id CHAR(32) NOT NULL PRIMARY KEY,
            public_id VARCHAR NOT NULL UNIQUE,
            name VARCHAR NOT NULL,
            owner_user_id CHAR(32) NOT NULL,
            key_hash VARCHAR NOT NULL,
            created_at DATETIME NOT NULL,
            expires_at DATETIME NULL,
            last_used_at DATETIME NULL,
            revoked_at DATETIME NULL,
            FOREIGN KEY(owner_user_id) REFERENCES users (id)
        )
        """
    )
    bind.execute(
        text(
            """
            INSERT INTO auth_api_keys (
                id,
                public_id,
                name,
                owner_user_id,
                key_hash,
                created_at,
                expires_at,
                last_used_at,
                revoked_at
            )
            SELECT
                id,
                public_id,
                name,
                :owner_user_id,
                key_hash,
                created_at,
                expires_at,
                last_used_at,
                revoked_at
            FROM auth_api_keys_legacy
            """
        ),
        {"owner_user_id": owner_user_id},
    )
    op.execute("DROP TABLE auth_api_keys_legacy")
    op.execute(
        """
        CREATE INDEX ix_auth_api_keys_owner_user_id
        ON auth_api_keys (owner_user_id)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_auth_api_keys_expires_at
        ON auth_api_keys (expires_at)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_auth_api_keys_revoked_at
        ON auth_api_keys (revoked_at)
        """
    )


def _rebuild_auth_sessions(owner_user_id: str) -> None:
    bind = op.get_bind()
    op.execute("DROP INDEX IF EXISTS ix_auth_sessions_sid")
    op.execute("DROP INDEX IF EXISTS ix_auth_sessions_username")
    op.execute("ALTER TABLE auth_sessions RENAME TO auth_sessions_legacy")
    op.execute(
        """
        CREATE TABLE auth_sessions (
            sid VARCHAR NOT NULL PRIMARY KEY,
            user_id CHAR(32) NOT NULL,
            created_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL,
            revoked_at DATETIME NULL,
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
        """
    )
    bind.execute(
        text(
            """
            INSERT INTO auth_sessions (
                sid,
                user_id,
                created_at,
                expires_at,
                revoked_at
            )
            SELECT
                sid,
                :user_id,
                created_at,
                expires_at,
                revoked_at
            FROM auth_sessions_legacy
            """
        ),
        {"user_id": owner_user_id},
    )
    op.execute("DROP TABLE auth_sessions_legacy")
    op.execute(
        """
        CREATE INDEX ix_auth_sessions_sid
        ON auth_sessions (sid)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_auth_sessions_user_id
        ON auth_sessions (user_id)
        """
    )


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE users (
            id CHAR(32) NOT NULL PRIMARY KEY,
            username VARCHAR NOT NULL UNIQUE,
            password_hash VARCHAR NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            disabled_at DATETIME NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_users_username
        ON users (username)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_users_disabled_at
        ON users (disabled_at)
        """
    )

    owner_user_id, _ = _bootstrap_user()
    _rebuild_drops(owner_user_id)
    _rebuild_auth_api_keys(owner_user_id)
    _rebuild_auth_sessions(owner_user_id)


def downgrade() -> None:
    bind = op.get_bind()
    settings = get_settings()

    op.execute("DROP INDEX IF EXISTS ix_auth_sessions_sid")
    op.execute("DROP INDEX IF EXISTS ix_auth_sessions_user_id")
    op.execute("ALTER TABLE auth_sessions RENAME TO auth_sessions_multi_user")
    op.execute(
        """
        CREATE TABLE auth_sessions (
            sid VARCHAR NOT NULL PRIMARY KEY,
            username VARCHAR NOT NULL,
            created_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL,
            revoked_at DATETIME NULL
        )
        """
    )
    bind.execute(
        text(
            """
            INSERT INTO auth_sessions (
                sid,
                username,
                created_at,
                expires_at,
                revoked_at
            )
            SELECT
                s.sid,
                COALESCE(u.username, :fallback_username),
                s.created_at,
                s.expires_at,
                s.revoked_at
            FROM auth_sessions_multi_user AS s
            LEFT JOIN users AS u
                ON u.id = s.user_id
            """
        ),
        {"fallback_username": settings.WEB_USERNAME},
    )
    op.execute("DROP TABLE auth_sessions_multi_user")
    op.execute(
        """
        CREATE INDEX ix_auth_sessions_sid
        ON auth_sessions (sid)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_auth_sessions_username
        ON auth_sessions (username)
        """
    )

    op.execute("DROP INDEX IF EXISTS ix_auth_api_keys_owner_user_id")
    op.execute("DROP INDEX IF EXISTS ix_auth_api_keys_expires_at")
    op.execute("DROP INDEX IF EXISTS ix_auth_api_keys_revoked_at")
    op.execute("ALTER TABLE auth_api_keys RENAME TO auth_api_keys_multi_user")
    op.execute(
        """
        CREATE TABLE auth_api_keys (
            id CHAR(32) NOT NULL PRIMARY KEY,
            public_id VARCHAR NOT NULL UNIQUE,
            name VARCHAR NOT NULL,
            created_by_username VARCHAR NOT NULL,
            key_hash VARCHAR NOT NULL,
            created_at DATETIME NOT NULL,
            expires_at DATETIME NULL,
            last_used_at DATETIME NULL,
            revoked_at DATETIME NULL
        )
        """
    )
    bind.execute(
        text(
            """
            INSERT INTO auth_api_keys (
                id,
                public_id,
                name,
                created_by_username,
                key_hash,
                created_at,
                expires_at,
                last_used_at,
                revoked_at
            )
            SELECT
                a.id,
                a.public_id,
                a.name,
                COALESCE(u.username, :fallback_username),
                a.key_hash,
                a.created_at,
                a.expires_at,
                a.last_used_at,
                a.revoked_at
            FROM auth_api_keys_multi_user AS a
            LEFT JOIN users AS u
                ON u.id = a.owner_user_id
            """
        ),
        {"fallback_username": settings.WEB_USERNAME},
    )
    op.execute("DROP TABLE auth_api_keys_multi_user")
    op.execute(
        """
        CREATE INDEX ix_auth_api_keys_created_by_username
        ON auth_api_keys (created_by_username)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_auth_api_keys_expires_at
        ON auth_api_keys (expires_at)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_auth_api_keys_revoked_at
        ON auth_api_keys (revoked_at)
        """
    )

    op.execute("DROP INDEX IF EXISTS ix_drops_owner_user_id")
    op.execute("ALTER TABLE drops RENAME TO drops_multi_user")
    op.execute(
        """
        CREATE TABLE drops (
            id CHAR(32) NOT NULL PRIMARY KEY,
            slug VARCHAR NOT NULL UNIQUE,
            access_scope VARCHAR NOT NULL,
            is_favorite BOOLEAN NOT NULL DEFAULT 0,
            drop_password VARCHAR NULL,
            file_name VARCHAR NOT NULL,
            mime_type VARCHAR NOT NULL,
            size_bytes INTEGER NOT NULL,
            sha256 VARCHAR NOT NULL,
            storage_key VARCHAR NOT NULL,
            title VARCHAR NULL,
            description VARCHAR NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NULL
        )
        """
    )
    op.execute(
        """
        INSERT INTO drops (
            id,
            slug,
            access_scope,
            is_favorite,
            drop_password,
            file_name,
            mime_type,
            size_bytes,
            sha256,
            storage_key,
            title,
            description,
            created_at,
            updated_at
        )
        SELECT
            id,
            slug,
            access_scope,
            is_favorite,
            drop_password,
            file_name,
            mime_type,
            size_bytes,
            sha256,
            storage_key,
            title,
            description,
            created_at,
            updated_at
        FROM drops_multi_user
        """
    )
    op.execute("DROP TABLE drops_multi_user")

    op.execute("DROP INDEX IF EXISTS ix_users_username")
    op.execute("DROP INDEX IF EXISTS ix_users_disabled_at")
    op.execute("DROP TABLE users")
