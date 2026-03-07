import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from argon2 import PasswordHasher
from sqlalchemy.exc import IntegrityError

from app.application.auth.models import (
    CreateApiKeyCommand,
    DeleteApiKeyCommand,
    PasswordLoginCommand,
    RevokeApiKeyCommand,
    VerifyApiKeyQuery,
    VerifySessionQuery,
)
from app.application.auth.ports import (
    AuthApiKeyCreateInput,
    AuthApiKeyRecord,
    AuthSessionCreateInput,
    AuthSessionRecord,
)
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.auth.use_cases.api_key import (
    API_KEY_PREFIX,
    CreateApiKeyUseCase,
    DeleteApiKeyUseCase,
    ListApiKeysUseCase,
    RevokeApiKeyUseCase,
    VerifyApiKeyUseCase,
    parse_api_key_token,
)
from app.application.auth.use_cases.password_login import PasswordLoginUseCase
from app.application.auth.use_cases.session import CreateSessionUseCase, VerifySessionUseCase
from app.core.config import Settings
from app.domain.auth.errors import ApiKeyInvalid, LoginInvalid, SessionExpired


class _InMemorySessionRepository:
    def __init__(self):
        self.records: dict[str, AuthSessionRecord] = {}
        self.revoked_calls: list[str] = []

    async def create(self, data: AuthSessionCreateInput) -> AuthSessionRecord:
        record = AuthSessionRecord(
            sid=data.sid,
            username=data.username,
            created_at=data.created_at,
            expires_at=data.expires_at,
            revoked_at=None,
        )
        self.records[data.sid] = record
        return record

    async def get_by_sid(self, sid: str) -> AuthSessionRecord | None:
        return self.records.get(sid)

    async def revoke_by_sid(self, sid: str) -> AuthSessionRecord | None:
        self.revoked_calls.append(sid)
        record = self.records.get(sid)
        if record is None:
            return None
        record.revoked_at = datetime.now(timezone.utc)
        return record


class _TrackingAuthUow:
    def __init__(self, repository: _InMemorySessionRepository):
        self.repository = repository
        self.entered = False
        self.exited = False
        self.commit_calls = 0

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True
        return None

    async def commit(self):
        self.commit_calls += 1

    async def rollback(self):
        return None


class _InMemoryApiKeyRepository:
    def __init__(self):
        self.records: dict[str, AuthApiKeyRecord] = {}
        self.touch_calls: list[tuple[str, datetime]] = []

    async def create(self, data: AuthApiKeyCreateInput) -> AuthApiKeyRecord:
        record = AuthApiKeyRecord(
            public_id=data.public_id,
            name=data.name,
            created_by_username=data.created_by_username,
            key_hash=data.key_hash,
            created_at=data.created_at,
            expires_at=data.expires_at,
            last_used_at=None,
            revoked_at=None,
        )
        self.records[data.public_id] = record
        return record

    async def list_all(self) -> list[AuthApiKeyRecord]:
        return list(self.records.values())

    async def get_by_public_id(self, public_id: str) -> AuthApiKeyRecord | None:
        return self.records.get(public_id)

    async def touch_last_used_at(
        self,
        public_id: str,
        used_at: datetime,
    ) -> AuthApiKeyRecord | None:
        self.touch_calls.append((public_id, used_at))
        record = self.records.get(public_id)
        if record is None:
            return None
        record.last_used_at = used_at
        return record

    async def revoke_by_public_id(
        self,
        public_id: str,
        revoked_at: datetime,
    ) -> AuthApiKeyRecord | None:
        record = self.records.get(public_id)
        if record is None:
            return None
        record.revoked_at = revoked_at
        return record

    async def delete_by_public_id(self, public_id: str) -> bool:
        return self.records.pop(public_id, None) is not None


class _TrackingApiKeyUow:
    def __init__(self, repository: _InMemoryApiKeyRepository):
        self.repository = repository
        self.entered = False
        self.exited = False
        self.commit_calls = 0

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True
        return None

    async def commit(self):
        self.commit_calls += 1

    async def rollback(self):
        return None


class _TransactionalApiKeyRepository:
    def __init__(self, records: dict[str, AuthApiKeyRecord]):
        self._records = records
        self._pending_create: AuthApiKeyRecord | None = None

    async def create(self, data: AuthApiKeyCreateInput) -> AuthApiKeyRecord:
        record = AuthApiKeyRecord(
            public_id=data.public_id,
            name=data.name,
            created_by_username=data.created_by_username,
            key_hash=data.key_hash,
            created_at=data.created_at,
            expires_at=data.expires_at,
            last_used_at=None,
            revoked_at=None,
        )
        self._pending_create = record
        return record

    async def get_by_public_id(self, public_id: str) -> AuthApiKeyRecord | None:
        return self._records.get(public_id)

    def commit_pending(self) -> None:
        if self._pending_create is not None:
            self._records[self._pending_create.public_id] = self._pending_create
            self._pending_create = None

    def rollback_pending(self) -> None:
        self._pending_create = None


class _CommitCollisionApiKeyUow:
    def __init__(self, records: dict[str, AuthApiKeyRecord], *, fail_commit: bool):
        self.repository = _TransactionalApiKeyRepository(records)
        self.fail_commit = fail_commit
        self.entered = False
        self.exited = False
        self.commit_calls = 0

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True
        if exc_type is not None:
            self.repository.rollback_pending()
        return None

    async def commit(self):
        self.commit_calls += 1
        if self.fail_commit:
            self.repository.rollback_pending()
            raise IntegrityError(
                "INSERT INTO auth_api_keys ...",
                {},
                sqlite3.IntegrityError(
                    "UNIQUE constraint failed: auth_api_keys.public_id"
                ),
            )
        self.repository.commit_pending()

    async def rollback(self):
        self.repository.rollback_pending()


class _CommitCollisionApiKeyUowFactory:
    def __init__(self, collisions_before_success: int = 1):
        self.records: dict[str, AuthApiKeyRecord] = {}
        self.collisions_remaining = collisions_before_success
        self.instances: list[_CommitCollisionApiKeyUow] = []

    def __call__(self):
        fail_commit = self.collisions_remaining > 0
        if fail_commit:
            self.collisions_remaining -= 1
        uow = _CommitCollisionApiKeyUow(self.records, fail_commit=fail_commit)
        self.instances.append(uow)
        return uow


def _session_uow_factory(repository: _InMemorySessionRepository):
    return lambda: _TrackingAuthUow(repository)


def _api_key_uow_factory(repository: _InMemoryApiKeyRepository):
    return lambda: _TrackingApiKeyUow(repository)


def _settings(**overrides) -> Settings:
    base = {
        "WEB_USERNAME": "admin",
        "WEB_PASSWORD": PasswordHasher().hash("password"),
        "SESSION_TTL_SECONDS": 3600,
        "CSRF_SECRET_KEY": "test-csrf-secret",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)


class TestAuthUseCase:
    async def test_password_login_creates_session(self):
        settings = _settings()
        session_repo = _InMemorySessionRepository()
        create_session = CreateSessionUseCase(
            session_ttl_seconds=settings.SESSION_TTL_SECONDS,
            uow_factory=_session_uow_factory(session_repo),
        )
        use_case = PasswordLoginUseCase(
            web_username=settings.WEB_USERNAME,
            web_password_hash=settings.WEB_PASSWORD,
            create_session_use_case=create_session,
        )

        session = await use_case.execute(
            PasswordLoginCommand(username="admin", password="password")
        )

        assert session.username == "admin"
        assert session.sid
        assert session.sid in session_repo.records

    async def test_password_login_invalid_raises(self):
        settings = _settings()
        session_repo = _InMemorySessionRepository()
        create_session = CreateSessionUseCase(
            session_ttl_seconds=settings.SESSION_TTL_SECONDS,
            uow_factory=_session_uow_factory(session_repo),
        )
        use_case = PasswordLoginUseCase(
            web_username=settings.WEB_USERNAME,
            web_password_hash=settings.WEB_PASSWORD,
            create_session_use_case=create_session,
        )

        with pytest.raises(LoginInvalid):
            await use_case.execute(PasswordLoginCommand(username="admin", password="wrong"))

    async def test_verify_session_expired_uses_uow_transaction_boundary(self):
        repo = _InMemorySessionRepository()
        repo.records["sid-1"] = AuthSessionRecord(
            sid="sid-1",
            username="tester",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            revoked_at=None,
        )
        tracking_uow = _TrackingAuthUow(repo)
        use_case = VerifySessionUseCase(uow_factory=lambda: tracking_uow)

        with pytest.raises(SessionExpired):
            await use_case.execute(VerifySessionQuery(sid="sid-1"))

        assert tracking_uow.entered
        assert tracking_uow.exited
        assert tracking_uow.commit_calls == 1
        assert repo.revoked_calls == ["sid-1"]

    def test_csrf_token_service_is_deterministic_and_validates(self):
        service = CsrfTokenService("csrf-secret-a")
        other_service = CsrfTokenService("csrf-secret-b")

        token = service.generate("session-1")

        assert token == service.generate("session-1")
        assert token != other_service.generate("session-1")
        assert service.verify("session-1", token)
        assert not service.verify("session-1", None)
        assert not service.verify("session-2", token)

    def test_settings_validation_rules(self):
        settings = _settings(SESSION_TTL_SECONDS=0)
        with pytest.raises(ValueError):
            settings.validate_auth_configuration()

        settings = _settings(SESSION_COOKIE_SAMESITE="none", SESSION_COOKIE_SECURE=False)
        with pytest.raises(ValueError):
            settings.validate_auth_configuration()

        settings = _settings(
            WEB_USERNAME="custom",
            WEB_PASSWORD=PasswordHasher().hash("strong-password"),
        )
        assert settings.validate_auth_configuration() is None
        assert settings.SESSION_COOKIE_SECURE is True

        settings = _settings(
            SESSION_COOKIE_SECURE=True,
            WEB_USERNAME="admin",
        )
        assert settings.validate_auth_configuration() is None

        settings = _settings(
            SESSION_COOKIE_SECURE=True,
            WEB_USERNAME="custom",
            WEB_PASSWORD=PasswordHasher().hash("strong-password"),
            CSRF_SECRET_KEY="safe-csrf-secret",
        )
        assert settings.validate_auth_configuration() is None

        settings = _settings(CSRF_SECRET_KEY="")
        with pytest.raises(ValueError):
            settings.validate_auth_configuration()

    async def test_create_api_key_list_and_verify_flow(self):
        repo = _InMemoryApiKeyRepository()
        create_use_case = CreateApiKeyUseCase(uow_factory=_api_key_uow_factory(repo))

        created = await create_use_case.execute(
            CreateApiKeyCommand(
                name="shortcuts",
                created_by_username="admin",
                expires_at=None,
            )
        )
        assert created.key.startswith(f"{API_KEY_PREFIX}_")

        listed = await ListApiKeysUseCase(repository=repo).execute()
        assert len(listed) == 1
        assert listed[0].public_id == created.public_id

        verify_use_case = VerifyApiKeyUseCase(uow_factory=lambda: _TrackingApiKeyUow(repo))
        username = await verify_use_case.execute(VerifyApiKeyQuery(api_key=created.key))
        assert username == "admin"

    async def test_verify_api_key_updates_last_used_and_commits_once(self):
        repo = _InMemoryApiKeyRepository()
        create_use_case = CreateApiKeyUseCase(uow_factory=_api_key_uow_factory(repo))
        created = await create_use_case.execute(
            CreateApiKeyCommand(
                name="mobile",
                created_by_username="admin",
                expires_at=None,
            )
        )
        tracking_uow = _TrackingApiKeyUow(repo)
        use_case = VerifyApiKeyUseCase(uow_factory=lambda: tracking_uow)

        username = await use_case.execute(VerifyApiKeyQuery(api_key=created.key))

        assert username == "admin"
        assert tracking_uow.entered
        assert tracking_uow.exited
        assert tracking_uow.commit_calls == 1
        assert repo.touch_calls

    async def test_verify_api_key_rejects_revoked_or_malformed(self):
        repo = _InMemoryApiKeyRepository()
        create_use_case = CreateApiKeyUseCase(uow_factory=_api_key_uow_factory(repo))
        created = await create_use_case.execute(
            CreateApiKeyCommand(
                name="revoked",
                created_by_username="admin",
                expires_at=None,
            )
        )
        record = repo.records[created.public_id]
        record.revoked_at = datetime.now(timezone.utc)

        use_case = VerifyApiKeyUseCase(uow_factory=lambda: _TrackingApiKeyUow(repo))
        with pytest.raises(ApiKeyInvalid):
            await use_case.execute(VerifyApiKeyQuery(api_key=created.key))

        with pytest.raises(ApiKeyInvalid):
            await use_case.execute(VerifyApiKeyQuery(api_key="bad-token"))

    async def test_revoke_and_delete_api_key_use_cases(self):
        repo = _InMemoryApiKeyRepository()
        create_use_case = CreateApiKeyUseCase(uow_factory=_api_key_uow_factory(repo))
        created = await create_use_case.execute(
            CreateApiKeyCommand(
                name="to-remove",
                created_by_username="admin",
                expires_at=None,
            )
        )
        revoke_uow = _TrackingApiKeyUow(repo)
        delete_uow = _TrackingApiKeyUow(repo)

        revoked = await RevokeApiKeyUseCase(uow_factory=lambda: revoke_uow).execute(
            RevokeApiKeyCommand(public_id=created.public_id)
        )
        assert revoked.revoked_at is not None
        assert revoke_uow.commit_calls == 1

        await DeleteApiKeyUseCase(uow_factory=lambda: delete_uow).execute(
            DeleteApiKeyCommand(public_id=created.public_id)
        )
        assert delete_uow.commit_calls == 1
        assert created.public_id not in repo.records

    async def test_create_api_key_retries_commit_time_public_id_collision(self):
        uow_factory = _CommitCollisionApiKeyUowFactory(collisions_before_success=1)
        create_use_case = CreateApiKeyUseCase(uow_factory=uow_factory)

        created = await create_use_case.execute(
            CreateApiKeyCommand(
                name="retry-me",
                created_by_username="admin",
                expires_at=None,
            )
        )

        assert created.key.startswith(f"{API_KEY_PREFIX}_")
        assert len(uow_factory.instances) == 2
        assert uow_factory.instances[0].commit_calls == 1
        assert uow_factory.instances[1].commit_calls == 1
        assert len(uow_factory.records) == 1

    def test_parse_api_key_token_rejects_invalid_shapes(self):
        with pytest.raises(ApiKeyInvalid):
            parse_api_key_token("tdpk_onlyprefix")
        with pytest.raises(ApiKeyInvalid):
            parse_api_key_token("wrong_x_y")
