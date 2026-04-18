import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.application.auth.models import (
    ApiKeyDTO,
    CreateApiKeyCommand,
    CreatedApiKeyDTO,
    DeleteApiKeyCommand,
    RevokeApiKeyCommand,
    VerifyApiKeyQuery,
)
from app.application.auth.ports import (
    AuthApiKeyCreateInput,
    AuthApiKeyRepositoryPort,
    AuthApiKeyRecord,
    AuthApiKeyUnitOfWorkFactory,
)
from app.domain.auth.errors import ApiKeyInvalid, ApiKeyNotFound


API_KEY_PREFIX = "tdpk"
API_KEY_NAME_MAX_LENGTH = 100
_PUBLIC_ID_BYTES = 8
_SECRET_BYTES = 24
_MAX_GENERATION_ATTEMPTS = 10


def _is_public_id_collision(exc: IntegrityError) -> bool:
    constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if isinstance(constraint_name, str) and "public_id" in constraint_name.lower():
        return True

    message = str(exc.orig).lower()
    return "unique" in message and "public_id" in message


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _hash_key_material(public_id: str, secret: str) -> str:
    payload = f"{public_id}:{secret}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _build_token(public_id: str, secret: str) -> str:
    return f"{API_KEY_PREFIX}_{public_id}_{secret}"


def parse_api_key_token(api_key: str) -> tuple[str, str]:
    prefix, sep, remaining = api_key.partition("_")
    if not sep or prefix != API_KEY_PREFIX:
        raise ApiKeyInvalid()

    public_id, sep, secret = remaining.partition("_")
    if not sep or not public_id or not secret:
        raise ApiKeyInvalid()

    return public_id, secret


def _to_api_key_dto(record: AuthApiKeyRecord) -> ApiKeyDTO:
    return ApiKeyDTO(
        public_id=record.public_id,
        name=record.name,
        created_by_username=record.created_by_username,
        created_at=record.created_at,
        expires_at=record.expires_at,
        last_used_at=record.last_used_at,
        revoked_at=record.revoked_at,
    )


class CreateApiKeyUseCase:
    def __init__(self, uow_factory: AuthApiKeyUnitOfWorkFactory):
        self.uow_factory = uow_factory

    async def execute(self, command: CreateApiKeyCommand) -> CreatedApiKeyDTO:
        name = (command.name or "").strip()
        if not name or len(name) > API_KEY_NAME_MAX_LENGTH:
            raise ValueError("API key name must be between 1 and 100 characters.")

        now = datetime.now(tz=timezone.utc)
        expires_at = _normalize_datetime(command.expires_at)
        if expires_at is not None and expires_at <= now:
            raise ValueError("API key expiration must be in the future.")

        for _ in range(_MAX_GENERATION_ATTEMPTS):
            public_id = secrets.token_hex(_PUBLIC_ID_BYTES)
            secret = secrets.token_urlsafe(_SECRET_BYTES)
            try:
                async with self.uow_factory() as uow:
                    existing = await uow.repository.get_by_public_id(public_id)
                    if existing is not None:
                        continue

                    key_hash = _hash_key_material(public_id, secret)
                    created = await uow.repository.create(
                        AuthApiKeyCreateInput(
                            public_id=public_id,
                            name=name,
                            created_by_username=command.created_by_username,
                            key_hash=key_hash,
                            created_at=now,
                            expires_at=expires_at,
                        )
                    )
                    await uow.commit()
            except IntegrityError as exc:
                if _is_public_id_collision(exc):
                    continue
                raise
            return CreatedApiKeyDTO(
                public_id=created.public_id,
                name=created.name,
                created_by_username=created.created_by_username,
                created_at=created.created_at,
                expires_at=created.expires_at,
                last_used_at=created.last_used_at,
                revoked_at=created.revoked_at,
                key=_build_token(public_id, secret),
            )

        raise RuntimeError("Failed to generate unique API key identifier.")


class ListApiKeysUseCase:
    def __init__(self, repository: AuthApiKeyRepositoryPort):
        self.repository = repository

    async def execute(self) -> list[ApiKeyDTO]:
        records = await self.repository.list_all()
        return [_to_api_key_dto(record) for record in records]


class RevokeApiKeyUseCase:
    def __init__(self, uow_factory: AuthApiKeyUnitOfWorkFactory):
        self.uow_factory = uow_factory

    async def execute(self, command: RevokeApiKeyCommand) -> ApiKeyDTO:
        revoked_at = datetime.now(tz=timezone.utc)
        async with self.uow_factory() as uow:
            record = await uow.repository.revoke_by_public_id(
                command.public_id,
                revoked_at=revoked_at,
            )
            if record is None:
                raise ApiKeyNotFound()
            await uow.commit()
        return _to_api_key_dto(record)


class DeleteApiKeyUseCase:
    def __init__(self, uow_factory: AuthApiKeyUnitOfWorkFactory):
        self.uow_factory = uow_factory

    async def execute(self, command: DeleteApiKeyCommand) -> None:
        async with self.uow_factory() as uow:
            deleted = await uow.repository.delete_by_public_id(command.public_id)
            if not deleted:
                raise ApiKeyNotFound()
            await uow.commit()


class VerifyApiKeyUseCase:
    def __init__(self, uow_factory: AuthApiKeyUnitOfWorkFactory):
        self.uow_factory = uow_factory

    async def execute(self, query: VerifyApiKeyQuery) -> str:
        public_id, secret = parse_api_key_token(query.api_key)
        expected_hash = _hash_key_material(public_id, secret)

        now = datetime.now(tz=timezone.utc)
        async with self.uow_factory() as uow:
            record = await uow.repository.get_by_public_id(public_id)
            if record is None:
                raise ApiKeyInvalid()

            if record.revoked_at is not None:
                raise ApiKeyInvalid()

            expires_at = _normalize_datetime(record.expires_at)
            if expires_at is not None and expires_at <= now:
                raise ApiKeyInvalid()

            if not secrets.compare_digest(record.key_hash, expected_hash):
                raise ApiKeyInvalid()

            touched = await uow.repository.touch_last_used_at(public_id, used_at=now)
            if touched is None:
                raise ApiKeyInvalid()

            await uow.commit()
            return touched.created_by_username


__all__ = [
    "API_KEY_NAME_MAX_LENGTH",
    "API_KEY_PREFIX",
    "CreateApiKeyUseCase",
    "DeleteApiKeyUseCase",
    "ListApiKeysUseCase",
    "RevokeApiKeyUseCase",
    "VerifyApiKeyUseCase",
    "_is_public_id_collision",
    "parse_api_key_token",
]
