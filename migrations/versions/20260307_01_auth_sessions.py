"""add auth sessions table

Revision ID: 20260307_01
Revises: 20260302_01
Create Date: 2026-03-07 17:00:00
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260307_01"
down_revision: Union[str, Sequence[str], None] = "20260302_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_sessions (
            sid VARCHAR NOT NULL PRIMARY KEY,
            username VARCHAR NOT NULL,
            created_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL,
            revoked_at DATETIME NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_auth_sessions_sid
        ON auth_sessions (sid)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_auth_sessions_username
        ON auth_sessions (username)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_auth_sessions_sid")
    op.execute("DROP INDEX IF EXISTS ix_auth_sessions_username")
    op.execute("DROP TABLE IF EXISTS auth_sessions")
