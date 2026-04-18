import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from app.core.config import Settings


_TOKEN_VERSION = "v1"
_DEFAULT_TTL_SECONDS = 900


def _normalize_target_view(target_view: str) -> str:
    return "manage" if target_view == "manage" else "shared"


def _token_ttl_seconds(settings: Settings) -> int:
    return max(60, min(settings.SESSION_TTL_SECONDS, _DEFAULT_TTL_SECONDS))


def _sign_payload(settings: Settings, payload: str) -> str:
    digest = hmac.new(
        settings.CSRF_SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def issue_drop_unlock_token(settings: Settings, slug: str, target_view: str) -> str:
    expires_at = int(
        (datetime.now(tz=timezone.utc) + timedelta(seconds=_token_ttl_seconds(settings))).timestamp()
    )
    normalized_target_view = _normalize_target_view(target_view)
    payload = f"{_TOKEN_VERSION}:{slug}:{normalized_target_view}:{expires_at}"
    signature = _sign_payload(settings, payload)
    return f"{_TOKEN_VERSION}.{expires_at}.{signature}"


def verify_drop_unlock_token(
    settings: Settings,
    *,
    slug: str,
    target_view: str,
    token: str | None,
) -> bool:
    if not token:
        return False

    version, sep, remainder = token.partition(".")
    if not sep or version != _TOKEN_VERSION:
        return False

    expires_at_text, sep, signature = remainder.partition(".")
    if not sep or not expires_at_text or not signature:
        return False

    try:
        expires_at = int(expires_at_text)
    except ValueError:
        return False

    if datetime.now(tz=timezone.utc).timestamp() > expires_at:
        return False

    normalized_target_view = _normalize_target_view(target_view)
    payload = f"{_TOKEN_VERSION}:{slug}:{normalized_target_view}:{expires_at}"
    expected_signature = _sign_payload(settings, payload)
    return hmac.compare_digest(signature, expected_signature)


__all__ = [
    "issue_drop_unlock_token",
    "verify_drop_unlock_token",
]
