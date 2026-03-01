import secrets

from app.domain.drop.entities import DropEntity
from app.domain.drop.errors import DropAccessDeniedError, DropPasswordInvalidError
from app.domain.drop.value_objects import AccessScope


class RequestAuthContext:
    def __init__(self, username: str | None):
        self.username = username


def normalize_drop_password(password: str | None) -> str | None:
    if password is None:
        return None
    stripped = password.strip()
    return stripped or None


def assert_drop_access_allowed(drop: DropEntity, auth: RequestAuthContext | None):
    if drop.access_scope == AccessScope.PRIVATE and (auth is None or auth.username is None):
        raise DropAccessDeniedError()


def assert_drop_password_matches(drop: DropEntity, password: str | None):
    expected = normalize_drop_password(drop.drop_password)
    provided = normalize_drop_password(password)
    if expected is None and provided is None:
        return
    if expected is None or provided is None:
        raise DropPasswordInvalidError()
    if not secrets.compare_digest(expected, provided):
        raise DropPasswordInvalidError()
