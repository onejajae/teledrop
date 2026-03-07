from collections.abc import Callable
from datetime import datetime

import anyio.to_thread
from sqlmodel import Session, select

from app.application.auth.ports import (
    AuthApiKeyCreateInput,
    AuthApiKeyMutationRepositoryPort,
    AuthApiKeyReadRepositoryPort,
    AuthApiKeyRecord,
)
from app.infrastructure.db.models.auth_api_key import AuthApiKey
from app.infrastructure.db.repositories.session_bound import SessionBoundMutationRepository


AUTH_API_KEY_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR = (
    "API key UnitOfWork session is not active."
)


def _find_by_public_id(session: Session, public_id: str) -> AuthApiKey | None:
    query = select(AuthApiKey).where(AuthApiKey.public_id == public_id)
    return session.exec(query).one_or_none()


def _build_row(data: AuthApiKeyCreateInput) -> AuthApiKey:
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


def _to_record(row: AuthApiKey) -> AuthApiKeyRecord:
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


class SQLModelApiKeyReadRepository(AuthApiKeyReadRepositoryPort):
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def _with_new_session(self, operation: Callable[[Session], object]):
        with self._session_factory() as session:
            return operation(session)

    async def list_all(self) -> list[AuthApiKeyRecord]:
        return await anyio.to_thread.run_sync(self._list_all_with_new_session)

    def _list_all_with_new_session(self) -> list[AuthApiKeyRecord]:
        def operation(session: Session) -> list[AuthApiKeyRecord]:
            query = select(AuthApiKey).order_by(AuthApiKey.created_at.desc())
            return [_to_record(row) for row in session.exec(query).all()]

        return self._with_new_session(operation)

    async def get_by_public_id(self, public_id: str) -> AuthApiKeyRecord | None:
        return await anyio.to_thread.run_sync(self._get_by_public_id_with_new_session, public_id)

    def _get_by_public_id_with_new_session(self, public_id: str) -> AuthApiKeyRecord | None:
        def operation(session: Session) -> AuthApiKeyRecord | None:
            row = _find_by_public_id(session, public_id)
            if row is None:
                return None
            return _to_record(row)

        return self._with_new_session(operation)


class SQLModelApiKeyMutationRepository(
    SessionBoundMutationRepository,
    AuthApiKeyMutationRepositoryPort,
):
    def __init__(
        self,
        session: Session,
        *,
        inactive_session_error: str = AUTH_API_KEY_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR,
    ):
        super().__init__(session, inactive_session_error=inactive_session_error)

    async def create(self, data: AuthApiKeyCreateInput) -> AuthApiKeyRecord:
        session = self._require_session()
        row = _build_row(data)
        session.add(row)
        session.flush()
        session.refresh(row)
        return _to_record(row)

    async def get_by_public_id(self, public_id: str) -> AuthApiKeyRecord | None:
        row = _find_by_public_id(self._require_session(), public_id)
        if row is None:
            return None
        return _to_record(row)

    async def touch_last_used_at(
        self,
        public_id: str,
        used_at: datetime,
    ) -> AuthApiKeyRecord | None:
        session = self._require_session()
        row = _find_by_public_id(session, public_id)
        if row is None:
            return None
        row.last_used_at = used_at
        session.add(row)
        session.flush()
        session.refresh(row)
        return _to_record(row)

    async def revoke_by_public_id(
        self,
        public_id: str,
        revoked_at: datetime,
    ) -> AuthApiKeyRecord | None:
        session = self._require_session()
        row = _find_by_public_id(session, public_id)
        if row is None:
            return None
        row.revoked_at = revoked_at
        session.add(row)
        session.flush()
        session.refresh(row)
        return _to_record(row)

    async def delete_by_public_id(self, public_id: str) -> bool:
        session = self._require_session()
        row = _find_by_public_id(session, public_id)
        if row is None:
            return False
        session.delete(row)
        session.flush()
        return True


__all__ = [
    "AUTH_API_KEY_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR",
    "SQLModelApiKeyMutationRepository",
    "SQLModelApiKeyReadRepository",
]
