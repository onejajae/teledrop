from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DownloadPreview(BaseModel):
    filename: str
    file_size: int
    content_type: str

    title: str
    description: str | None
    datetime: datetime

    key: str

    is_anonymous: bool
    user_only: bool

    url: str


class ContentListElement(BaseModel):
    size: int
    mime: str


class UploadListElement(BaseModel):
    filename: str
    key: str
    datetime: datetime
    content: ContentListElement
    user_only: bool
    model_config = ConfigDict(from_attributes=True)
