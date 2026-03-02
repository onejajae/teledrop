from collections.abc import Callable
from datetime import datetime
from typing import TypeVar

import anyio.to_thread
from sqlmodel import Session, select

from app.application.auth.ports import (
    AuthApiKeyCreateInput,
    AuthApiKeyRecord,
    AuthApiKeyRepositoryPort,
)
from app.infrastructure.db.models.auth_api_key import AuthApiKey


T = TypeVar("T")


class SQLModelApiKeyRepository(AuthApiKeyRepositoryPort):
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

    async def create(self, data: AuthApiKeyCreateInput) -> AuthApiKeyRecord:
        if self._session is not None:
            return self._create_in_bound_session(self._session, data)
        return await anyio.to_thread.run_sync(self._create_with_new_session, data)

    async def list_all(self) -> list[AuthApiKeyRecord]:
        if self._session is not None:
            return self._list_all_in_session(self._session)
        return await anyio.to_thread.run_sync(self._list_all_with_new_session)

    async def get_by_public_id(self, public_id: str) -> AuthApiKeyRecord | None:
        if self._session is not None:
            return self._get_by_public_id_in_session(self._session, public_id)
        return await anyio.to_thread.run_sync(self._get_by_public_id_with_new_session, public_id)

    async def touch_last_used_at(
        self,
        public_id: str,
        used_at: datetime,
    ) -> AuthApiKeyRecord | None:
        if self._session is not None:
            return self._touch_last_used_at_in_bound_session(self._session, public_id, used_at)
        return await anyio.to_thread.run_sync(
            self._touch_last_used_at_with_new_session,
            public_id,
            used_at,
        )

    async def revoke_by_public_id(
        self,
        public_id: str,
        revoked_at: datetime,
    ) -> AuthApiKeyRecord | None:
        if self._session is not None:
            return self._revoke_by_public_id_in_bound_session(
                self._session,
                public_id,
                revoked_at,
            )
        return await anyio.to_thread.run_sync(
            self._revoke_by_public_id_with_new_session,
            public_id,
            revoked_at,
        )

    async def delete_by_public_id(self, public_id: str) -> bool:
        if self._session is not None:
            return self._delete_by_public_id_in_bound_session(self._session, public_id)
        return await anyio.to_thread.run_sync(self._delete_by_public_id_with_new_session, public_id)

    def _session_factory_required(self) -> Callable[[], Session]:
        if self._session_factory is None:
            raise RuntimeError("Session factory is not available for unbound repository usage.")
        return self._session_factory

    def _with_new_session(self, operation: Callable[[Session], T]) -> T:
        with self._session_factory_required()() as session:
            return operation(session)

    def _find_by_public_id(self, session: Session, public_id: str) -> AuthApiKey | None:
        query = select(AuthApiKey).where(AuthApiKey.public_id == public_id)
        return session.exec(query).one_or_none()

    def _build_row(self, data: AuthApiKeyCreateInput) -> AuthApiKey:
        return AuthApiKey(
            public_id=data.public_id,
            name=data.name,
            created_by_username=data.created_by_username,
            key_hash=data.key_hash,
            created_at=data.created_at,
            expires_at=data.expires_at,
            last_used_at=None,
            revoked_at=None,
        )

    def _create_with_new_session(self, data: AuthApiKeyCreateInput) -> AuthApiKeyRecord:
        return self._with_new_session(lambda session: self._create_in_new_session(session, data))

    def _create_in_new_session(
        self,
        session: Session,
        data: AuthApiKeyCreateInput,
    ) -> AuthApiKeyRecord:
        row = self._build_row(data)
        session.add(row)
        session.commit()
        session.refresh(row)
        return self._to_record(row)

    def _create_in_bound_session(
        self,
        session: Session,
        data: AuthApiKeyCreateInput,
    ) -> AuthApiKeyRecord:
        row = self._build_row(data)
        session.add(row)
        session.flush()
        session.refresh(row)
        return self._to_record(row)

    def _list_all_with_new_session(self) -> list[AuthApiKeyRecord]:
        return self._with_new_session(self._list_all_in_session)

    def _list_all_in_session(self, session: Session) -> list[AuthApiKeyRecord]:
        query = select(AuthApiKey).order_by(AuthApiKey.created_at.desc())
        return [self._to_record(row) for row in session.exec(query).all()]

    def _get_by_public_id_with_new_session(self, public_id: str) -> AuthApiKeyRecord | None:
        return self._with_new_session(
            lambda session: self._get_by_public_id_in_session(session, public_id)
        )

    def _get_by_public_id_in_session(
        self,
        session: Session,
        public_id: str,
    ) -> AuthApiKeyRecord | None:
        row = self._find_by_public_id(session, public_id)
        if row is None:
            return None
        return self._to_record(row)

    def _touch_last_used_at_with_new_session(
        self,
        public_id: str,
        used_at: datetime,
    ) -> AuthApiKeyRecord | None:
        return self._with_new_session(
            lambda session: self._touch_last_used_at_in_new_session(session, public_id, used_at)
        )

    def _touch_last_used_at_in_new_session(
        self,
        session: Session,
        public_id: str,
        used_at: datetime,
    ) -> AuthApiKeyRecord | None:
        row = self._find_by_public_id(session, public_id)
        if row is None:
            return None
        row.last_used_at = used_at
        session.add(row)
        session.commit()
        session.refresh(row)
        return self._to_record(row)

    def _touch_last_used_at_in_bound_session(
        self,
        session: Session,
        public_id: str,
        used_at: datetime,
    ) -> AuthApiKeyRecord | None:
        row = self._find_by_public_id(session, public_id)
        if row is None:
            return None
        row.last_used_at = used_at
        session.add(row)
        session.flush()
        session.refresh(row)
        return self._to_record(row)

    def _revoke_by_public_id_with_new_session(
        self,
        public_id: str,
        revoked_at: datetime,
    ) -> AuthApiKeyRecord | None:
        return self._with_new_session(
            lambda session: self._revoke_by_public_id_in_new_session(
                session,
                public_id,
                revoked_at,
            )
        )

    def _revoke_by_public_id_in_new_session(
        self,
        session: Session,
        public_id: str,
        revoked_at: datetime,
    ) -> AuthApiKeyRecord | None:
        row = self._find_by_public_id(session, public_id)
        if row is None:
            return None
        row.revoked_at = revoked_at
        session.add(row)
        session.commit()
        session.refresh(row)
        return self._to_record(row)

    def _revoke_by_public_id_in_bound_session(
        self,
        session: Session,
        public_id: str,
        revoked_at: datetime,
    ) -> AuthApiKeyRecord | None:
        row = self._find_by_public_id(session, public_id)
        if row is None:
            return None
        row.revoked_at = revoked_at
        session.add(row)
        session.flush()
        session.refresh(row)
        return self._to_record(row)

    def _delete_by_public_id_with_new_session(self, public_id: str) -> bool:
        return self._with_new_session(
            lambda session: self._delete_by_public_id_in_new_session(session, public_id)
        )

    def _delete_by_public_id_in_new_session(self, session: Session, public_id: str) -> bool:
        row = self._find_by_public_id(session, public_id)
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True

    def _delete_by_public_id_in_bound_session(self, session: Session, public_id: str) -> bool:
        row = self._find_by_public_id(session, public_id)
        if row is None:
            return False
        session.delete(row)
        session.flush()
        return True

    def _to_record(self, row: AuthApiKey) -> AuthApiKeyRecord:
        return AuthApiKeyRecord(
            public_id=row.public_id,
            name=row.name,
            created_by_username=row.created_by_username,
            key_hash=row.key_hash,
            created_at=row.created_at,
            expires_at=row.expires_at,
            last_used_at=row.last_used_at,
            revoked_at=row.revoked_at,
        )
