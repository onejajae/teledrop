from sqlmodel import SQLModel, Field


class PostCreate(SQLModel):
    key: str | None
    password: str | None

    is_user_only: bool | None = False

    title: str | None
    description: str | None
