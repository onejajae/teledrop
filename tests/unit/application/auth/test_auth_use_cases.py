from datetime import datetime, timedelta, timezone

import pytest
from argon2 import PasswordHasher

from app.application.auth.models import PasswordLoginCommand, VerifySessionQuery
from app.application.auth.ports import AuthSessionCreateInput, AuthSessionRecord
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.auth.use_cases.password_login import PasswordLoginUseCase
from app.application.auth.use_cases.session import CreateSessionUseCase, VerifySessionUseCase
from app.core.config import Settings
from app.domain.auth.errors import LoginInvalid, SessionExpired


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


def _settings(**overrides) -> Settings:
    base = {
        "APP_MODE": "test",
        "WEB_USERNAME": "admin",
        "WEB_PASSWORD": PasswordHasher().hash("password"),
        "SESSION_TTL_SECONDS": 3600,
        "CSRF_SECRET_KEY": "test-csrf-secret",
    }
    base.update(overrides)
    return Settings(**base)


class TestAuthUseCase:
    async def test_password_login_creates_session(self):
        settings = _settings()
        session_repo = _InMemorySessionRepository()
        create_session = CreateSessionUseCase(
            session_ttl_seconds=settings.SESSION_TTL_SECONDS,
            repository=session_repo,
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
            repository=session_repo,
        )
        use_case = PasswordLoginUseCase(
            web_username=settings.WEB_USERNAME,
            web_password_hash=settings.WEB_PASSWORD,
            create_session_use_case=create_session,
        )

        with pytest.raises(LoginInvalid):
            await use_case.execute(PasswordLoginCommand(username="admin", password="wrong"))

    async def test_verify_session_expired_revokes_and_raises(self):
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

        assert repo.revoked_calls == ["sid-1"]

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

        settings = _settings(APP_MODE="prod", SESSION_COOKIE_SECURE=False)
        with pytest.raises(ValueError):
            settings.validate_auth_configuration()

        settings = _settings(
            APP_MODE="prod",
            SESSION_COOKIE_SECURE=True,
            WEB_USERNAME="admin",
        )
        with pytest.raises(ValueError):
            settings.validate_auth_configuration()

        settings = _settings(
            APP_MODE="prod",
            SESSION_COOKIE_SECURE=True,
            WEB_USERNAME="custom",
            WEB_PASSWORD=PasswordHasher().hash("strong-password"),
            CSRF_SECRET_KEY="prod-csrf-secret",
        )
        assert settings.validate_auth_configuration() is None

        settings = _settings(
            APP_MODE="prod",
            SESSION_COOKIE_SECURE=True,
            WEB_USERNAME="custom",
            WEB_PASSWORD=PasswordHasher().hash("strong-password"),
            CSRF_SECRET_KEY="dev-csrf-secret",
        )
        with pytest.raises(ValueError):
            settings.validate_auth_configuration()
