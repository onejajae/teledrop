import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field
from pydantic import computed_field


# Content Models
class ContentBase(SQLModel):
    key: str = Field(index=True, unique=True, default=None)

    password: str | None

    user_only: bool | None = True
    favorite: bool | None = False

    file_name: str
    file_hash: str
    file_type: str
    file_size: int

    location: str

    title: str | None
    description: str | None

    created_at: datetime
    updated_at: datetime | None = None


class ContentCreate(ContentBase):
    pass


class ContentRead(ContentBase):
    id: uuid.UUID


class ContentPublic(ContentRead):
    id: uuid.UUID = Field(exclude=True)
    password: str | None = Field(exclude=True)
    location: str = Field(exclude=True)

    @computed_field
    @property
    def required_password(self) -> bool:
        return bool(self.password)


class ContentPublicListElement(ContentPublic):
    description: str | None = Field(exclude=True)
    file_hash: str = Field(exclude=True)
    updated_at: datetime | None = Field(exclude=True)


class ContentsPublic(SQLModel):
    contents: list[ContentPublicListElement]


class ContentUpdate(SQLModel):
    title: str | None = None
    description: str | None = None
    favorite: bool | None = None
    user_only: bool | None = None
    password: str | None = None
    updated_at: datetime


class ContentUpdateDetail(SQLModel):
    password: str | None = None

    title: str | None = None
    description: str | None = None


class ContentUpdatePermission(SQLModel):
    password: str | None = None
    user_only: bool


class ContentUpdatePassword(SQLModel):
    new_password: str | None


class ContentResetPassword(SQLModel):
    password: str | None = None


class ContentUpdateFavorite(SQLModel):
    password: str | None = None
    favorite: bool


class Content(ContentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


# Auth Models
class AccessToken(SQLModel):
    access_token: str
    exp: datetime
    type: str = "Bearer"


class TokenPayload(SQLModel):
    username: str
    exp: datetime = None


class AuthData(SQLModel):
    username: str | None

    read_permission: bool | None = False
    write_permission: bool | None = False


# APIKey Models
class APIKeyBase(SQLModel):
    key: str = Field(index=True, unique=True)

    description: str | None = None

    read_permission: bool
    write_permission: bool

    active: bool
    created_at: datetime
    updated_at: datetime | None = None


class APIKeyRead(APIKeyBase):
    pass


class APIKeyPublic(APIKeyRead):
    id: uuid.UUID = Field(exclude=True)


class APIKeysPublic(SQLModel):
    api_keys: list[APIKeyPublic]


class APIKeyCreate(APIKeyBase):
    pass


class APIKeyCreateRequest(SQLModel):
    description: str | None = None
    read_permission: bool | None = True
    write_permission: bool | None = None


class APIKeyUpdate(SQLModel):
    description: str | None = None
    read_permission: bool | None = None
    write_permission: bool | None = None
    active: bool | None = None
    updated_at: datetime


class APIKeyUpdatePermissions(SQLModel):
    key: str
    read_permission: bool
    write_permission: bool


class APIKeyUpdateDescription(SQLModel):
    key: str
    description: str


class APIKeyUpdateActive(SQLModel):
    key: str
    active: bool


class APIKey(APIKeyBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
