import jwt
from datetime import datetime, timedelta, timezone

from api.config import Settings

from api.models import AccessToken, TokenPayload

from api.exceptions import TokenExpiredError, TokenInvalidError


class AuthService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def authenticate(self, username: str, password: str) -> bool:
        if username != self.settings.WEB_USERNAME:
            return False

        if password != self.settings.WEB_PASSWORD:
            return False

        return True

    def create_token(self, payload=TokenPayload):
        payload.exp = datetime.now(tz=timezone.utc) + timedelta(
            minutes=self.settings.JWT_EXP_MINUTES
        )

        return AccessToken(
            access_token=jwt.encode(
                payload.model_dump(),
                key=self.settings.JWT_SECRET,
                algorithm=self.settings.JWT_ALGORITHM,
            )
        )

    def verify_token(self, token: str) -> TokenPayload:
        try:
            payload = jwt.decode(
                token,
                key=self.settings.JWT_SECRET,
                algorithms=self.settings.JWT_ALGORITHM,
            )
            return TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except Exception as e:
            raise TokenInvalidError()
