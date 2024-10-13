from datetime import datetime
from sqlmodel import SQLModel, Field
from pydantic import computed_field
from typing import Annotated


class UserCreate(SQLModel):
    username: str
    password: str
    register_code: str | None = None


class UserPublic(SQLModel):
    id: int

    username: str

    created_at: datetime | None = datetime.now()


class UserMinimal(SQLModel):
    username: str


class PostPublic(SQLModel):
    id: int
    key: str

    is_user_only: bool | None
    favorite: bool
    user: UserMinimal

    filename: str
    filetype: str
    filesize: int

    title: str | None
    description: str | None

    created_at: datetime
    updated_at: datetime | None

    password: Annotated[str | None, Field(exclude=True)]

    @computed_field
    @property
    def required_password(self) -> bool:
        return bool(self.password)


class PostMinimal(SQLModel):
    key: str

    is_user_only: bool
    favorite: bool

    filename: str
    filetype: str
    filesize: int

    title: str | None
    description: str | None

    created_at: datetime


class PostUpdate(SQLModel):
    password: str | None = None

    title: str | None = None
    description: str | None = None
    is_user_only: bool | None = False

    new_password: str | None = None
    delete_password: bool | None = False


class PostCreate(SQLModel):
    key: str | None
    password: str | None

    is_user_only: bool | None = False

    title: str | None
    description: str | None


class PostFavoriteUpdate(SQLModel):
    password: str | None = None
    favorite: bool


class PostPasswordReset(SQLModel):
    new_password: str


class PostListElement(SQLModel):
    id: int
    key: str

    password: Annotated[str | None, Field(exclude=True)]
    is_user_only: bool
    favorite: bool

    title: str | None

    filename: str
    filetype: str
    filesize: int

    created_at: datetime
    updated_at: datetime | None

    @computed_field
    @property
    def required_password(self) -> bool:
        return bool(self.password)


class Token(SQLModel):
    access_token: str
    token_type: str
    username: str
