import base64
import hmac
import secrets


class CsrfTokenService:
    def __init__(self, secret_key: str):
        if not secret_key:
            raise ValueError("CSRF secret key must not be empty.")
        self._secret_key = secret_key.encode("utf-8")

    def generate(self, session_id: str) -> str:
        digest = hmac.digest(self._secret_key, session_id.encode("utf-8"), "sha256")
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    def verify(self, session_id: str, csrf_token: str | None) -> bool:
        if not csrf_token:
            return False
        expected = self.generate(session_id)
        return secrets.compare_digest(expected, csrf_token)
