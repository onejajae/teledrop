import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class AuthApiKey(SQLModel, table=True):
    __tablename__ = "auth_api_keys"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    public_id: str = Field(index=True, unique=True)
    name: str
    created_by_username: str = Field(index=True)
    key_hash: str

    created_at: datetime
    expires_at: datetime | None = Field(default=None, index=True)
    last_used_at: datetime | None = None
    revoked_at: datetime | None = Field(default=None, index=True)


__all__ = ["AuthApiKey"]
