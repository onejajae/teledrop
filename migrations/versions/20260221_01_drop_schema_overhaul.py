"""drop schema overhaul

Revision ID: 20260221_01
Revises:
Create Date: 2026-02-21 21:00:00
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = "20260221_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pick_column_expr(columns: set[str], *candidates: str, default: str) -> str:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return default


def _copy_legacy_table_into_drops(table_name: str) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())
    if table_name not in table_names:
        return

    columns = {column_info["name"] for column_info in inspector.get_columns(table_name)}
    if "id" not in columns:
        return

    slug_expr = _pick_column_expr(columns, "slug", "key", default="")
    if not slug_expr:
        return

    if "access_scope" in columns:
        access_scope_expr = "access_scope"
    elif "user_only" in columns:
        access_scope_expr = "CASE WHEN COALESCE(user_only, 1) = 1 THEN 'private' ELSE 'public' END"
    else:
        access_scope_expr = "'private'"

    is_favorite_expr = _pick_column_expr(columns, "is_favorite", "favorite", default="0")
    if is_favorite_expr in {"is_favorite", "favorite"}:
        is_favorite_expr = f"COALESCE({is_favorite_expr}, 0)"

    drop_password_expr = _pick_column_expr(
        columns,
        "drop_password",
        "content_password",
        "password",
        default="NULL",
    )
    file_name_expr = _pick_column_expr(columns, "file_name", default=slug_expr)
    mime_type_expr = _pick_column_expr(
        columns,
        "mime_type",
        "file_type",
        default="'application/octet-stream'",
    )
    size_bytes_expr = _pick_column_expr(columns, "size_bytes", "file_size", default="0")
    sha256_expr = _pick_column_expr(columns, "sha256", "file_hash", default="''")
    storage_key_expr = _pick_column_expr(columns, "storage_key", "location", default="''")
    title_expr = _pick_column_expr(columns, "title", default="NULL")
    description_expr = _pick_column_expr(columns, "description", default="NULL")
    created_at_expr = _pick_column_expr(columns, "created_at", default="CURRENT_TIMESTAMP")
    updated_at_expr = _pick_column_expr(columns, "updated_at", default="NULL")

    bind.execute(
        text(
            f"""
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
                {slug_expr},
                {access_scope_expr},
                {is_favorite_expr},
                {drop_password_expr},
                {file_name_expr},
                {mime_type_expr},
                {size_bytes_expr},
                {sha256_expr},
                {storage_key_expr},
                {title_expr},
                {description_expr},
                {created_at_expr},
                {updated_at_expr}
            FROM {table_name}
            WHERE {slug_expr} NOT IN (SELECT slug FROM drops)
            """
        )
    )
    bind.execute(text(f"DROP TABLE IF EXISTS {table_name}"))


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS drops (
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

    _copy_legacy_table_into_drops("content")
    _copy_legacy_table_into_drops("contents")


def downgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS content (
            id CHAR(32) NOT NULL PRIMARY KEY,
            key VARCHAR NOT NULL UNIQUE,
            password VARCHAR NULL,
            user_only BOOLEAN,
            favorite BOOLEAN,
            file_name VARCHAR NOT NULL,
            file_hash VARCHAR NOT NULL,
            file_type VARCHAR NOT NULL,
            file_size INTEGER NOT NULL,
            location VARCHAR NOT NULL,
            title VARCHAR NULL,
            description VARCHAR NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NULL
        )
        """
    )

    op.execute(
        """
        INSERT INTO content (
            id,
            key,
            password,
            user_only,
            favorite,
            file_name,
            file_hash,
            file_type,
            file_size,
            location,
            title,
            description,
            created_at,
            updated_at
        )
        SELECT
            id,
            slug,
            drop_password,
            CASE WHEN access_scope = 'private' THEN 1 ELSE 0 END,
            is_favorite,
            file_name,
            sha256,
            mime_type,
            size_bytes,
            storage_key,
            title,
            description,
            created_at,
            updated_at
        FROM drops
        """
    )

    op.execute("DROP TABLE IF EXISTS drops")
