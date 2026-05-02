from datetime import datetime

from pydantic import BaseModel

from app.application.drop.models import DropDetailDTO, DropListDTO, DropListItemDTO
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

    @classmethod
    def from_dto(cls, item: DropListItemDTO) -> "DropListItemResponse":
        return cls(
            slug=item.slug,
            title=item.title,
            description=item.description,
            file_name=item.file_name,
            mime_type=item.mime_type,
            size_bytes=item.size_bytes,
            access_scope=item.access_scope,
            is_favorite=item.is_favorite,
            requires_password=item.requires_password,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


class DropDetailResponse(DropListItemResponse):
    sha256: str

    @classmethod
    def from_dto(cls, item: DropDetailDTO) -> "DropDetailResponse":
        return cls(
            **DropListItemResponse.from_dto(item).model_dump(),
            sha256=item.sha256,
        )


class DropListResponse(BaseModel):
    items: list[DropListItemResponse]
    page: int
    page_size: int
    total: int

    @classmethod
    def from_dto(cls, data: DropListDTO) -> "DropListResponse":
        return cls(
            items=[DropListItemResponse.from_dto(item) for item in data.items],
            page=data.page,
            page_size=data.page_size,
            total=data.total,
        )


class SlugAvailabilityResponse(BaseModel):
    available: bool


class DropPatchRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    access_scope: AccessScope | None = None
    is_favorite: bool | None = None
    new_password: str | None = None
