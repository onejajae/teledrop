from __future__ import annotations

from argon2 import PasswordHasher

from app.application.auth.models import AuthSessionDTO, PasswordLoginCommand
from app.application.auth.use_cases.session import CreateSessionUseCase
from app.domain.auth.errors import LoginInvalid


class PasswordLoginUseCase:
    def __init__(
        self,
        web_username: str,
        web_password_hash: str,
        create_session_use_case: CreateSessionUseCase,
        password_hasher: PasswordHasher | None = None,
    ):
        self.web_username = web_username
        self.web_password_hash = web_password_hash
        self.create_session_use_case = create_session_use_case
        self.password_hasher = password_hasher or PasswordHasher()

    async def execute(self, command: PasswordLoginCommand) -> AuthSessionDTO:
        if command.username != self.web_username:
            raise LoginInvalid()

        try:
            self.password_hasher.verify(
                hash=self.web_password_hash,
                password=command.password,
            )
        except Exception as exc:  # pragma: no cover - argon2 exception tree is broad
            raise LoginInvalid() from exc

        return await self.create_session_use_case.execute(command.username)
