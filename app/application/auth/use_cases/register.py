import re
from datetime import datetime, timezone

from argon2 import PasswordHasher
from sqlalchemy.exc import IntegrityError

from app.application.auth.models import AuthSessionDTO, RegisterUserCommand
from app.application.auth.ports import UserCreateInput, UserUnitOfWorkFactory
from app.application.auth.use_cases.session import CreateSessionUseCase
from app.domain.auth.errors import (
    PasswordConfirmationMismatch,
    PasswordTooShort,
    RegistrationDisabled,
    UsernameInvalid,
    UsernameUnavailable,
)


USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
PASSWORD_MIN_LENGTH = 8


def _is_username_collision(exc: IntegrityError) -> bool:
    constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if isinstance(constraint_name, str) and "username" in constraint_name.lower():
        return True

    message = str(exc.orig).lower()
    return "unique" in message and "username" in message


class RegisterUserUseCase:
    def __init__(
        self,
        uow_factory: UserUnitOfWorkFactory,
        create_session_use_case: CreateSessionUseCase,
        *,
        registration_enabled: bool,
        password_hasher: PasswordHasher | None = None,
    ):
        self.uow_factory = uow_factory
        self.create_session_use_case = create_session_use_case
        self.registration_enabled = registration_enabled
        self.password_hasher = password_hasher or PasswordHasher()

    async def execute(self, command: RegisterUserCommand) -> AuthSessionDTO:
        if not self.registration_enabled:
            raise RegistrationDisabled()

        username = (command.username or "").strip()
        password = command.password or ""
        confirm_password = command.confirm_password or ""

        if USERNAME_PATTERN.fullmatch(username) is None:
            raise UsernameInvalid()

        if len(password) < PASSWORD_MIN_LENGTH:
            raise PasswordTooShort()

        if password != confirm_password:
            raise PasswordConfirmationMismatch()

        now = datetime.now(timezone.utc)
        try:
            async with self.uow_factory() as uow:
                existing = await uow.repository.get_by_username(username)
                if existing is not None:
                    raise UsernameUnavailable()

                created = await uow.repository.create(
                    UserCreateInput(
                        username=username,
                        password_hash=self.password_hasher.hash(password),
                        created_at=now,
                        updated_at=now,
                        disabled_at=None,
                    )
                )
                await uow.commit()
        except IntegrityError as exc:
            if _is_username_collision(exc):
                raise UsernameUnavailable() from exc
            raise

        return await self.create_session_use_case.execute(
            user_id=created.id,
            username=created.username,
        )


__all__ = [
    "PASSWORD_MIN_LENGTH",
    "USERNAME_PATTERN",
    "RegisterUserUseCase",
]
