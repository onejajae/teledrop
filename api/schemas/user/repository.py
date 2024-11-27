from sqlmodel import SQLModel
from datetime import datetime


class UserRepositoryCreate(SQLModel):
    username: str
    password: str
    created_at: datetime


class UserRepositoryRead(SQLModel):
    id: int
    username: str
    password: str
    created_at: datetime
