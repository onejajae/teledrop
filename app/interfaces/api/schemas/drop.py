from datetime import datetime

from pydantic import BaseModel

from app.domain.drop.value_objects import AccessScope


class DropListItemResponse(BaseModel):
    slug: str
    title: str | None
    description: str | None
    file_name: str
    mime_type: str
    size_bytes: int
    access_scope: AccessScope
    is_favorite: bool
    requires_password: bool
    created_at: datetime
    updated_at: datetime | None


class DropDetailResponse(DropListItemResponse):
    sha256: str


class DropListResponse(BaseModel):
    items: list[DropListItemResponse]
    page: int
    page_size: int
    total: int


class SlugAvailabilityResponse(BaseModel):
    available: bool


class DropPatchRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    access_scope: AccessScope | None = None
    is_favorite: bool | None = None
    new_password: str | None = None
    current_password: str | None = None
