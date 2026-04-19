from argon2 import PasswordHasher

from app.application.auth.models import AuthSessionDTO, PasswordLoginCommand
from app.application.auth.ports import UserReadRepositoryPort
from app.application.auth.use_cases.session import CreateSessionUseCase
from app.domain.auth.errors import LoginInvalid


class PasswordLoginUseCase:
    def __init__(
        self,
        user_repository: UserReadRepositoryPort,
        create_session_use_case: CreateSessionUseCase,
        password_hasher: PasswordHasher | None = None,
    ):
        self.user_repository = user_repository
        self.create_session_use_case = create_session_use_case
        self.password_hasher = password_hasher or PasswordHasher()

    async def execute(self, command: PasswordLoginCommand) -> AuthSessionDTO:
        user = await self.user_repository.get_by_username(command.username)
        if user is None or user.disabled_at is not None:
            raise LoginInvalid()

        try:
            self.password_hasher.verify(
                hash=user.password_hash,
                password=command.password,
            )
        except Exception as exc:  # pragma: no cover - argon2 exception tree is broad
            raise LoginInvalid() from exc

        return await self.create_session_use_case.execute(
            user_id=user.id,
            username=user.username,
        )
