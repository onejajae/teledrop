from sqlmodel import SQLModel
from datetime import datetime


class UserCreateRequest(SQLModel):
    username: str
    password: str
    register_code: str | None = None


class UserInfoResponse(SQLModel):
    id: int
    username: str
    created_at: datetime


class AccessTokenResponse(SQLModel):
    token: str
    type: str = "Bearer"


class UserAccessTokenResponse(SQLModel):
    username: str
    access_token: str
    type: str = "Bearer"


class UserInfoMinimalResponse(SQLModel):
    id: int
    username: str
