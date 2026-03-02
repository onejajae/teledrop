from collections.abc import Callable
from types import TracebackType

from sqlmodel import Session

from app.application.auth.ports import AuthApiKeyUnitOfWorkPort
from app.infrastructure.db.repositories.api_key_repository import SQLModelApiKeyRepository
from app.infrastructure.db.uow_base import BaseSQLModelUnitOfWork


class SQLModelApiKeyUnitOfWork(
    BaseSQLModelUnitOfWork[SQLModelApiKeyRepository],
    AuthApiKeyUnitOfWorkPort,
):
    def __init__(self, session_factory: Callable[[], Session]):
        super().__init__(
            session_factory=session_factory,
            repository_factory=lambda session: SQLModelApiKeyRepository(session=session),
            initial_repository=SQLModelApiKeyRepository(session_factory=session_factory),
            inactive_session_error="API key UnitOfWork session is not active.",
        )

    async def __aenter__(self) -> "SQLModelApiKeyUnitOfWork":
        await super().__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        return await super().__aexit__(exc_type, exc, tb)
