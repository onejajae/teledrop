from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO

from app.application.auth.types import AuthIdentity
from app.application.drop.sentinel import UNSET
from app.domain.drop.value_objects import AccessScope, DropSortField


@dataclass(slots=True)
class CreateDropCommand:
    file_stream: BinaryIO
    file_name: str
    mime_type: str
    size_bytes: int
    slug: str | None
    access_scope: AccessScope
    drop_password: str | None
    title: str | None
    description: str | None


@dataclass(slots=True)
class UpdateDropCommand:
    slug: str
    current_password: str | None
    title: str | None | object = UNSET
    description: str | None | object = UNSET
    access_scope: AccessScope | object = UNSET
    is_favorite: bool | object = UNSET
    new_password: str | None | object = UNSET


@dataclass(slots=True)
class DeleteDropCommand:
    slug: str
    current_password: str | None


@dataclass(slots=True)
class DropListQuery:
    page: int
    page_size: int
    sort: DropSortField
    order: str
    auth: AuthIdentity


@dataclass(slots=True)
class DropMetaQuery:
    slug: str
    drop_password: str | None
    auth: AuthIdentity | None


@dataclass(slots=True)
class DropStreamQuery:
    slug: str
    drop_password: str | None
    auth: AuthIdentity | None


@dataclass(slots=True)
class DropListItemDTO:
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


@dataclass(slots=True)
class DropDetailDTO(DropListItemDTO):
    sha256: str


@dataclass(slots=True)
class DropListDTO:
    items: list[DropListItemDTO]
    page: int
    page_size: int
    total: int


__all__ = [
    "CreateDropCommand",
    "DeleteDropCommand",
    "DropDetailDTO",
    "DropListDTO",
    "DropListItemDTO",
    "DropListQuery",
    "DropMetaQuery",
    "DropStreamQuery",
    "UNSET",
    "UpdateDropCommand",
]
