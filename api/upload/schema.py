from datetime import datetime

from pydantic import BaseModel


class UploadComplete(BaseModel):
    filename: str
    file_size: int

    key: str

    title: str
    description: str | None
    datetime: datetime

    is_anonymous: bool

    user_id: int | None
    user_only: bool


class UploadListRequest(BaseModel):
    access_token: str
