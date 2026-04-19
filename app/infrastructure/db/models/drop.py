import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class DropRecord(SQLModel, table=True):
    __tablename__ = "drops"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_user_id: str = Field(foreign_key="users.id", index=True)
    slug: str = Field(index=True, unique=True)

    access_scope: str = Field(index=True)
    is_favorite: bool = Field(default=False)
    drop_password: str | None = None

    file_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    storage_key: str

    title: str | None = None
    description: str | None = None

    created_at: datetime
    updated_at: datetime | None = None
