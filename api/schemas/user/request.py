from sqlmodel import SQLModel


class UserCreateRequest(SQLModel):
    username: str
    password: str
    register_code: str | None = None
