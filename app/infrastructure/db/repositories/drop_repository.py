from collections.abc import Callable
from datetime import datetime, timezone

import anyio.to_thread
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.application.drop.ports import (
    UNSET,
    DropCreateInput,
    DropRepositoryPort,
    DropUpdateInput,
)
from app.domain.drop.entities import DropEntity
from app.domain.drop.errors import DropSlugUnavailableError
from app.domain.drop.value_objects import AccessScope, DropSortField
from app.infrastructure.db.models.drop import DropRecord


DROP_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR = "Drop UnitOfWork session is not active."


def _build_record(data: DropCreateInput) -> DropRecord:
    now = datetime.now(timezone.utc)
    return DropRecord(
        owner_user_id=data.owner_user_id,
        slug=data.slug,
        access_scope=data.access_scope.value,
        is_favorite=data.is_favorite,
        drop_password=data.drop_password,
        file_name=data.file_name,
        mime_type=data.mime_type,
        size_bytes=data.size_bytes,
        sha256=data.sha256,
        storage_key=data.storage_key,
        title=data.title,
        description=data.description,
        created_at=now,
        updated_at=None,
    )


def _find_by_slug_row(session: Session, slug: str) -> DropRecord | None:
    query = select(DropRecord).where(DropRecord.slug == slug)
    return session.exec(query).one_or_none()


def _to_entity(row: DropRecord) -> DropEntity:
    return DropEntity(
        id=row.id.hex,
        owner_user_id=row.owner_user_id,
        slug=row.slug,
        access_scope=AccessScope(row.access_scope),
        is_favorite=bool(row.is_favorite),
        drop_password=row.drop_password,
        file_name=row.file_name,
        mime_type=row.mime_type,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        storage_key=row.storage_key,
        title=row.title,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _apply_update(row: DropRecord, data: DropUpdateInput) -> None:
    row.updated_at = datetime.now(timezone.utc)
    if data.title is not UNSET:
        row.title = data.title
    if data.description is not UNSET:
        row.description = data.description
    if data.access_scope is not UNSET:
        row.access_scope = data.access_scope.value
    if data.is_favorite is not UNSET:
        row.is_favorite = data.is_favorite
    if data.drop_password is not UNSET:
        row.drop_password = data.drop_password


class SQLModelDropRepository(DropRepositoryPort):
    def __init__(
        self,
        *,
        session_factory: Callable[[], Session] | None = None,
        session: Session | None = None,
        inactive_session_error: str = DROP_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR,
    ):
        self._session_factory = session_factory
        self._session = session
        self._inactive_session_error = inactive_session_error

    def deactivate(self) -> None:
        self._session = None

    def _require_session(self) -> Session:
        if self._session is None:
            raise RuntimeError(self._inactive_session_error)
        return self._session

    def _with_new_session(self, operation: Callable[[Session], object]):
        if self._session_factory is None:
            raise RuntimeError(self._inactive_session_error)
        with self._session_factory() as session:
            return operation(session)

    def _with_read_session(self, operation: Callable[[Session], object]):
        if self._session is not None:
            return operation(self._session)
        return self._with_new_session(operation)

    async def list(
        self,
        *,
        owner_user_id: str,
        limit: int,
        offset: int,
        sort: DropSortField,
        order: str,
    ) -> list[DropEntity]:
        return await anyio.to_thread.run_sync(
            self._list,
            owner_user_id,
            limit,
            offset,
            sort,
            order,
        )

    def _list(
        self,
        owner_user_id: str,
        limit: int,
        offset: int,
        sort: DropSortField,
        order: str,
    ) -> list[DropEntity]:
        def operation(session: Session) -> list[DropEntity]:
            sort_column = DropRecord.created_at
            if sort == DropSortField.TITLE:
                sort_column = func.coalesce(DropRecord.title, DropRecord.file_name)
            elif sort == DropSortField.SIZE_BYTES:
                sort_column = DropRecord.size_bytes

            ordered_column = sort_column.asc() if order == "asc" else sort_column.desc()
            query = (
                select(DropRecord)
                .where(DropRecord.owner_user_id == owner_user_id)
                .order_by(ordered_column)
                .limit(limit)
                .offset(offset)
            )
            rows = session.exec(query).all()
            return [_to_entity(row) for row in rows]

        return self._with_read_session(operation)

    async def count(self, *, owner_user_id: str) -> int:
        return await anyio.to_thread.run_sync(self._count, owner_user_id)

    def _count(self, owner_user_id: str) -> int:
        def operation(session: Session) -> int:
            query = (
                select(func.count())
                .select_from(DropRecord)
                .where(DropRecord.owner_user_id == owner_user_id)
            )
            result = session.exec(query).one()
            return int(result)

        return self._with_read_session(operation)

    async def get_by_slug(self, slug: str) -> DropEntity | None:
        return await anyio.to_thread.run_sync(self._get_by_slug, slug)

    def _get_by_slug(self, slug: str) -> DropEntity | None:
        def operation(session: Session) -> DropEntity | None:
            row = _find_by_slug_row(session, slug)
            if row is None:
                return None
            return _to_entity(row)

        return self._with_read_session(operation)

    async def get_owned_by_slug(
        self, slug: str, *, owner_user_id: str
    ) -> DropEntity | None:
        return await anyio.to_thread.run_sync(self._get_owned_by_slug, slug, owner_user_id)

    def _get_owned_by_slug(self, slug: str, owner_user_id: str) -> DropEntity | None:
        def operation(session: Session) -> DropEntity | None:
            row = _find_by_slug_row(session, slug)
            if row is None or row.owner_user_id != owner_user_id:
                return None
            return _to_entity(row)

        return self._with_read_session(operation)

    async def create(self, data: DropCreateInput) -> DropEntity:
        session = self._require_session()
        record = _build_record(data)
        session.add(record)
        try:
            session.flush()
        except IntegrityError as exc:
            if _is_slug_unique_violation(exc):
                raise DropSlugUnavailableError() from exc
            raise
        session.refresh(record)
        return _to_entity(record)

    async def update_by_slug(
        self,
        slug: str,
        *,
        owner_user_id: str,
        data: DropUpdateInput,
    ) -> DropEntity | None:
        session = self._require_session()
        row = _find_by_slug_row(session, slug)
        if row is None or row.owner_user_id != owner_user_id:
            return None
        _apply_update(row, data)
        session.add(row)
        session.flush()
        session.refresh(row)
        return _to_entity(row)

    async def delete_by_slug(self, slug: str, *, owner_user_id: str) -> bool:
        session = self._require_session()
        row = _find_by_slug_row(session, slug)
        if row is None or row.owner_user_id != owner_user_id:
            return False
        session.delete(row)
        session.flush()
        return True


class SQLModelDropReadRepository(SQLModelDropRepository):
    def __init__(self, session_factory: Callable[[], Session]):
        super().__init__(session_factory=session_factory)


class SQLModelDropMutationRepository(SQLModelDropRepository):
    def __init__(
        self,
        session: Session,
        *,
        inactive_session_error: str = DROP_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR,
    ):
        super().__init__(
            session=session,
            inactive_session_error=inactive_session_error,
        )


__all__ = [
    "DROP_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR",
    "SQLModelDropMutationRepository",
    "SQLModelDropReadRepository",
    "SQLModelDropRepository",
]


def _is_slug_unique_violation(exc: IntegrityError) -> bool:
    message = str(getattr(exc, "orig", exc))
    return "drops.slug" in message and "UNIQUE" in message.upper()
