from datetime import datetime, timezone

import pytest

from app.domain.drop.entities import DropEntity
from app.domain.drop.errors import DropAccessDeniedError, DropPasswordInvalidError
from app.domain.drop.grants import DropPasswordCredential, DropPasswordGrantService
from app.domain.drop.policies import (
    RequestAuthContext,
    assert_drop_access_allowed,
    assert_drop_password_matches,
    normalize_drop_password,
)
from app.domain.drop.value_objects import AccessScope


def _drop(
    *,
    access_scope: AccessScope = AccessScope.PRIVATE,
    drop_password: str | None = None,
) -> DropEntity:
    return DropEntity(
        id="drop-1",
        slug="slug-1",
        access_scope=access_scope,
        is_favorite=False,
        drop_password=drop_password,
        file_name="file.txt",
        mime_type="text/plain",
        size_bytes=4,
        sha256="abcd",
        storage_key="storage-1",
        title="title",
        description="desc",
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )


def _credential(password: str | None) -> DropPasswordCredential | None:
    if password is None:
        return None
    return DropPasswordCredential(password=password)


class TestDropPolicies:
    _grant_service = DropPasswordGrantService(secret_key="test-secret", ttl_seconds=3600)

    @pytest.mark.parametrize(
        ("raw_password", "expected"),
        [
            (None, None),
            ("", None),
            ("   ", None),
            ("  pass  ", "pass"),
            ("pass", "pass"),
        ],
    )
    def test_normalize_drop_password(self, raw_password: str | None, expected: str | None):
        assert normalize_drop_password(raw_password) == expected

    def test_assert_drop_access_allowed_for_private_drop_and_anonymous(self):
        with pytest.raises(DropAccessDeniedError):
            assert_drop_access_allowed(_drop(access_scope=AccessScope.PRIVATE), None)

        with pytest.raises(DropAccessDeniedError):
            assert_drop_access_allowed(
                _drop(access_scope=AccessScope.PRIVATE),
                RequestAuthContext(username=None),
            )

    def test_assert_drop_access_allowed_permits_public_and_authenticated_access(self):
        assert_drop_access_allowed(_drop(access_scope=AccessScope.PUBLIC), None)
        assert_drop_access_allowed(
            _drop(access_scope=AccessScope.PRIVATE),
            RequestAuthContext(username="tester"),
        )

    def test_assert_drop_password_matches_accepts_none_pair_and_trimmed_match(self):
        assert_drop_password_matches(
            _drop(drop_password=None),
            None,
            self._grant_service,
        )
        assert_drop_password_matches(
            _drop(drop_password="  secret  "),
            _credential("secret"),
            self._grant_service,
        )

    @pytest.mark.parametrize(
        ("expected", "provided"),
        [
            ("secret", None),
            ("secret", "wrong"),
        ],
    )
    def test_assert_drop_password_matches_rejects_mismatch(
        self,
        expected: str | None,
        provided: str | None,
    ):
        with pytest.raises(DropPasswordInvalidError):
            assert_drop_password_matches(
                _drop(drop_password=expected),
                _credential(provided),
                self._grant_service,
            )

    def test_assert_drop_password_matches_ignores_credential_when_password_not_required(self):
        assert_drop_password_matches(
            _drop(drop_password=None),
            _credential("secret"),
            self._grant_service,
        )
