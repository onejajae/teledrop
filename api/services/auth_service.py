import jwt
from argon2 import PasswordHasher
from typing import Literal
from datetime import datetime, timedelta, timezone

from api.config import Settings

from api.models import AccessToken, TokenPayload

from api.exceptions import TokenExpired, TokenInvalid, LoginInvalid


class AuthService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.ph = PasswordHasher()

    def authenticate(self, username: str, password: str) -> Literal[True]:
        if username != self.settings.WEB_USERNAME:
            raise LoginInvalid

        try:
            result = self.ph.verify(hash=self.settings.WEB_PASSWORD, password=password)
        except:
            raise LoginInvalid

        return result

    def create_token(self, payload=TokenPayload):
        payload.exp = datetime.now(tz=timezone.utc) + timedelta(
            minutes=self.settings.JWT_EXP_MINUTES
        )

        return AccessToken(
            access_token=jwt.encode(
                payload.model_dump(),
                key=self.settings.JWT_SECRET,
                algorithm=self.settings.JWT_ALGORITHM,
            ),
            exp=payload.exp,
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
            raise TokenExpired()
        except Exception as e:
            raise TokenInvalid()
