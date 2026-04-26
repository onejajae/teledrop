import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


@dataclass(slots=True, frozen=True)
class DropPasswordCredential:
    password: str | None = None
    grant_token: str | None = None

    @property
    def has_material(self) -> bool:
        return bool(self.password or self.grant_token)


class DropPasswordGrantService:
    _VERSION = "v2"
    _PURPOSE = "drop-grant"

    def __init__(
        self,
        secret_key: str,
        ttl_seconds: int,
        now_fn: Callable[[], datetime] | None = None,
    ):
        self._secret_key = secret_key.encode("utf-8")
        self._ttl_seconds = ttl_seconds
        self._now_fn = now_fn or _utc_now

    def issue(self, slug: str, password_hash: str | None) -> str | None:
        normalized_password_hash = _normalize_drop_password_hash(password_hash)
        if normalized_password_hash is None:
            return None

        expires_at = int(_normalize_datetime(self._now_fn()).timestamp()) + self._ttl_seconds
        signature = self._sign(slug, normalized_password_hash, expires_at)
        return f"{self._VERSION}.{expires_at}.{signature}"

    def verify(self, slug: str, expected_password_hash: str | None, grant_token: str | None) -> bool:
        normalized_expected = _normalize_drop_password_hash(expected_password_hash)
        if normalized_expected is None or not grant_token:
            return False

        parts = grant_token.split(".")
        if len(parts) != 3:
            return False

        version, expires_at_raw, provided_signature = parts
        if version != self._VERSION:
            return False

        try:
            expires_at = int(expires_at_raw)
        except ValueError:
            return False

        if expires_at <= int(_normalize_datetime(self._now_fn()).timestamp()):
            return False

        expected_signature = self._sign(slug, normalized_expected, expires_at)
        return secrets.compare_digest(expected_signature, provided_signature)

    def _sign(self, slug: str, normalized_password_hash: str, expires_at: int) -> str:
        message = (
            f"{self._PURPOSE}:{slug}:{normalized_password_hash}:{expires_at}"
        ).encode("utf-8")
        digest = hmac.new(self._secret_key, message, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _normalize_drop_password_hash(password_hash: str | None) -> str | None:
    if password_hash is None:
        return None
    stripped = password_hash.strip()
    return stripped or None


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
