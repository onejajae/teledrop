from sqlmodel import SQLModel
from datetime import datetime


class PostRepositoryUser(SQLModel):
    id: int
    username: str


class PostRepositoryCreate(SQLModel):
    key: str

    is_user_only: bool | None
    password: str | None

    filename: str
    filetype: str
    filesize: int
    location: str

    title: str | None
    description: str | None

    created_at: datetime
    updated_at: datetime | None = None

    user_id: int


from api.schemas.user.repository import UserRepositoryRead


class PostRepositoryRead(SQLModel):
    id: int
    key: str

    is_user_only: bool | None
    favorite: bool
    user: UserRepositoryRead

    filename: str
    filetype: str
    filesize: int
    location: str

    title: str | None
    description: str | None

    created_at: datetime
    updated_at: datetime | None

    password: str | None


class PostRepositoryUpdate(SQLModel):
    title: str | None = None
    description: str | None = None
    favorite: bool = False
    is_user_only: bool | None = False
    password: str | None = None
    updated_at: datetime
