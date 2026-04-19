import secrets

from app.domain.drop.entities import DropEntity
from app.domain.drop.errors import DropAccessDeniedError, DropPasswordInvalidError
from app.domain.drop.grants import DropPasswordCredential, DropPasswordGrantService
from app.domain.drop.value_objects import AccessScope


class RequestAuthContext:
    def __init__(self, user_id: str | None, username: str | None = None):
        self.user_id = user_id
        self.username = username


def normalize_drop_password(password: str | None) -> str | None:
    if password is None:
        return None
    stripped = password.strip()
    return stripped or None


def assert_drop_access_allowed(drop: DropEntity, auth: RequestAuthContext | None):
    if drop.access_scope == AccessScope.PRIVATE and not is_drop_owner(drop, auth):
        raise DropAccessDeniedError()


def is_drop_owner(drop: DropEntity, auth: RequestAuthContext | None) -> bool:
    return auth is not None and auth.user_id is not None and auth.user_id == drop.owner_user_id


def assert_drop_owner(drop: DropEntity, auth: RequestAuthContext | None):
    if not is_drop_owner(drop, auth):
        raise DropAccessDeniedError()


def assert_drop_password_matches(
    drop: DropEntity,
    credential: DropPasswordCredential | None,
    grant_service: DropPasswordGrantService,
):
    expected = normalize_drop_password(drop.drop_password)
    if expected is None:
        return

    if credential is None:
        raise DropPasswordInvalidError()

    provided = normalize_drop_password(credential.password)
    if provided is not None and secrets.compare_digest(expected, provided):
        return

    if grant_service.verify(drop.slug, expected, credential.grant_token):
        return

    raise DropPasswordInvalidError()
