from collections.abc import Callable
from types import TracebackType
from typing import Generic, TypeVar

from sqlmodel import Session


RepositoryT = TypeVar("RepositoryT")


class BaseSQLModelUnitOfWork(Generic[RepositoryT]):
    def __init__(
        self,
        session_factory: Callable[[], Session],
        repository_factory: Callable[[Session], RepositoryT],
        *,
        inactive_session_error: str,
    ):
        self._session_factory = session_factory
        self._repository_factory = repository_factory
        self._inactive_session_error = inactive_session_error
        self._session: Session | None = None
        self._repository: RepositoryT | None = None

    @property
    def repository(self) -> RepositoryT:
        if self._repository is None or self._session is None:
            raise RuntimeError(self._inactive_session_error)
        return self._repository

    async def __aenter__(self) -> "BaseSQLModelUnitOfWork[RepositoryT]":
        self._session = self._session_factory()
        self._repository = self._repository_factory(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        if self._session is None:
            return None
        repository = self._repository
        try:
            if exc_type is not None:
                self._session.rollback()
        finally:
            if repository is not None:
                deactivate = getattr(repository, "deactivate", None)
                if callable(deactivate):
                    deactivate()
            self._session.close()
            self._session = None
            self._repository = None
        return None

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError(self._inactive_session_error)
        self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError(self._inactive_session_error)
        self._session.rollback()
