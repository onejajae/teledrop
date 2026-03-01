from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PasswordLoginCommand:
    username: str
    password: str


@dataclass(slots=True)
class VerifySessionQuery:
    sid: str


@dataclass(slots=True)
class AuthSessionDTO:
    sid: str
    username: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


__all__ = [
    "AuthSessionDTO",
    "PasswordLoginCommand",
    "VerifySessionQuery",
]
