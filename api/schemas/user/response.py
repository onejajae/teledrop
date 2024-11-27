from sqlmodel import SQLModel
from datetime import datetime
from api.schemas.user.service import AccessToken


class UserInfoResponse(SQLModel):
    id: int
    username: str
    created_at: datetime


class UserTokenResponse(SQLModel):
    access_token: AccessToken
    username: str
