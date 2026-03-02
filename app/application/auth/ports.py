from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Protocol


@dataclass(slots=True)
class AuthSessionCreateInput:
    sid: str
    username: str
    created_at: datetime
    expires_at: datetime


@dataclass(slots=True)
class AuthSessionRecord:
    sid: str
    username: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


class AuthSessionRepositoryPort(Protocol):
    async def create(self, data: AuthSessionCreateInput) -> AuthSessionRecord: ...

    async def get_by_sid(self, sid: str) -> AuthSessionRecord | None: ...

    async def revoke_by_sid(self, sid: str) -> AuthSessionRecord | None: ...


class AuthSessionUnitOfWorkPort(Protocol):
    repository: AuthSessionRepositoryPort

    async def __aenter__(self) -> "AuthSessionUnitOfWorkPort": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


AuthSessionUnitOfWorkFactory = Callable[[], AuthSessionUnitOfWorkPort]
