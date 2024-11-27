from sqlmodel import SQLModel
from datetime import datetime
from pydantic import computed_field


class PostServiceCreate(SQLModel):
    key: str | None

    is_user_only: bool

    filename: str
    filetype: str
    filesize: int

    title: str | None
    description: str | None

    password: str | None


from api.schemas.user.service import UserServiceMinimalRead


class PostServiceRead(SQLModel):
    id: int
    key: str

    is_user_only: bool | None
    favorite: bool
    user: UserServiceMinimalRead

    filename: str
    filetype: str
    filesize: int

    title: str | None
    description: str | None

    created_at: datetime
    updated_at: datetime | None

    password: str | None

    @computed_field
    @property
    def required_password(self) -> bool:
        return bool(self.password)


class PostServiceUpdate(SQLModel):
    title: str | None = None
    description: str | None = None
    is_user_only: bool | None = False

    new_password: str | None = None
    delete_password: bool | None = False
