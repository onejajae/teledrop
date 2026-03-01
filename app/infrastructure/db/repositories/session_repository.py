from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import TypeVar

import anyio.to_thread
from sqlmodel import Session, select

from app.application.auth.ports import (
    AuthSessionCreateInput,
    AuthSessionRecord,
    AuthSessionRepositoryPort,
)
from app.infrastructure.db.models.auth import AuthSession


T = TypeVar("T")


class SQLModelSessionRepository(AuthSessionRepositoryPort):
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

    async def create(self, auth_session: AuthSessionCreateInput) -> AuthSessionRecord:
        if self._session is not None:
            return self._create_in_bound_session(self._session, auth_session)
        return await anyio.to_thread.run_sync(self._create_with_new_session, auth_session)

    async def get_by_sid(self, sid: str) -> AuthSessionRecord | None:
        if self._session is not None:
            return self._get_by_sid_in_session(self._session, sid)
        return await anyio.to_thread.run_sync(self._get_by_sid_with_new_session, sid)

    async def revoke_by_sid(self, sid: str) -> AuthSessionRecord | None:
        if self._session is not None:
            return self._revoke_by_sid_in_bound_session(self._session, sid)
        return await anyio.to_thread.run_sync(self._revoke_by_sid_with_new_session, sid)

    def _session_factory_required(self) -> Callable[[], Session]:
        if self._session_factory is None:
            raise RuntimeError("Session factory is not available for unbound repository usage.")
        return self._session_factory

    def _with_new_session(self, operation: Callable[[Session], T]) -> T:
        with self._session_factory_required()() as session:
            return operation(session)

    def _create_with_new_session(self, auth_session: AuthSessionCreateInput) -> AuthSessionRecord:
        return self._with_new_session(lambda session: self._create_in_new_session(session, auth_session))

    def _create_in_new_session(
        self,
        session: Session,
        auth_session: AuthSessionCreateInput,
    ) -> AuthSessionRecord:
        row = AuthSession(
            sid=auth_session.sid,
            username=auth_session.username,
            created_at=auth_session.created_at,
            expires_at=auth_session.expires_at,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return self._to_record(row)

    def _create_in_bound_session(
        self,
        session: Session,
        auth_session: AuthSessionCreateInput,
    ) -> AuthSessionRecord:
        row = AuthSession(
            sid=auth_session.sid,
            username=auth_session.username,
            created_at=auth_session.created_at,
            expires_at=auth_session.expires_at,
        )
        session.add(row)
        session.flush()
        session.refresh(row)
        return self._to_record(row)

    def _get_by_sid_with_new_session(self, sid: str) -> AuthSessionRecord | None:
        return self._with_new_session(lambda session: self._get_by_sid_in_session(session, sid))

    def _get_by_sid_in_session(self, session: Session, sid: str) -> AuthSessionRecord | None:
        row = self._get_auth_session_by_sid(session, sid)
        return self._to_record(row) if row else None

    def _revoke_by_sid_with_new_session(self, sid: str) -> AuthSessionRecord | None:
        return self._with_new_session(lambda session: self._revoke_by_sid_in_new_session(session, sid))

    def _get_auth_session_by_sid(self, session: Session, sid: str) -> AuthSession | None:
        query = select(AuthSession).where(AuthSession.sid == sid)
        return session.exec(query).one_or_none()

    def _revoke_by_sid_in_new_session(
        self,
        session: Session,
        sid: str,
    ) -> AuthSessionRecord | None:
        row = self._get_auth_session_by_sid(session, sid)
        if row is None:
            return None
        row.revoked_at = datetime.now(timezone.utc)
        session.add(row)
        session.commit()
        session.refresh(row)
        return self._to_record(row)

    def _revoke_by_sid_in_bound_session(
        self,
        session: Session,
        sid: str,
    ) -> AuthSessionRecord | None:
        row = self._get_auth_session_by_sid(session, sid)
        if row is None:
            return None
        row.revoked_at = datetime.now(timezone.utc)
        session.add(row)
        session.flush()
        session.refresh(row)
        return self._to_record(row)

    def _to_record(self, row: AuthSession) -> AuthSessionRecord:
        return AuthSessionRecord(
            sid=row.sid,
            username=row.username,
            created_at=row.created_at,
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
        )
