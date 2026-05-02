from datetime import datetime, timezone

import pytest

from app.domain.drop.entities import DropEntity
from app.domain.drop.errors import DropAccessDeniedError, DropPasswordInvalidError
from app.domain.drop.grants import DropPasswordCredential, DropPasswordGrantService
from app.domain.drop.policies import (
    RequestAuthContext,
    assert_drop_access_allowed,
    assert_drop_owner,
    is_drop_owner,
    assert_drop_password_matches,
    hash_drop_password,
    normalize_drop_password,
    verify_drop_password_hash,
)
from app.domain.drop.value_objects import AccessScope


def _drop(
    *,
    owner_user_id: str = "user-1",
    access_scope: AccessScope = AccessScope.PRIVATE,
    drop_password: str | None = None,
) -> DropEntity:
    return DropEntity(
        id="drop-1",
        owner_user_id=owner_user_id,
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
                RequestAuthContext(user_id=None, username=None),
            )

    def test_assert_drop_access_allowed_permits_public_and_owner_access(self):
        assert_drop_access_allowed(_drop(access_scope=AccessScope.PUBLIC), None)
        assert_drop_access_allowed(
            _drop(access_scope=AccessScope.PRIVATE),
            RequestAuthContext(user_id="user-1", username="tester"),
        )

    def test_assert_drop_access_allowed_rejects_private_non_owner(self):
        with pytest.raises(DropAccessDeniedError):
            assert_drop_access_allowed(
                _drop(access_scope=AccessScope.PRIVATE, owner_user_id="user-1"),
                RequestAuthContext(user_id="user-2", username="other"),
            )

    def test_owner_helpers_use_user_id(self):
        drop = _drop(owner_user_id="user-1")

        assert is_drop_owner(drop, RequestAuthContext(user_id="user-1"))
        assert not is_drop_owner(drop, RequestAuthContext(user_id="user-2"))

        assert_drop_owner(drop, RequestAuthContext(user_id="user-1"))
        with pytest.raises(DropAccessDeniedError):
            assert_drop_owner(drop, RequestAuthContext(user_id="user-2"))

    def test_assert_drop_password_matches_accepts_none_pair_and_trimmed_match(self):
        assert_drop_password_matches(
            _drop(drop_password=None),
            None,
            self._grant_service,
        )
        password_hash = hash_drop_password("  secret  ")
        assert_drop_password_matches(
            _drop(drop_password=password_hash),
            _credential("secret"),
            self._grant_service,
        )

    def test_drop_password_hash_does_not_store_plaintext(self):
        password_hash = hash_drop_password("secret")

        assert password_hash is not None
        assert password_hash != "secret"
        assert verify_drop_password_hash(password_hash, "secret")
        assert not verify_drop_password_hash(password_hash, "wrong")

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
                _drop(drop_password=hash_drop_password(expected)),
                _credential(provided),
                self._grant_service,
            )

    def test_assert_drop_password_matches_rejects_non_hash_storage(self):
        with pytest.raises(DropPasswordInvalidError):
            assert_drop_password_matches(
                _drop(drop_password="secret"),
                _credential("secret"),
                self._grant_service,
            )

    def test_assert_drop_password_matches_ignores_credential_when_password_not_required(self):
        assert_drop_password_matches(
            _drop(drop_password=None),
            _credential("secret"),
            self._grant_service,
        )
