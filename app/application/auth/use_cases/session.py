from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from app.application.auth.models import AuthSessionDTO, VerifySessionQuery
from app.application.auth.ports import (
    AuthSessionCreateInput,
    AuthSessionRepositoryPort,
    AuthSessionUnitOfWorkFactory,
)
from app.domain.auth.errors import SessionExpired, SessionInvalid


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _to_session_dto(record) -> AuthSessionDTO:
    return AuthSessionDTO(
        sid=record.sid,
        username=record.username,
        created_at=record.created_at,
        expires_at=record.expires_at,
        revoked_at=record.revoked_at,
    )


class CreateSessionUseCase:
    def __init__(self, session_ttl_seconds: int, repository: AuthSessionRepositoryPort):
        self.session_ttl_seconds = session_ttl_seconds
        self.repository = repository

    async def execute(self, username: str) -> AuthSessionDTO:
        now = datetime.now(tz=timezone.utc)
        record = await self.repository.create(
            AuthSessionCreateInput(
                sid=secrets.token_urlsafe(32),
                username=username,
                created_at=now,
                expires_at=now + timedelta(seconds=self.session_ttl_seconds),
            )
        )
        return _to_session_dto(record)


class VerifySessionUseCase:
    def __init__(
        self,
        uow_factory: AuthSessionUnitOfWorkFactory,
    ):
        self.uow_factory = uow_factory

    async def execute(self, query: VerifySessionQuery) -> str:
        async with self.uow_factory() as uow:
            record = await uow.repository.get_by_sid(query.sid)
            if record is None or record.revoked_at is not None:
                raise SessionInvalid()

            expires_at = _normalize_datetime(record.expires_at)
            if expires_at <= datetime.now(tz=timezone.utc):
                await uow.repository.revoke_by_sid(query.sid)
                await uow.commit()
                raise SessionExpired()

            return record.username


class RevokeSessionUseCase:
    def __init__(
        self,
        uow_factory: AuthSessionUnitOfWorkFactory,
    ):
        self.uow_factory = uow_factory

    async def execute(self, sid: str) -> None:
        async with self.uow_factory() as uow:
            await uow.repository.revoke_by_sid(sid)
            await uow.commit()
