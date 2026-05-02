from datetime import datetime, timedelta, timezone

from app.domain.drop.grants import DropPasswordGrantService


class TestDropPasswordGrantService:
    def test_issue_and_verify_accept_valid_unexpired_token(self):
        now = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)
        service = DropPasswordGrantService(
            secret_key="test-secret",
            ttl_seconds=60,
            now_fn=lambda: now,
        )

        token = service.issue("drop-1", "  secret  ")

        assert token is not None
        assert token.startswith("v2.")
        assert service.verify("drop-1", "secret", token) is True

    def test_verify_rejects_expired_token_server_side(self):
        issued_at = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)
        issuing_service = DropPasswordGrantService(
            secret_key="test-secret",
            ttl_seconds=60,
            now_fn=lambda: issued_at,
        )
        token = issuing_service.issue("drop-1", "secret")

        verifying_service = DropPasswordGrantService(
            secret_key="test-secret",
            ttl_seconds=60,
            now_fn=lambda: issued_at + timedelta(seconds=60),
        )

        assert verifying_service.verify("drop-1", "secret", token) is False

    def test_verify_rejects_wrong_version_and_malformed_tokens(self):
        now = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)
        service = DropPasswordGrantService(
            secret_key="test-secret",
            ttl_seconds=60,
            now_fn=lambda: now,
        )

        assert service.verify("drop-1", "secret", "v1.previous-signature") is False
        assert service.verify("drop-1", "secret", "v2.bad-expiry.signature") is False
        assert service.verify("drop-1", "secret", "not-a-token") is False

    def test_verify_rejects_wrong_slug_or_password(self):
        now = datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc)
        service = DropPasswordGrantService(
            secret_key="test-secret",
            ttl_seconds=60,
            now_fn=lambda: now,
        )
        token = service.issue("drop-1", "secret")

        assert service.verify("drop-2", "secret", token) is False
        assert service.verify("drop-1", "wrong", token) is False
