from collections.abc import Callable
from datetime import datetime, timezone

import anyio.to_thread
from sqlmodel import Session, select

from app.application.auth.ports import (
    AuthSessionCreateInput,
    AuthSessionRepositoryPort,
    AuthSessionRecord,
)
from app.infrastructure.db.models.auth import AuthSession
from app.infrastructure.db.repositories.session_bound import SessionBoundMutationRepository


AUTH_SESSION_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR = (
    "Auth session UnitOfWork session is not active."
)


def _get_auth_session_by_sid(session: Session, sid: str) -> AuthSession | None:
    query = select(AuthSession).where(AuthSession.sid == sid)
    return session.exec(query).one_or_none()


def _to_record(row: AuthSession) -> AuthSessionRecord:
    return AuthSessionRecord(
        sid=row.sid,
        username=row.username,
        created_at=row.created_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
    )


class SQLModelSessionReadRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def _with_new_session(self, operation: Callable[[Session], object]):
        with self._session_factory() as session:
            return operation(session)

    async def get_by_sid(self, sid: str) -> AuthSessionRecord | None:
        return await anyio.to_thread.run_sync(self._get_by_sid_with_new_session, sid)

    def _get_by_sid_with_new_session(self, sid: str) -> AuthSessionRecord | None:
        def operation(session: Session) -> AuthSessionRecord | None:
            row = _get_auth_session_by_sid(session, sid)
            return _to_record(row) if row else None

        return self._with_new_session(operation)


class SQLModelSessionMutationRepository(
    SessionBoundMutationRepository,
    AuthSessionRepositoryPort,
):
    def __init__(
        self,
        session: Session,
        *,
        inactive_session_error: str = AUTH_SESSION_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR,
    ):
        super().__init__(session, inactive_session_error=inactive_session_error)

    async def create(self, auth_session: AuthSessionCreateInput) -> AuthSessionRecord:
        session = self._require_session()
        row = AuthSession(
            sid=auth_session.sid,
            username=auth_session.username,
            created_at=auth_session.created_at,
            expires_at=auth_session.expires_at,
        )
        session.add(row)
        session.flush()
        session.refresh(row)
        return _to_record(row)

    async def get_by_sid(self, sid: str) -> AuthSessionRecord | None:
        row = _get_auth_session_by_sid(self._require_session(), sid)
        return _to_record(row) if row else None

    async def revoke_by_sid(self, sid: str) -> AuthSessionRecord | None:
        session = self._require_session()
        row = _get_auth_session_by_sid(session, sid)
        if row is None:
            return None
        row.revoked_at = datetime.now(timezone.utc)
        session.add(row)
        session.flush()
        session.refresh(row)
        return _to_record(row)


__all__ = [
    "AUTH_SESSION_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR",
    "SQLModelSessionMutationRepository",
    "SQLModelSessionReadRepository",
]
