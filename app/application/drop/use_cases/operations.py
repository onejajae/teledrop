from __future__ import annotations

from app.application.auth.types import AuthIdentity
from app.application.drop.models import (
    UNSET as COMMAND_UNSET,
    CreateDropCommand,
    DeleteDropCommand,
    DropDetailDTO,
    DropListDTO,
    DropListItemDTO,
    DropListQuery,
    DropMetaQuery,
    DropStreamQuery,
    UpdateDropCommand,
)
from app.application.drop.ports import (
    DropCreateInput,
    DropRepositoryPort,
    DropStoragePort,
    DropUnitOfWorkFactory,
    DropUpdateInput,
)
from app.application.drop.slug_service import DropSlugService
from app.domain.drop.entities import DropEntity
from app.domain.drop.errors import (
    DropAccessDeniedError,
    DropNotFoundError,
)
from app.domain.drop.policies import (
    RequestAuthContext,
    assert_drop_access_allowed,
    assert_drop_password_matches,
    normalize_drop_password,
)
from app.domain.drop.value_objects import AccessScope


def _assert_access(drop: DropEntity, auth: AuthIdentity | None):
    auth_ctx = RequestAuthContext(username=auth.username if auth else None)
    assert_drop_access_allowed(drop, auth_ctx)


def _assert_password(drop: DropEntity, password: str | None):
    assert_drop_password_matches(drop, password)


async def _get_by_slug_or_raise(repository: DropRepositoryPort, slug: str) -> DropEntity:
    drop = await repository.get_by_slug(slug)
    if drop is None:
        raise DropNotFoundError()
    return drop


def _to_list_dto(drop: DropEntity) -> DropListItemDTO:
    return DropListItemDTO(
        slug=drop.slug,
        title=drop.title,
        description=drop.description,
        file_name=drop.file_name,
        mime_type=drop.mime_type,
        size_bytes=drop.size_bytes,
        access_scope=drop.access_scope,
        is_favorite=drop.is_favorite,
        requires_password=drop.requires_password,
        created_at=drop.created_at,
        updated_at=drop.updated_at,
    )


def _to_detail_dto(drop: DropEntity) -> DropDetailDTO:
    list_dto = _to_list_dto(drop)
    return DropDetailDTO(
        slug=list_dto.slug,
        title=list_dto.title,
        description=list_dto.description,
        file_name=list_dto.file_name,
        mime_type=list_dto.mime_type,
        size_bytes=list_dto.size_bytes,
        access_scope=list_dto.access_scope,
        is_favorite=list_dto.is_favorite,
        requires_password=list_dto.requires_password,
        created_at=list_dto.created_at,
        updated_at=list_dto.updated_at,
        sha256=drop.sha256,
    )


class CreateDropUseCase:
    def __init__(
        self,
        storage: DropStoragePort,
        slug_service: DropSlugService,
        uow_factory: DropUnitOfWorkFactory,
    ):
        self.storage = storage
        self.slug_service = slug_service
        self.uow_factory = uow_factory

    async def execute(self, command: CreateDropCommand) -> DropDetailDTO:
        slug = await self.slug_service.resolve(command.slug)
        password = normalize_drop_password(command.drop_password)
        access_scope = command.access_scope

        if access_scope not in (AccessScope.PUBLIC, AccessScope.PRIVATE):
            access_scope = AccessScope.PRIVATE

        storage_key, sha256 = await self.storage.write_stream(command.file_stream)

        async with self.uow_factory() as uow:
            created = await uow.repository.create(
                DropCreateInput(
                    slug=slug,
                    access_scope=access_scope,
                    is_favorite=False,
                    drop_password=password,
                    file_name=command.file_name,
                    mime_type=command.mime_type,
                    size_bytes=command.size_bytes,
                    sha256=sha256,
                    storage_key=storage_key,
                    title=command.title,
                    description=command.description,
                )
            )
            await uow.commit()
        return _to_detail_dto(created)


class ListDropsUseCase:
    def __init__(
        self,
        repository: DropRepositoryPort,
        default_page_size: int,
        max_page_size: int,
    ):
        self.repository = repository
        self.default_page_size = default_page_size
        self.max_page_size = max_page_size

    async def execute(self, query: DropListQuery) -> DropListDTO:
        if query.auth.username is None:
            raise DropAccessDeniedError()

        page = max(query.page, 1)
        page_size = query.page_size or self.default_page_size
        page_size = min(max(page_size, 1), self.max_page_size)

        total = await self.repository.count()
        items = await self.repository.list(
            limit=page_size,
            offset=(page - 1) * page_size,
            sort=query.sort,
            order=(query.order or "desc").lower(),
        )

        return DropListDTO(
            items=[_to_list_dto(item) for item in items],
            page=page,
            page_size=page_size,
            total=total,
        )


class GetDropMetaUseCase:
    def __init__(self, repository: DropRepositoryPort):
        self.repository = repository

    async def execute(self, query: DropMetaQuery) -> DropDetailDTO:
        drop = await _get_by_slug_or_raise(self.repository, query.slug)
        _assert_access(drop, query.auth)
        _assert_password(drop, query.drop_password)
        return _to_detail_dto(drop)

    async def execute_for_display(self, slug: str, auth: AuthIdentity | None) -> DropDetailDTO:
        drop = await _get_by_slug_or_raise(self.repository, slug)
        _assert_access(drop, auth)
        return _to_detail_dto(drop)


class GetDropStreamSourceUseCase:
    def __init__(self, repository: DropRepositoryPort, storage: DropStoragePort):
        self.repository = repository
        self.storage = storage

    async def execute(self, query: DropStreamQuery) -> tuple[DropDetailDTO, str]:
        drop = await _get_by_slug_or_raise(self.repository, query.slug)
        _assert_access(drop, query.auth)
        _assert_password(drop, query.drop_password)
        return _to_detail_dto(drop), drop.storage_key

    async def iter_stream_range(self, storage_key: str, start: int, end: int):
        async for chunk in self.storage.stream_range(storage_key, start, end):
            yield chunk


class UpdateDropUseCase:
    def __init__(
        self,
        uow_factory: DropUnitOfWorkFactory,
    ):
        self.uow_factory = uow_factory

    async def execute(self, command: UpdateDropCommand) -> DropDetailDTO:
        async with self.uow_factory() as uow:
            drop = await _get_by_slug_or_raise(uow.repository, command.slug)
            _assert_password(drop, command.current_password)

            update = DropUpdateInput()
            if command.title is not COMMAND_UNSET:
                update.title = command.title
            if command.description is not COMMAND_UNSET:
                update.description = command.description
            if command.access_scope is not COMMAND_UNSET:
                update.access_scope = command.access_scope
            if command.is_favorite is not COMMAND_UNSET:
                update.is_favorite = command.is_favorite
            if command.new_password is not COMMAND_UNSET:
                update.drop_password = normalize_drop_password(command.new_password)

            updated = await uow.repository.update_by_slug(command.slug, update)
            if updated is None:
                raise DropNotFoundError()
            await uow.commit()
        return _to_detail_dto(updated)


class DeleteDropUseCase:
    def __init__(
        self,
        storage: DropStoragePort,
        uow_factory: DropUnitOfWorkFactory,
    ):
        self.storage = storage
        self.uow_factory = uow_factory

    async def execute(self, command: DeleteDropCommand) -> None:
        source_key = ""
        staged_key: str | None = None
        try:
            async with self.uow_factory() as uow:
                drop = await _get_by_slug_or_raise(uow.repository, command.slug)
                _assert_password(drop, command.current_password)

                source_key, staged_key = await self.storage.stage_delete(drop.storage_key)
                deleted = await uow.repository.delete_by_slug(command.slug)
                if not deleted:
                    raise DropNotFoundError()
                await uow.commit()
        except Exception:
            if staged_key is not None:
                await self.storage.rollback_staged_delete(source_key, staged_key)
            raise

        if staged_key is not None:
            await self.storage.finalize_staged_delete(staged_key)


class CheckSlugAvailabilityUseCase:
    def __init__(self, slug_service: DropSlugService):
        self.slug_service = slug_service

    async def execute(self, slug: str) -> bool:
        return await self.slug_service.is_available(slug)


__all__ = [
    "CheckSlugAvailabilityUseCase",
    "CreateDropUseCase",
    "DeleteDropUseCase",
    "GetDropMetaUseCase",
    "GetDropStreamSourceUseCase",
    "ListDropsUseCase",
    "UpdateDropUseCase",
]
