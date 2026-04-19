import secrets
from datetime import datetime, timedelta, timezone

from app.application.auth.models import AuthSessionDTO, VerifySessionQuery
from app.application.auth.ports import (
    AuthSessionCreateInput,
    AuthSessionUnitOfWorkFactory,
    UserReadRepositoryPort,
)
from app.application.auth.types import AuthIdentity
from app.domain.auth.errors import SessionExpired, SessionInvalid


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _to_session_dto(record, *, username: str) -> AuthSessionDTO:
    return AuthSessionDTO(
        sid=record.sid,
        user_id=record.user_id,
        username=username,
        created_at=record.created_at,
        expires_at=record.expires_at,
        revoked_at=record.revoked_at,
    )


class CreateSessionUseCase:
    def __init__(self, session_ttl_seconds: int, uow_factory: AuthSessionUnitOfWorkFactory):
        self.session_ttl_seconds = session_ttl_seconds
        self.uow_factory = uow_factory

    async def execute(self, *, user_id: str, username: str) -> AuthSessionDTO:
        now = datetime.now(tz=timezone.utc)
        async with self.uow_factory() as uow:
            record = await uow.repository.create(
                AuthSessionCreateInput(
                    sid=secrets.token_urlsafe(32),
                    user_id=user_id,
                    created_at=now,
                    expires_at=now + timedelta(seconds=self.session_ttl_seconds),
                )
            )
            await uow.commit()
        return _to_session_dto(record, username=username)


class VerifySessionUseCase:
    def __init__(
        self,
        uow_factory: AuthSessionUnitOfWorkFactory,
        user_repository: UserReadRepositoryPort,
    ):
        self.uow_factory = uow_factory
        self.user_repository = user_repository

    async def execute(self, query: VerifySessionQuery) -> AuthIdentity:
        async with self.uow_factory() as uow:
            record = await uow.repository.get_by_sid(query.sid)
            if record is None or record.revoked_at is not None:
                raise SessionInvalid()

            expires_at = _normalize_datetime(record.expires_at)
            if expires_at <= datetime.now(tz=timezone.utc):
                await uow.repository.revoke_by_sid(query.sid)
                await uow.commit()
                raise SessionExpired()

            user = await self.user_repository.get_by_id(record.user_id)
            if user is None or user.disabled_at is not None:
                await uow.repository.revoke_by_sid(query.sid)
                await uow.commit()
                raise SessionInvalid()

            return AuthIdentity(user_id=user.id, username=user.username)


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
