from sqlmodel import SQLModel
from datetime import datetime


class PostCreateResponse(SQLModel):
    id: int
    key: str

    is_user_only: bool | None
    favorite: bool
    user_id: int

    filename: str
    filetype: str
    filesize: int

    title: str | None
    description: str | None

    created_at: datetime
    updated_at: datetime | None

    required_password: bool


from api.schemas.user.router import UserInfoMinimalResponse


class PostCreateResponse(SQLModel):
    id: int
    key: str

    is_user_only: bool | None
    favorite: bool
    user: UserInfoMinimalResponse

    filename: str
    filetype: str
    filesize: int

    title: str | None
    description: str | None

    created_at: datetime
    updated_at: datetime | None

    required_password: bool


class PostPreviewResponse(SQLModel):
    id: int
    key: str

    is_user_only: bool | None
    favorite: bool
    user: UserInfoMinimalResponse

    filename: str
    filetype: str
    filesize: int

    title: str | None
    description: str | None

    created_at: datetime
    updated_at: datetime | None

    required_password: bool


class PostUpdateRequest(SQLModel):
    password: str | None = None

    title: str | None = None
    description: str | None = None
    is_user_only: bool | None = False

    new_password: str | None = None
    delete_password: bool | None = False


class PostListElement(SQLModel):
    id: int
    key: str

    is_user_only: bool
    favorite: bool

    title: str | None

    filename: str
    filetype: str
    filesize: int

    created_at: datetime
    updated_at: datetime | None

    required_password: bool


class PostListUserInfo(SQLModel):
    id: int
    username: str
    used_capacity: int | None = 0
    max_capacity: int = 1024 * 1024 * 1024 * 10


class PostListResponse(SQLModel):
    posts: list[PostListElement]
    # num_posts: int | None = 0
    # used_capacity: int | None = 0
    # max_capacity: int = 1024 * 1024 * 1024 * 10
    # user: PostListUserInfo
