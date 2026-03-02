"""add auth api keys table

Revision ID: 20260302_01
Revises: 20260221_01
Create Date: 2026-03-02 12:00:00
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260302_01"
down_revision: Union[str, Sequence[str], None] = "20260221_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_api_keys (
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
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_auth_api_keys_created_by_username
        ON auth_api_keys (created_by_username)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_auth_api_keys_expires_at
        ON auth_api_keys (expires_at)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_auth_api_keys_revoked_at
        ON auth_api_keys (revoked_at)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_auth_api_keys_created_by_username")
    op.execute("DROP INDEX IF EXISTS ix_auth_api_keys_expires_at")
    op.execute("DROP INDEX IF EXISTS ix_auth_api_keys_revoked_at")
    op.execute("DROP TABLE IF EXISTS auth_api_keys")
