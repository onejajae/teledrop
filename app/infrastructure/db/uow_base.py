from collections.abc import Callable
from types import TracebackType
from typing import Generic, TypeVar

from sqlmodel import Session


RepositoryT = TypeVar("RepositoryT")


class BaseSQLModelUnitOfWork(Generic[RepositoryT]):
    repository: RepositoryT

    def __init__(
        self,
        session_factory: Callable[[], Session],
        repository_factory: Callable[[Session], RepositoryT],
        *,
        initial_repository: RepositoryT,
        inactive_session_error: str,
    ):
        self._session_factory = session_factory
        self._repository_factory = repository_factory
        self._inactive_session_error = inactive_session_error
        self._session: Session | None = None
        self.repository = initial_repository

    async def __aenter__(self) -> "BaseSQLModelUnitOfWork[RepositoryT]":
        self._session = self._session_factory()
        self.repository = self._repository_factory(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        if self._session is None:
            return None
        try:
            if exc_type is not None:
                self._session.rollback()
        finally:
            self._session.close()
            self._session = None
        return None

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError(self._inactive_session_error)
        self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError(self._inactive_session_error)
        self._session.rollback()
