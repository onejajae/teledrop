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
    DropSlugUnavailableError,
)
from app.domain.drop.grants import DropPasswordCredential, DropPasswordGrantService
from app.domain.drop.policies import (
    RequestAuthContext,
    assert_drop_owner,
    assert_drop_access_allowed,
    is_drop_owner,
    assert_drop_password_matches,
    hash_drop_password,
    normalize_drop_password,
)
from app.domain.drop.value_objects import AccessScope
from app.core.utils import normalize_pagination


def _assert_access(drop: DropEntity, auth: AuthIdentity | None):
    auth_ctx = RequestAuthContext(
        user_id=auth.user_id if auth else None,
        username=auth.username if auth else None,
    )
    assert_drop_access_allowed(drop, auth_ctx)


def _is_owner(drop: DropEntity, auth: AuthIdentity | None) -> bool:
    auth_ctx = RequestAuthContext(
        user_id=auth.user_id if auth else None,
        username=auth.username if auth else None,
    )
    return is_drop_owner(drop, auth_ctx)


def _assert_owner(drop: DropEntity, auth: AuthIdentity | None):
    auth_ctx = RequestAuthContext(
        user_id=auth.user_id if auth else None,
        username=auth.username if auth else None,
    )
    assert_drop_owner(drop, auth_ctx)


def _assert_password(
    drop: DropEntity,
    credential: DropPasswordCredential | None,
    grant_service: DropPasswordGrantService,
):
    assert_drop_password_matches(drop, credential, grant_service)


async def _get_by_slug_or_raise(
    repository: DropRepositoryPort,
    slug: str,
) -> DropEntity:
    drop = await repository.get_by_slug(slug)
    if drop is None:
        raise DropNotFoundError()
    return drop


def _to_list_dto(drop: DropEntity) -> DropListItemDTO:
    return DropListItemDTO(
        owner_user_id=drop.owner_user_id,
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
        owner_user_id=list_dto.owner_user_id,
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
        max_upload_bytes: int,
    ):
        self.storage = storage
        self.slug_service = slug_service
        self.uow_factory = uow_factory
        self.max_upload_bytes = max_upload_bytes

    async def execute(self, command: CreateDropCommand) -> DropDetailDTO:
        requested_slug = normalize_drop_password(command.slug)
        slug = await self.slug_service.resolve(requested_slug)
        password_hash = hash_drop_password(command.drop_password)
        access_scope = command.access_scope

        if access_scope not in (AccessScope.PUBLIC, AccessScope.PRIVATE):
            access_scope = AccessScope.PRIVATE

        storage_key = ""
        try:
            storage_key, sha256 = await self.storage.write_stream(
                command.file_stream,
                max_bytes=self.max_upload_bytes,
            )

            last_slug_error: DropSlugUnavailableError | None = None
            for attempt in range(self.slug_service.max_attempts):
                if attempt > 0:
                    slug = await self.slug_service.resolve(None)

                try:
                    async with self.uow_factory() as uow:
                        created = await uow.repository.create(
                            DropCreateInput(
                                owner_user_id=command.owner_user_id,
                                slug=slug,
                                access_scope=access_scope,
                                is_favorite=False,
                                drop_password=password_hash,
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
                except DropSlugUnavailableError as exc:
                    last_slug_error = exc
                    if requested_slug is not None:
                        raise

            raise last_slug_error or DropSlugUnavailableError()
        except Exception:
            if storage_key:
                await self.storage.discard_upload(storage_key)
            raise

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
        if query.auth.user_id is None:
            raise DropAccessDeniedError()

        page, page_size = normalize_pagination(
            page=query.page,
            page_size=query.page_size,
            default_page_size=self.default_page_size,
            max_page_size=self.max_page_size,
        )

        total = await self.repository.count(owner_user_id=query.auth.user_id)
        items = await self.repository.list(
            owner_user_id=query.auth.user_id,
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
    def __init__(
        self,
        repository: DropRepositoryPort,
        grant_service: DropPasswordGrantService,
    ):
        self.repository = repository
        self.grant_service = grant_service

    async def execute(self, query: DropMetaQuery) -> DropDetailDTO:
        drop = await _get_by_slug_or_raise(self.repository, query.slug)
        _assert_access(drop, query.auth)
        if not _is_owner(drop, query.auth):
            _assert_password(drop, query.drop_password, self.grant_service)
        return _to_detail_dto(drop)

    async def issue_grant_token(self, query: DropMetaQuery) -> str | None:
        drop = await _get_by_slug_or_raise(self.repository, query.slug)
        _assert_access(drop, query.auth)
        _assert_password(drop, query.drop_password, self.grant_service)
        return self.grant_service.issue(drop.slug, drop.drop_password)

    async def execute_for_display(self, slug: str, auth: AuthIdentity | None) -> DropDetailDTO:
        drop = await _get_by_slug_or_raise(self.repository, slug)
        _assert_access(drop, auth)
        return _to_detail_dto(drop)


class GetDropStreamSourceUseCase:
    def __init__(
        self,
        repository: DropRepositoryPort,
        storage: DropStoragePort,
        grant_service: DropPasswordGrantService,
    ):
        self.repository = repository
        self.storage = storage
        self.grant_service = grant_service

    async def execute(self, query: DropStreamQuery) -> tuple[DropDetailDTO, str]:
        drop = await _get_by_slug_or_raise(self.repository, query.slug)
        _assert_access(drop, query.auth)
        if not _is_owner(drop, query.auth):
            _assert_password(drop, query.drop_password, self.grant_service)
        return _to_detail_dto(drop), drop.storage_key

    async def iter_stream_range(self, storage_key: str, start: int, end: int):
        async for chunk in self.storage.stream_range(storage_key, start, end):
            yield chunk


class UpdateDropUseCase:
    def __init__(
        self,
        uow_factory: DropUnitOfWorkFactory,
        grant_service: DropPasswordGrantService,
    ):
        self.uow_factory = uow_factory
        self.grant_service = grant_service

    async def execute(self, command: UpdateDropCommand) -> DropDetailDTO:
        async with self.uow_factory() as uow:
            drop = await _get_by_slug_or_raise(uow.repository, command.slug)
            _assert_owner(drop, command.auth)

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
                update.drop_password = hash_drop_password(command.new_password)

            updated = await uow.repository.update_by_slug(
                command.slug,
                owner_user_id=command.auth.user_id or "",
                data=update,
            )
            if updated is None:
                raise DropNotFoundError()
            await uow.commit()
        return _to_detail_dto(updated)


class DeleteDropUseCase:
    def __init__(
        self,
        storage: DropStoragePort,
        uow_factory: DropUnitOfWorkFactory,
        grant_service: DropPasswordGrantService,
    ):
        self.storage = storage
        self.uow_factory = uow_factory
        self.grant_service = grant_service

    async def execute(self, command: DeleteDropCommand) -> None:
        source_key = ""
        staged_key: str | None = None
        try:
            async with self.uow_factory() as uow:
                drop = await _get_by_slug_or_raise(uow.repository, command.slug)
                _assert_owner(drop, command.auth)

                source_key, staged_key = await self.storage.stage_delete(drop.storage_key)
                deleted = await uow.repository.delete_by_slug(
                    command.slug,
                    owner_user_id=command.auth.user_id or "",
                )
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
