import io
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib

import pytest

from app.application.auth.types import AuthIdentity
from app.application.drop.models import (
    CreateDropCommand,
    DeleteDropCommand,
    DropListQuery,
    DropStreamQuery,
    UpdateDropCommand,
)
from app.application.drop.ports import (
    DropCreateInput,
    DropSlugCandidateGeneratorPort,
    DropUpdateInput,
    UNSET,
)
from app.application.drop.slug_service import DropSlugService
from app.application.drop.use_cases import (
    CheckSlugAvailabilityUseCase,
    CreateDropUseCase,
    DeleteDropUseCase,
    GetDropStreamSourceUseCase,
    ListDropsUseCase,
    UpdateDropUseCase,
)
from app.domain.drop.entities import DropEntity
from app.domain.drop.errors import (
    DropAccessDeniedError,
    DropSlugUnavailableError,
    DropUploadTooLargeError,
)
from app.domain.drop.grants import DropPasswordCredential, DropPasswordGrantService
from app.domain.drop.policies import hash_drop_password, verify_drop_password_hash
from app.domain.drop.value_objects import AccessScope, DropSortField
from app.infrastructure.storage.local_file_storage import LocalFileStorage


class _InMemoryRepository:
    def __init__(self):
        self.items: dict[str, DropEntity] = {}

    async def create(self, data: DropCreateInput) -> DropEntity:
        if data.slug in self.items:
            raise DropSlugUnavailableError()
        now = datetime.now(timezone.utc)
        entity = DropEntity(
            id=f"id-{data.slug}",
            owner_user_id=data.owner_user_id,
            slug=data.slug,
            access_scope=data.access_scope,
            is_favorite=data.is_favorite,
            drop_password=data.drop_password,
            file_name=data.file_name,
            mime_type=data.mime_type,
            size_bytes=data.size_bytes,
            sha256=data.sha256,
            storage_key=data.storage_key,
            title=data.title,
            description=data.description,
            created_at=now,
            updated_at=None,
        )
        self.items[data.slug] = entity
        return entity

    async def list(
        self,
        *,
        owner_user_id: str,
        limit: int,
        offset: int,
        sort: DropSortField,
        order: str,
    ):
        values = [item for item in self.items.values() if item.owner_user_id == owner_user_id]
        if sort == DropSortField.TITLE:
            values.sort(key=lambda item: item.title or item.file_name)
        elif sort == DropSortField.SIZE_BYTES:
            values.sort(key=lambda item: item.size_bytes)
        else:
            values.sort(key=lambda item: item.created_at)

        if order == "desc":
            values.reverse()

        return values[offset : offset + limit]

    async def count(self, *, owner_user_id: str) -> int:
        return sum(1 for item in self.items.values() if item.owner_user_id == owner_user_id)

    async def get_by_slug(self, slug: str):
        return self.items.get(slug)

    async def get_owned_by_slug(self, slug: str, *, owner_user_id: str):
        current = self.items.get(slug)
        if current is None or current.owner_user_id != owner_user_id:
            return None
        return current

    async def update_by_slug(self, slug: str, *, owner_user_id: str, data: DropUpdateInput):
        current = self.items.get(slug)
        if current is None or current.owner_user_id != owner_user_id:
            return None

        if data.title is not UNSET:
            current.title = data.title
        if data.description is not UNSET:
            current.description = data.description
        if data.access_scope is not UNSET:
            current.access_scope = data.access_scope
        if data.is_favorite is not UNSET:
            current.is_favorite = data.is_favorite
        if data.drop_password is not UNSET:
            current.drop_password = data.drop_password
        current.updated_at = datetime.now(timezone.utc)
        self.items[slug] = current
        return current

    async def delete_by_slug(self, slug: str, *, owner_user_id: str) -> bool:
        current = self.items.get(slug)
        if current is None or current.owner_user_id != owner_user_id:
            return False
        self.items.pop(slug, None)
        return True


class _RaceRepository(_InMemoryRepository):
    def __init__(self, fail_once_slugs: set[str]):
        super().__init__()
        self.fail_once_slugs = fail_once_slugs

    async def create(self, data: DropCreateInput) -> DropEntity:
        if data.slug in self.fail_once_slugs:
            self.fail_once_slugs.remove(data.slug)
            raise DropSlugUnavailableError()
        return await super().create(data)


class _InMemoryDropUow:
    def __init__(self, repository: _InMemoryRepository):
        self.repository = repository

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def commit(self):
        return None

    async def rollback(self):
        return None


class _CommitFailingDropUow(_InMemoryDropUow):
    async def commit(self):
        raise RuntimeError("forced commit failure")


class _StubSlugCandidateGenerator(DropSlugCandidateGeneratorPort):
    def __init__(self, candidates: list[str] | None = None):
        self._candidates = list(candidates or ["generated-slug"])

    async def generate_candidate(self) -> str:
        if self._candidates:
            return self._candidates.pop(0)
        return "generated-slug"


class _DeleteStorageSpy:
    def __init__(self, staged_key: str | None = "staged-key"):
        self.staged_key = staged_key
        self.stage_calls: list[str] = []
        self.rollback_calls: list[tuple[str, str]] = []
        self.finalize_calls: list[str] = []
        self._payloads: dict[str, bytes] = {}
        self._counter = 0

    async def write_stream(self, file_stream, *, max_bytes: int | None = None):
        payload = file_stream.read()
        if max_bytes is not None and len(payload) > max_bytes:
            raise DropUploadTooLargeError()
        storage_key = f"spy-{self._counter}"
        self._counter += 1
        self._payloads[storage_key] = payload
        return storage_key, hashlib.sha256(payload).hexdigest()

    async def discard_upload(self, storage_key: str) -> None:
        self._payloads.pop(storage_key, None)

    async def stage_delete(self, storage_key: str) -> tuple[str, str | None]:
        self.stage_calls.append(storage_key)
        return storage_key, self.staged_key

    async def rollback_staged_delete(self, source_key: str, staged_key: str) -> None:
        self.rollback_calls.append((source_key, staged_key))

    async def finalize_staged_delete(self, staged_key: str) -> None:
        self.finalize_calls.append(staged_key)

    async def stream_range(self, storage_key: str, start: int, end: int):
        payload = self._payloads[storage_key]
        yield payload[start : end + 1]


@dataclass(slots=True)
class _UseCases:
    create_drop_use_case: CreateDropUseCase
    list_drops_use_case: ListDropsUseCase
    stream_source_use_case: GetDropStreamSourceUseCase
    update_drop_use_case: UpdateDropUseCase
    delete_drop_use_case: DeleteDropUseCase
    availability_use_case: CheckSlugAvailabilityUseCase


def _build_use_cases(repo: _InMemoryRepository, temp_dir: str) -> _UseCases:
    storage = LocalFileStorage(temp_dir)
    grant_service = DropPasswordGrantService(secret_key="test-secret", ttl_seconds=3600)
    slug_service = DropSlugService(
        repository=repo,
        candidate_generator=_StubSlugCandidateGenerator(),
    )
    uow_factory = lambda: _InMemoryDropUow(repo)

    return _UseCases(
        create_drop_use_case=CreateDropUseCase(
            storage=storage,
            slug_service=slug_service,
            uow_factory=uow_factory,
            max_upload_bytes=1024 * 1024,
        ),
        list_drops_use_case=ListDropsUseCase(
            repository=repo,
            default_page_size=10,
            max_page_size=200,
        ),
        stream_source_use_case=GetDropStreamSourceUseCase(
            repository=repo,
            storage=storage,
            grant_service=grant_service,
        ),
        update_drop_use_case=UpdateDropUseCase(
            uow_factory=uow_factory,
        ),
        delete_drop_use_case=DeleteDropUseCase(
            storage=storage,
            uow_factory=uow_factory,
        ),
        availability_use_case=CheckSlugAvailabilityUseCase(slug_service=slug_service),
    )


def _password_credential(password: str | None) -> DropPasswordCredential | None:
    if password is None:
        return None
    return DropPasswordCredential(password=password)


def _auth(user_id: str | None, username: str | None = None) -> AuthIdentity:
    return AuthIdentity(user_id=user_id, username=username)


async def _seed_drop(
    repo: _InMemoryRepository,
    *,
    slug: str,
    storage_key: str,
    owner_user_id: str = "user-1",
    drop_password: str | None = "pw",
    title: str | None = "title",
    description: str | None = "desc",
) -> DropEntity:
    return await repo.create(
        DropCreateInput(
            owner_user_id=owner_user_id,
            slug=slug,
            access_scope=AccessScope.PRIVATE,
            is_favorite=False,
            drop_password=hash_drop_password(drop_password),
            file_name=f"{slug}.txt",
            mime_type="text/plain",
            size_bytes=4,
            sha256=f"sha-{slug}",
            storage_key=storage_key,
            title=title,
            description=description,
        )
    )


class TestDropUseCases:
    async def test_create_list_update_stream_delete_happy_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = _InMemoryRepository()
            use_cases = _build_use_cases(repo, temp_dir)

            created = await use_cases.create_drop_use_case.execute(
                CreateDropCommand(
                    owner_user_id="user-1",
                    file_stream=io.BytesIO(b"hello world"),
                    file_name="hello.txt",
                    mime_type="text/plain",
                    size_bytes=11,
                    slug="k1",
                    access_scope=AccessScope.PRIVATE,
                    drop_password="pw",
                    title="t1",
                    description="d1",
                )
            )
            assert created.slug == "k1"

            listed = await use_cases.list_drops_use_case.execute(
                DropListQuery(
                    page=1,
                    page_size=20,
                    sort=DropSortField.CREATED_AT,
                    order="desc",
                    auth=_auth("user-1", "tester"),
                )
            )
            assert listed.total == 1
            assert listed.items[0].slug == "k1"
            assert listed.items[0].owner_user_id == "user-1"

            updated = await use_cases.update_drop_use_case.execute(
                UpdateDropCommand(
                    slug="k1",
                    auth=_auth("user-1", "tester"),
                    title="t2",
                    is_favorite=True,
                )
            )
            assert updated.title == "t2"
            assert updated.is_favorite

            detail, storage_key = await use_cases.stream_source_use_case.execute(
                DropStreamQuery(
                    slug="k1",
                    drop_password=None,
                    auth=_auth("user-1", "tester"),
                )
            )
            assert detail.file_name == "hello.txt"

            chunks = []
            async for chunk in use_cases.stream_source_use_case.iter_stream_range(
                storage_key, 0, 4
            ):
                chunks.append(chunk)
            assert b"".join(chunks) == b"hello"

            await use_cases.delete_drop_use_case.execute(
                DeleteDropCommand(
                    slug="k1",
                    auth=_auth("user-1", "tester"),
                )
            )
            assert (
                await use_cases.list_drops_use_case.execute(
                    DropListQuery(
                        page=1,
                        page_size=20,
                        sort=DropSortField.CREATED_AT,
                        order="desc",
                        auth=_auth("user-1", "tester"),
                    )
                )
            ).total == 0

    async def test_create_uses_slug_service_for_generated_slug(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = _InMemoryRepository()
            storage = LocalFileStorage(temp_dir)
            slug_service = DropSlugService(
                repository=repo,
                candidate_generator=_StubSlugCandidateGenerator(["cat-dance-happy"]),
            )
            uow_factory = lambda: _InMemoryDropUow(repo)
            create_use_case = CreateDropUseCase(
                storage=storage,
                slug_service=slug_service,
                uow_factory=uow_factory,
                max_upload_bytes=1024 * 1024,
            )
            availability_use_case = CheckSlugAvailabilityUseCase(slug_service=slug_service)

            created = await create_use_case.execute(
                CreateDropCommand(
                    owner_user_id="user-1",
                    file_stream=io.BytesIO(b"hello"),
                    file_name="hello.txt",
                    mime_type="text/plain",
                    size_bytes=5,
                    slug=None,
                    access_scope=AccessScope.PRIVATE,
                    drop_password=None,
                    title=None,
                    description=None,
                )
            )

            assert created.slug == "cat-dance-happy"
            assert await availability_use_case.execute("another-slug")
            assert not await availability_use_case.execute("cat-dance-happy")

    async def test_create_rejects_invalid_manual_slug_before_storage_write(self):
        repo = _InMemoryRepository()
        storage = _DeleteStorageSpy()
        slug_service = DropSlugService(
            repository=repo,
            candidate_generator=_StubSlugCandidateGenerator(),
        )
        create_use_case = CreateDropUseCase(
            storage=storage,
            slug_service=slug_service,
            uow_factory=lambda: _InMemoryDropUow(repo),
            max_upload_bytes=1024 * 1024,
        )

        with pytest.raises(DropSlugUnavailableError):
            await create_use_case.execute(
                CreateDropCommand(
                    owner_user_id="user-1",
                    file_stream=io.BytesIO(b"hello"),
                    file_name="hello.txt",
                    mime_type="text/plain",
                    size_bytes=5,
                    slug="a/b",
                    access_scope=AccessScope.PRIVATE,
                    drop_password=None,
                    title=None,
                    description=None,
                )
            )

        assert repo.items == {}
        assert storage._counter == 0

    async def test_create_retries_generated_slug_after_repository_unique_race(self):
        repo = _RaceRepository({"race-slug"})
        storage = _DeleteStorageSpy()
        slug_service = DropSlugService(
            repository=repo,
            candidate_generator=_StubSlugCandidateGenerator(["race-slug", "free-slug"]),
        )
        create_use_case = CreateDropUseCase(
            storage=storage,
            slug_service=slug_service,
            uow_factory=lambda: _InMemoryDropUow(repo),
            max_upload_bytes=1024 * 1024,
        )

        created = await create_use_case.execute(
            CreateDropCommand(
                owner_user_id="user-1",
                file_stream=io.BytesIO(b"hello"),
                file_name="hello.txt",
                mime_type="text/plain",
                size_bytes=5,
                slug=None,
                access_scope=AccessScope.PRIVATE,
                drop_password=None,
                title=None,
                description=None,
            )
        )

        assert created.slug == "free-slug"
        assert "race-slug" not in repo.items
        assert list(storage._payloads) == ["spy-0"]

    async def test_create_explicit_slug_unique_race_discards_written_file(self):
        repo = _RaceRepository({"fixed-slug"})
        storage = _DeleteStorageSpy()
        slug_service = DropSlugService(
            repository=repo,
            candidate_generator=_StubSlugCandidateGenerator(),
        )
        create_use_case = CreateDropUseCase(
            storage=storage,
            slug_service=slug_service,
            uow_factory=lambda: _InMemoryDropUow(repo),
            max_upload_bytes=1024 * 1024,
        )

        with pytest.raises(DropSlugUnavailableError):
            await create_use_case.execute(
                CreateDropCommand(
                    owner_user_id="user-1",
                    file_stream=io.BytesIO(b"hello"),
                    file_name="hello.txt",
                    mime_type="text/plain",
                    size_bytes=5,
                    slug="fixed-slug",
                    access_scope=AccessScope.PRIVATE,
                    drop_password=None,
                    title=None,
                    description=None,
                )
            )

        assert storage._payloads == {}

    async def test_create_discards_written_file_when_commit_fails(self):
        repo = _InMemoryRepository()
        storage = _DeleteStorageSpy()
        slug_service = DropSlugService(
            repository=repo,
            candidate_generator=_StubSlugCandidateGenerator(),
        )
        create_use_case = CreateDropUseCase(
            storage=storage,
            slug_service=slug_service,
            uow_factory=lambda: _CommitFailingDropUow(repo),
            max_upload_bytes=1024 * 1024,
        )

        with pytest.raises(RuntimeError, match="forced commit failure"):
            await create_use_case.execute(
                CreateDropCommand(
                    owner_user_id="user-1",
                    file_stream=io.BytesIO(b"hello"),
                    file_name="hello.txt",
                    mime_type="text/plain",
                    size_bytes=5,
                    slug="commit-fail",
                    access_scope=AccessScope.PRIVATE,
                    drop_password=None,
                    title=None,
                    description=None,
                )
            )

        assert storage._payloads == {}

    async def test_create_rejects_upload_larger_than_configured_limit(self):
        repo = _InMemoryRepository()
        storage = _DeleteStorageSpy()
        slug_service = DropSlugService(
            repository=repo,
            candidate_generator=_StubSlugCandidateGenerator(),
        )
        create_use_case = CreateDropUseCase(
            storage=storage,
            slug_service=slug_service,
            uow_factory=lambda: _InMemoryDropUow(repo),
            max_upload_bytes=4,
        )

        with pytest.raises(DropUploadTooLargeError):
            await create_use_case.execute(
                CreateDropCommand(
                    owner_user_id="user-1",
                    file_stream=io.BytesIO(b"hello"),
                    file_name="hello.txt",
                    mime_type="text/plain",
                    size_bytes=5,
                    slug="too-large",
                    access_scope=AccessScope.PRIVATE,
                    drop_password=None,
                    title=None,
                    description=None,
                )
            )

        assert storage._payloads == {}

    async def test_list_drops_requires_authenticated_identity(self):
        repo = _InMemoryRepository()
        use_case = ListDropsUseCase(
            repository=repo,
            default_page_size=10,
            max_page_size=200,
        )

        with pytest.raises(DropAccessDeniedError):
            await use_case.execute(
                DropListQuery(
                    page=1,
                    page_size=20,
                    sort=DropSortField.CREATED_AT,
                    order="desc",
                    auth=_auth(None, None),
                )
            )

    async def test_list_drops_returns_only_owner_items(self):
        repo = _InMemoryRepository()
        await _seed_drop(repo, slug="mine", storage_key="storage-mine", owner_user_id="user-1")
        await _seed_drop(repo, slug="other", storage_key="storage-other", owner_user_id="user-2")
        use_case = ListDropsUseCase(
            repository=repo,
            default_page_size=10,
            max_page_size=200,
        )

        listed = await use_case.execute(
            DropListQuery(
                page=1,
                page_size=20,
                sort=DropSortField.CREATED_AT,
                order="desc",
                auth=_auth("user-1", "tester"),
            )
        )

        assert listed.total == 1
        assert [item.slug for item in listed.items] == ["mine"]

    async def test_create_normalizes_password_with_trim(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = _InMemoryRepository()
            use_cases = _build_use_cases(repo, temp_dir)

            created = await use_cases.create_drop_use_case.execute(
                CreateDropCommand(
                    owner_user_id="user-1",
                    file_stream=io.BytesIO(b"hello"),
                    file_name="hello.txt",
                    mime_type="text/plain",
                    size_bytes=5,
                    slug="trimmed",
                    access_scope=AccessScope.PRIVATE,
                    drop_password="  pw  ",
                    title=None,
                    description=None,
                )
            )

            assert created.requires_password
            assert repo.items["trimmed"].drop_password != "pw"
            assert verify_drop_password_hash(repo.items["trimmed"].drop_password, "pw")

    async def test_update_distinguishes_unset_and_explicit_none(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = _InMemoryRepository()
            use_cases = _build_use_cases(repo, temp_dir)

            await use_cases.create_drop_use_case.execute(
                CreateDropCommand(
                    owner_user_id="user-1",
                    file_stream=io.BytesIO(b"hello"),
                    file_name="hello.txt",
                    mime_type="text/plain",
                    size_bytes=5,
                    slug="k-update",
                    access_scope=AccessScope.PRIVATE,
                    drop_password="pw",
                    title="original",
                    description="before",
                )
            )

            omitted_title = await use_cases.update_drop_use_case.execute(
                UpdateDropCommand(
                    slug="k-update",
                    auth=_auth("user-1", "tester"),
                    description=None,
                )
            )
            assert omitted_title.title == "original"
            assert omitted_title.description is None

            explicit_null_title = await use_cases.update_drop_use_case.execute(
                UpdateDropCommand(
                    slug="k-update",
                    auth=_auth("user-1", "tester"),
                    title=None,
                )
            )
            assert explicit_null_title.title is None

    async def test_owner_can_clear_password(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = _InMemoryRepository()
            use_cases = _build_use_cases(repo, temp_dir)

            await use_cases.create_drop_use_case.execute(
                CreateDropCommand(
                    owner_user_id="user-1",
                    file_stream=io.BytesIO(b"hello"),
                    file_name="hello.txt",
                    mime_type="text/plain",
                    size_bytes=5,
                    slug="k-clear",
                    access_scope=AccessScope.PRIVATE,
                    drop_password="pw",
                    title="locked",
                    description=None,
                )
            )

            updated = await use_cases.update_drop_use_case.execute(
                UpdateDropCommand(
                    slug="k-clear",
                    auth=_auth("user-1", "tester"),
                    new_password=None,
                )
            )

            assert updated.requires_password is False
            assert repo.items["k-clear"].drop_password is None

    async def test_non_owner_cannot_update_or_delete_private_drop(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = _InMemoryRepository()
            use_cases = _build_use_cases(repo, temp_dir)
            await _seed_drop(
                repo,
                slug="owned",
                storage_key="storage-owned",
                owner_user_id="user-1",
            )

            with pytest.raises(DropAccessDeniedError):
                await use_cases.update_drop_use_case.execute(
                    UpdateDropCommand(
                        slug="owned",
                        auth=_auth("user-2", "other"),
                        title="nope",
                    )
                )

            with pytest.raises(DropAccessDeniedError):
                await use_cases.delete_drop_use_case.execute(
                    DeleteDropCommand(
                        slug="owned",
                        auth=_auth("user-2", "other"),
                    )
                )

    async def test_delete_finalizes_staged_file_on_success(self):
        repo = _InMemoryRepository()
        storage = _DeleteStorageSpy(staged_key="staged-1")
        await _seed_drop(repo, slug="k-delete", storage_key="storage-k-delete")
        use_case = DeleteDropUseCase(
            storage=storage,
            uow_factory=lambda: _InMemoryDropUow(repo),
        )

        await use_case.execute(
            DeleteDropCommand(
                slug="k-delete",
                auth=_auth("user-1", "tester"),
            )
        )

        assert storage.stage_calls == ["storage-k-delete"]
        assert storage.rollback_calls == []
        assert storage.finalize_calls == ["staged-1"]

    async def test_delete_rolls_back_staged_file_when_commit_fails(self):
        repo = _InMemoryRepository()
        storage = _DeleteStorageSpy(staged_key="staged-2")
        await _seed_drop(repo, slug="k-rollback", storage_key="storage-k-rollback")
        use_case = DeleteDropUseCase(
            storage=storage,
            uow_factory=lambda: _CommitFailingDropUow(repo),
        )

        with pytest.raises(RuntimeError, match="forced commit failure"):
            await use_case.execute(
                DeleteDropCommand(
                    slug="k-rollback",
                    auth=_auth("user-1", "tester"),
                )
            )

        assert storage.stage_calls == ["storage-k-rollback"]
        assert storage.rollback_calls == [("storage-k-rollback", "staged-2")]
        assert storage.finalize_calls == []

    def test_unset_singleton_is_shared_across_models_and_ports(self):
        from app.application.drop.models import UNSET as model_unset
        from app.application.drop.ports import UNSET as port_unset

        assert model_unset is port_unset

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Known residual risk: a delete can stage the file before a concurrent "
            "download stream opens it."
        ),
    )
    async def test_known_risk_delete_can_remove_file_before_concurrent_stream_opens(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorage(temp_dir)
            storage_key, _sha256 = await storage.write_stream(
                io.BytesIO(b"hello"),
                max_bytes=1024,
            )

            stream = storage.stream_range(storage_key, 0, 4)
            await storage.stage_delete(storage_key)

            chunks = []
            async for chunk in stream:
                chunks.append(chunk)

            assert b"".join(chunks) == b"hello"
