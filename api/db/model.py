from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    username: str = Field(index=True, unique=True)
    password: str

    created_at: datetime

    posts: list["Post"] = Relationship(back_populates="user")


class Post(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)

    password: str | None
    is_user_only: bool | None = True
    favorite: bool | None = False

    filename: str
    filetype: str
    filesize: int
    location: str

    title: str | None
    description: str | None

    created_at: datetime
    updated_at: datetime | None

    user: User | None = Relationship(back_populates="posts")
    user_id: int | None = Field(default=None, foreign_key="user.id")
