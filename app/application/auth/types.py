from dataclasses import dataclass


@dataclass(slots=True)
class AuthIdentity:
    username: str | None
