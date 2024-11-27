from sqlmodel import SQLModel
from datetime import datetime


class UserServiceCreate(SQLModel):
    username: str
    password: str
    register_code: str | None = None


class UserServiceRead(SQLModel):
    id: int
    username: str
    password: str
    created_at: datetime


class TokenPayload(SQLModel):
    user_id: int
    username: str
    exp: datetime = None


class AccessToken(SQLModel):
    token: str
    type: str = "Bearer"


class UserServiceMinimalRead(SQLModel):
    id: int
    username: str
