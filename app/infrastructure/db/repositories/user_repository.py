from collections.abc import Callable
import uuid

import anyio.to_thread
from sqlmodel import Session, select

from app.application.auth.ports import UserReadRepositoryPort, UserRecord
from app.infrastructure.db.models.user import UserRecord as UserModel


def _find_by_id(session: Session, user_id: str) -> UserModel | None:
    try:
        normalized_user_id = uuid.UUID(user_id)
    except ValueError:
        return None

    query = select(UserModel).where(UserModel.id == normalized_user_id)
    return session.exec(query).one_or_none()


def _find_by_username(session: Session, username: str) -> UserModel | None:
    query = select(UserModel).where(UserModel.username == username)
    return session.exec(query).one_or_none()


def _to_record(row: UserModel) -> UserRecord:
    return UserRecord(
        id=row.id.hex,
        username=row.username,
        password_hash=row.password_hash,
        created_at=row.created_at,
        updated_at=row.updated_at,
        disabled_at=row.disabled_at,
    )


class SQLModelUserReadRepository(UserReadRepositoryPort):
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def _with_new_session(self, operation: Callable[[Session], object]):
        with self._session_factory() as session:
            return operation(session)

    async def get_by_id(self, user_id: str) -> UserRecord | None:
        return await anyio.to_thread.run_sync(self._get_by_id_with_new_session, user_id)

    def _get_by_id_with_new_session(self, user_id: str) -> UserRecord | None:
        def operation(session: Session) -> UserRecord | None:
            row = _find_by_id(session, user_id)
            return _to_record(row) if row else None

        return self._with_new_session(operation)

    async def get_by_username(self, username: str) -> UserRecord | None:
        return await anyio.to_thread.run_sync(self._get_by_username_with_new_session, username)

    def _get_by_username_with_new_session(self, username: str) -> UserRecord | None:
        def operation(session: Session) -> UserRecord | None:
            row = _find_by_username(session, username)
            return _to_record(row) if row else None

        return self._with_new_session(operation)


__all__ = ["SQLModelUserReadRepository"]
