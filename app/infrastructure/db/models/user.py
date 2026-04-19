import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class UserRecord(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime
    updated_at: datetime
    disabled_at: datetime | None = Field(default=None, index=True)


__all__ = ["UserRecord"]
