from __future__ import annotations

from collections.abc import Callable
from types import TracebackType

from sqlmodel import Session

from app.application.auth.ports import AuthSessionUnitOfWorkPort
from app.infrastructure.db.uow_base import BaseSQLModelUnitOfWork
from app.infrastructure.db.repositories.session_repository import SQLModelSessionRepository


class SQLModelAuthSessionUnitOfWork(
    BaseSQLModelUnitOfWork[SQLModelSessionRepository],
    AuthSessionUnitOfWorkPort,
):
    def __init__(self, session_factory: Callable[[], Session]):
        super().__init__(
            session_factory=session_factory,
            repository_factory=lambda session: SQLModelSessionRepository(session=session),
            initial_repository=SQLModelSessionRepository(session_factory=session_factory),
            inactive_session_error="Auth session UnitOfWork session is not active.",
        )

    async def __aenter__(self) -> "SQLModelAuthSessionUnitOfWork":
        await super().__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        return await super().__aexit__(exc_type, exc, tb)
