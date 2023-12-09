from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    id: int
    username: str


class UserCreate(BaseModel):
    username: str
    password: str
    code: str | None = None


class AccessToken(BaseModel):
    access_token: str
    username: str
    token_type: str = "bearer"
