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


@dataclass(slots=True)
class CreateApiKeyCommand:
    name: str
    created_by_username: str
    expires_at: datetime | None


@dataclass(slots=True)
class RevokeApiKeyCommand:
    public_id: str


@dataclass(slots=True)
class DeleteApiKeyCommand:
    public_id: str


@dataclass(slots=True)
class VerifyApiKeyQuery:
    api_key: str


@dataclass(slots=True)
class ApiKeyDTO:
    public_id: str
    name: str
    created_by_username: str
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None


@dataclass(slots=True)
class CreatedApiKeyDTO(ApiKeyDTO):
    key: str


__all__ = [
    "ApiKeyDTO",
    "AuthSessionDTO",
    "CreateApiKeyCommand",
    "CreatedApiKeyDTO",
    "DeleteApiKeyCommand",
    "PasswordLoginCommand",
    "RevokeApiKeyCommand",
    "VerifyApiKeyQuery",
    "VerifySessionQuery",
]
