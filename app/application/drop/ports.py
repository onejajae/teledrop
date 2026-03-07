from dataclasses import dataclass
from types import TracebackType
from typing import AsyncIterator, BinaryIO, Protocol
from collections.abc import Callable

from app.application.drop.sentinel import UNSET
from app.domain.drop.entities import DropEntity
from app.domain.drop.value_objects import AccessScope, DropSortField


@dataclass(slots=True)
class DropCreateInput:
    slug: str
    access_scope: AccessScope
    is_favorite: bool
    drop_password: str | None
    file_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    storage_key: str
    title: str | None
    description: str | None


@dataclass(slots=True)
class DropUpdateInput:
    title: str | None | object = UNSET
    description: str | None | object = UNSET
    access_scope: AccessScope | object = UNSET
    is_favorite: bool | object = UNSET
    drop_password: str | None | object = UNSET


class DropReadRepositoryPort(Protocol):
    async def list(
        self,
        *,
        limit: int,
        offset: int,
        sort: DropSortField,
        order: str,
    ) -> list[DropEntity]: ...

    async def count(self) -> int: ...

    async def get_by_slug(self, slug: str) -> DropEntity | None: ...


class DropMutationRepositoryPort(Protocol):
    async def create(self, data: DropCreateInput) -> DropEntity: ...

    async def get_by_slug(self, slug: str) -> DropEntity | None: ...

    async def update_by_slug(self, slug: str, data: DropUpdateInput) -> DropEntity | None: ...

    async def delete_by_slug(self, slug: str) -> bool: ...


class DropSlugCandidateGeneratorPort(Protocol):
    async def generate_candidate(self) -> str: ...


class DropStoragePort(Protocol):
    async def write_stream(self, file_stream: BinaryIO) -> tuple[str, str]: ...

    async def stage_delete(self, storage_key: str) -> tuple[str, str | None]: ...

    async def rollback_staged_delete(self, source_key: str, staged_key: str) -> None: ...

    async def finalize_staged_delete(self, staged_key: str) -> None: ...

    async def stream_range(
        self, storage_key: str, start: int, end: int
    ) -> AsyncIterator[bytes]: ...


class DropUnitOfWorkPort(Protocol):
    repository: DropMutationRepositoryPort

    async def __aenter__(self) -> "DropUnitOfWorkPort": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


DropUnitOfWorkFactory = Callable[[], DropUnitOfWorkPort]


__all__ = [
    "UNSET",
    "DropCreateInput",
    "DropMutationRepositoryPort",
    "DropReadRepositoryPort",
    "DropSlugCandidateGeneratorPort",
    "DropStoragePort",
    "DropUnitOfWorkFactory",
    "DropUnitOfWorkPort",
    "DropUpdateInput",
]
