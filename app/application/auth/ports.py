from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Protocol


@dataclass(slots=True)
class UserRecord:
    id: str
    username: str
    password_hash: str
    created_at: datetime
    updated_at: datetime
    disabled_at: datetime | None


@dataclass(slots=True)
class UserCreateInput:
    username: str
    password_hash: str
    created_at: datetime
    updated_at: datetime
    disabled_at: datetime | None = None


@dataclass(slots=True)
class AuthSessionCreateInput:
    sid: str
    user_id: str
    created_at: datetime
    expires_at: datetime


@dataclass(slots=True)
class AuthSessionRecord:
    sid: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


@dataclass(slots=True)
class AuthApiKeyCreateInput:
    public_id: str
    name: str
    owner_user_id: str
    key_hash: str
    created_at: datetime
    expires_at: datetime | None


@dataclass(slots=True)
class AuthApiKeyRecord:
    public_id: str
    name: str
    owner_user_id: str
    key_hash: str
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None


class UserReadRepositoryPort(Protocol):
    async def get_by_id(self, user_id: str) -> UserRecord | None: ...

    async def get_by_username(self, username: str) -> UserRecord | None: ...


class UserMutationRepositoryPort(Protocol):
    async def create(self, data: UserCreateInput) -> UserRecord: ...

    async def get_by_username(self, username: str) -> UserRecord | None: ...


class AuthSessionRepositoryPort(Protocol):
    async def create(self, data: AuthSessionCreateInput) -> AuthSessionRecord: ...

    async def get_by_sid(self, sid: str) -> AuthSessionRecord | None: ...

    async def revoke_by_sid(self, sid: str) -> AuthSessionRecord | None: ...


class AuthApiKeyRepositoryPort(Protocol):
    async def create(self, data: AuthApiKeyCreateInput) -> AuthApiKeyRecord: ...

    async def list_for_owner(self, owner_user_id: str) -> list[AuthApiKeyRecord]: ...

    async def get_by_public_id(self, public_id: str) -> AuthApiKeyRecord | None: ...

    async def touch_last_used_at(
        self,
        public_id: str,
        used_at: datetime,
    ) -> AuthApiKeyRecord | None: ...

    async def revoke_by_public_id(
        self,
        public_id: str,
        owner_user_id: str,
        revoked_at: datetime,
    ) -> AuthApiKeyRecord | None: ...

    async def delete_by_public_id(self, public_id: str, owner_user_id: str) -> bool: ...


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


class UserUnitOfWorkPort(Protocol):
    repository: UserMutationRepositoryPort

    async def __aenter__(self) -> "UserUnitOfWorkPort": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class AuthApiKeyUnitOfWorkPort(Protocol):
    repository: AuthApiKeyRepositoryPort

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
UserUnitOfWorkFactory = Callable[[], UserUnitOfWorkPort]
AuthApiKeyUnitOfWorkFactory = Callable[[], AuthApiKeyUnitOfWorkPort]


__all__ = [
    "AuthApiKeyCreateInput",
    "AuthApiKeyRepositoryPort",
    "AuthApiKeyRecord",
    "AuthApiKeyUnitOfWorkFactory",
    "AuthApiKeyUnitOfWorkPort",
    "AuthSessionCreateInput",
    "AuthSessionRepositoryPort",
    "AuthSessionRecord",
    "AuthSessionUnitOfWorkFactory",
    "AuthSessionUnitOfWorkPort",
    "UserCreateInput",
    "UserMutationRepositoryPort",
    "UserReadRepositoryPort",
    "UserRecord",
    "UserUnitOfWorkFactory",
    "UserUnitOfWorkPort",
]
