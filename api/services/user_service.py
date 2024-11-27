import jwt
from bcrypt import hashpw, gensalt, checkpw
from datetime import datetime, timedelta, timezone

from api.config import Settings
from api.repositories.user_repository import UserRepositoryInterface

from api.schemas.user.service import (
    TokenPayload,
    AccessToken,
    UserServiceCreate,
    UserServiceRead,
)
from api.schemas.user.repository import UserRepositoryCreate, UserRepositoryRead
from api.exceptions.user_exceptions import *


class UserService:
    def __init__(self, user_repository: UserRepositoryInterface, settings: Settings):
        self.user_repository = user_repository
        self.settings = settings

    def create_token(self, payload=TokenPayload):
        payload.exp = datetime.now(tz=timezone.utc) + timedelta(
            minutes=self.settings.JWT_EXP_MINUTES
        )

        return AccessToken(
            token=jwt.encode(
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

    def create(self, user_data: UserServiceCreate) -> UserServiceRead:
        if not self.settings.ALLOW_REGISTER:
            raise RegisterNotAllowedError()

        if (
            self.settings.REGISTER_CODE is not None
            and self.settings.REGISTER_CODE != user_data.register_code
        ):
            raise RegisterCodeNotMatchedError()

        hashed_password = hashpw(user_data.password.encode("utf-8"), gensalt())
        hashed_password = hashed_password.decode("utf-8")

        return self.user_repository.create(
            UserRepositoryCreate(
                username=user_data.username,
                password=hashed_password,
                created_at=datetime.now(timezone.utc),
            )
        )

    def authenticate(self, username: str, password: str) -> UserServiceRead:
        user = self.user_repository.get_by_filter(filter_params={"username": username})
        if user is None:
            raise UserNotFoundError()

        if not checkpw(password.encode("utf-8"), user.password.encode("utf-8")):
            raise PasswordInvlaidError()

        return user

    def get_by_id(self, id: int) -> UserServiceRead:
        return self.user_repository.get_by_id(id)

    def get_by_username(self, username: str) -> UserServiceRead:
        return self.user_repository.get_by_filter(filter_params={"username": username})
