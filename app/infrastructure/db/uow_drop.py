from collections.abc import Callable
from types import TracebackType

from sqlmodel import Session

from app.application.drop.ports import DropUnitOfWorkPort
from app.infrastructure.db.repositories.drop_repository import (
    DROP_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR,
    SQLModelDropMutationRepository,
)
from app.infrastructure.db.uow_base import BaseSQLModelUnitOfWork


class SQLModelDropUnitOfWork(
    BaseSQLModelUnitOfWork[SQLModelDropMutationRepository],
    DropUnitOfWorkPort,
):
    def __init__(self, session_factory: Callable[[], Session]):
        super().__init__(
            session_factory=session_factory,
            repository_factory=lambda session: SQLModelDropMutationRepository(
                session=session,
                inactive_session_error=DROP_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR,
            ),
            inactive_session_error=DROP_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR,
        )

    async def __aenter__(self) -> "SQLModelDropUnitOfWork":
        await super().__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        return await super().__aexit__(exc_type, exc, tb)
