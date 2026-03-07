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


@dataclass(slots=True)
class AuthApiKeyCreateInput:
    public_id: str
    name: str
    created_by_username: str
    key_hash: str
    created_at: datetime
    expires_at: datetime | None


@dataclass(slots=True)
class AuthApiKeyRecord:
    public_id: str
    name: str
    created_by_username: str
    key_hash: str
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None


class AuthSessionReadRepositoryPort(Protocol):
    async def get_by_sid(self, sid: str) -> AuthSessionRecord | None: ...


class AuthSessionMutationRepositoryPort(Protocol):
    async def create(self, data: AuthSessionCreateInput) -> AuthSessionRecord: ...

    async def get_by_sid(self, sid: str) -> AuthSessionRecord | None: ...

    async def revoke_by_sid(self, sid: str) -> AuthSessionRecord | None: ...


class AuthApiKeyReadRepositoryPort(Protocol):
    async def list_all(self) -> list[AuthApiKeyRecord]: ...

    async def get_by_public_id(self, public_id: str) -> AuthApiKeyRecord | None: ...


class AuthApiKeyMutationRepositoryPort(Protocol):
    async def create(self, data: AuthApiKeyCreateInput) -> AuthApiKeyRecord: ...

    async def get_by_public_id(self, public_id: str) -> AuthApiKeyRecord | None: ...

    async def touch_last_used_at(
        self,
        public_id: str,
        used_at: datetime,
    ) -> AuthApiKeyRecord | None: ...

    async def revoke_by_public_id(
        self,
        public_id: str,
        revoked_at: datetime,
    ) -> AuthApiKeyRecord | None: ...

    async def delete_by_public_id(self, public_id: str) -> bool: ...


class AuthSessionUnitOfWorkPort(Protocol):
    repository: AuthSessionMutationRepositoryPort

    async def __aenter__(self) -> "AuthSessionUnitOfWorkPort": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class AuthApiKeyUnitOfWorkPort(Protocol):
    repository: AuthApiKeyMutationRepositoryPort

    async def __aenter__(self) -> "AuthApiKeyUnitOfWorkPort": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


AuthSessionUnitOfWorkFactory = Callable[[], AuthSessionUnitOfWorkPort]
AuthApiKeyUnitOfWorkFactory = Callable[[], AuthApiKeyUnitOfWorkPort]


__all__ = [
    "AuthApiKeyCreateInput",
    "AuthApiKeyMutationRepositoryPort",
    "AuthApiKeyReadRepositoryPort",
    "AuthApiKeyRecord",
    "AuthApiKeyUnitOfWorkFactory",
    "AuthApiKeyUnitOfWorkPort",
    "AuthSessionCreateInput",
    "AuthSessionMutationRepositoryPort",
    "AuthSessionReadRepositoryPort",
    "AuthSessionRecord",
    "AuthSessionUnitOfWorkFactory",
    "AuthSessionUnitOfWorkPort",
]
