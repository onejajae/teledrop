from collections.abc import Callable
from types import TracebackType

from sqlmodel import Session

from app.application.auth.ports import UserUnitOfWorkPort
from app.infrastructure.db.repositories.user_repository import (
    SQLModelUserMutationRepository,
    USER_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR,
)
from app.infrastructure.db.uow_base import BaseSQLModelUnitOfWork


class SQLModelUserUnitOfWork(
    BaseSQLModelUnitOfWork[SQLModelUserMutationRepository],
    UserUnitOfWorkPort,
):
    def __init__(self, session_factory: Callable[[], Session]):
        super().__init__(
            session_factory=session_factory,
            repository_factory=lambda session: SQLModelUserMutationRepository(
                session=session,
                inactive_session_error=USER_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR,
            ),
            inactive_session_error=USER_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR,
        )

    async def __aenter__(self) -> "SQLModelUserUnitOfWork":
        await super().__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        return await super().__aexit__(exc_type, exc, tb)
