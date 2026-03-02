from collections.abc import Callable
from datetime import datetime, timezone
from typing import List, TypeVar

import anyio.to_thread
from sqlalchemy import func
from sqlmodel import Session, select

from app.application.drop.ports import (
    UNSET,
    DropCreateInput,
    DropRepositoryPort,
    DropUpdateInput,
)
from app.domain.drop.entities import DropEntity
from app.domain.drop.value_objects import AccessScope, DropSortField
from app.infrastructure.db.models.drop import DropRecord


T = TypeVar("T")


class SQLModelDropRepository(DropRepositoryPort):
    def __init__(
        self,
        session_factory: Callable[[], Session] | None = None,
        *,
        session: Session | None = None,
    ):
        if session_factory is None and session is None:
            raise ValueError("Either session_factory or session must be provided.")
        self._session_factory = session_factory
        self._session = session

    async def create(self, data: DropCreateInput) -> DropEntity:
        if self._session is not None:
            return self._create_in_bound_session(self._session, data)
        return await anyio.to_thread.run_sync(self._create_with_new_session, data)

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        sort: DropSortField,
        order: str,
    ) -> List[DropEntity]:
        if self._session is not None:
            return self._list_in_session(
                self._session,
                limit=limit,
                offset=offset,
                sort=sort,
                order=order,
            )
        return await anyio.to_thread.run_sync(self._list_with_new_session, limit, offset, sort, order)

    async def count(self) -> int:
        if self._session is not None:
            return self._count_in_session(self._session)
        return await anyio.to_thread.run_sync(self._count_with_new_session)

    async def get_by_slug(self, slug: str) -> DropEntity | None:
        if self._session is not None:
            return self._get_by_slug_in_session(self._session, slug)
        return await anyio.to_thread.run_sync(self._get_by_slug_with_new_session, slug)

    async def update_by_slug(self, slug: str, data: DropUpdateInput) -> DropEntity | None:
        if self._session is not None:
            return self._update_by_slug_in_bound_session(self._session, slug, data)
        return await anyio.to_thread.run_sync(self._update_by_slug_with_new_session, slug, data)

    async def delete_by_slug(self, slug: str) -> bool:
        if self._session is not None:
            return self._delete_by_slug_in_bound_session(self._session, slug)
        return await anyio.to_thread.run_sync(self._delete_by_slug_with_new_session, slug)

    def _session_factory_required(self) -> Callable[[], Session]:
        if self._session_factory is None:
            raise RuntimeError("Session factory is not available for unbound repository usage.")
        return self._session_factory

    def _with_new_session(self, operation: Callable[[Session], T]) -> T:
        with self._session_factory_required()() as session:
            return operation(session)

    def _create_with_new_session(self, data: DropCreateInput) -> DropEntity:
        return self._with_new_session(lambda session: self._create_in_new_session(session, data))

    def _build_record(self, data: DropCreateInput) -> DropRecord:
        now = datetime.now(timezone.utc)
        return DropRecord(
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

    def _create_in_new_session(
        self,
        session: Session,
        data: DropCreateInput,
    ) -> DropEntity:
        record = self._build_record(data)
        session.add(record)
        session.commit()
        session.refresh(record)
        return self._to_entity(record)

    def _create_in_bound_session(self, session: Session, data: DropCreateInput) -> DropEntity:
        record = self._build_record(data)
        session.add(record)
        session.flush()
        session.refresh(record)
        return self._to_entity(record)

    def _list_with_new_session(
        self,
        limit: int,
        offset: int,
        sort: DropSortField,
        order: str,
    ) -> List[DropEntity]:
        return self._with_new_session(
            lambda session: self._list_in_session(
                session,
                limit=limit,
                offset=offset,
                sort=sort,
                order=order,
            )
        )

    def _list_in_session(
        self,
        session: Session,
        *,
        limit: int,
        offset: int,
        sort: DropSortField,
        order: str,
    ) -> List[DropEntity]:
        sort_column = DropRecord.created_at
        if sort == DropSortField.TITLE:
            sort_column = func.coalesce(DropRecord.title, DropRecord.file_name)
        elif sort == DropSortField.SIZE_BYTES:
            sort_column = DropRecord.size_bytes

        sort_column = sort_column.asc() if order == "asc" else sort_column.desc()
        query = select(DropRecord).order_by(sort_column).limit(limit).offset(offset)
        rows = session.exec(query).all()
        return [self._to_entity(row) for row in rows]

    def _count_with_new_session(self) -> int:
        return self._with_new_session(self._count_in_session)

    def _count_in_session(self, session: Session) -> int:
        query = select(func.count()).select_from(DropRecord)
        result = session.exec(query).one()
        return int(result)

    def _get_by_slug_with_new_session(self, slug: str) -> DropEntity | None:
        return self._with_new_session(lambda session: self._get_by_slug_in_session(session, slug))

    def _get_by_slug_in_session(self, session: Session, slug: str) -> DropEntity | None:
        row = self._find_by_slug_row(session, slug)
        if row is None:
            return None
        return self._to_entity(row)

    def _update_by_slug_with_new_session(self, slug: str, data: DropUpdateInput) -> DropEntity | None:
        return self._with_new_session(lambda session: self._update_by_slug_in_new_session(session, slug, data))

    def _find_by_slug_row(self, session: Session, slug: str) -> DropRecord | None:
        query = select(DropRecord).where(DropRecord.slug == slug)
        return session.exec(query).one_or_none()

    def _apply_update(self, row: DropRecord, data: DropUpdateInput) -> None:
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

    def _update_by_slug_in_new_session(
        self,
        session: Session,
        slug: str,
        data: DropUpdateInput,
    ) -> DropEntity | None:
        row = self._find_by_slug_row(session, slug)
        if row is None:
            return None
        self._apply_update(row, data)
        session.add(row)
        session.commit()
        session.refresh(row)
        return self._to_entity(row)

    def _update_by_slug_in_bound_session(
        self,
        session: Session,
        slug: str,
        data: DropUpdateInput,
    ) -> DropEntity | None:
        row = self._find_by_slug_row(session, slug)
        if row is None:
            return None
        self._apply_update(row, data)
        session.add(row)
        session.flush()
        session.refresh(row)
        return self._to_entity(row)

    def _delete_by_slug_with_new_session(self, slug: str) -> bool:
        return self._with_new_session(lambda session: self._delete_by_slug_in_new_session(session, slug))

    def _delete_by_slug_in_new_session(self, session: Session, slug: str) -> bool:
        row = self._find_by_slug_row(session, slug)
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True

    def _delete_by_slug_in_bound_session(self, session: Session, slug: str) -> bool:
        row = self._find_by_slug_row(session, slug)
        if row is None:
            return False
        session.delete(row)
        session.flush()
        return True

    def _to_entity(self, row: DropRecord) -> DropEntity:
        return DropEntity(
            id=str(row.id),
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
