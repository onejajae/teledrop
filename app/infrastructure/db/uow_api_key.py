from collections.abc import Callable
from types import TracebackType

from sqlmodel import Session

from app.application.auth.ports import AuthApiKeyUnitOfWorkPort
from app.infrastructure.db.repositories.api_key_repository import (
    AUTH_API_KEY_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR,
    SQLModelApiKeyMutationRepository,
)
from app.infrastructure.db.uow_base import BaseSQLModelUnitOfWork


class SQLModelApiKeyUnitOfWork(
    BaseSQLModelUnitOfWork[SQLModelApiKeyMutationRepository],
    AuthApiKeyUnitOfWorkPort,
):
    def __init__(self, session_factory: Callable[[], Session]):
        super().__init__(
            session_factory=session_factory,
            repository_factory=lambda session: SQLModelApiKeyMutationRepository(
                session=session,
                inactive_session_error=AUTH_API_KEY_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR,
            ),
            inactive_session_error=AUTH_API_KEY_MUTATION_REPOSITORY_INACTIVE_SESSION_ERROR,
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
