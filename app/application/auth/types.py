from dataclasses import dataclass


@dataclass(slots=True)
class AuthIdentity:
    user_id: str | None = None
    username: str | None = None

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None
