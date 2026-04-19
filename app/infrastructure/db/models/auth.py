from datetime import datetime

from sqlmodel import Field, SQLModel


class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_sessions"

    sid: str = Field(primary_key=True, index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


__all__ = ["AuthSession"]
