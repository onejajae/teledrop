import io
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone

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
    DropRepositoryPort,
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
from app.domain.drop.value_objects import AccessScope, DropSortField
from app.infrastructure.storage.local_file_storage import LocalFileStorage


class _InMemoryRepository(DropRepositoryPort):
    def __init__(self):
        self.items: dict[str, DropEntity] = {}

    async def create(self, data: DropCreateInput) -> DropEntity:
        now = datetime.now(timezone.utc)
        entity = DropEntity(
            id=f"id-{data.slug}",
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

    async def list(self, *, limit: int, offset: int, sort: DropSortField, order: str):
        values = list(self.items.values())
        if sort == DropSortField.TITLE:
            values.sort(key=lambda item: item.title or item.file_name)
        elif sort == DropSortField.SIZE_BYTES:
            values.sort(key=lambda item: item.size_bytes)
        else:
            values.sort(key=lambda item: item.created_at)

        if order == "desc":
            values.reverse()

        return values[offset : offset + limit]

    async def count(self) -> int:
        return len(self.items)

    async def get_by_slug(self, slug: str):
        return self.items.get(slug)

    async def update_by_slug(self, slug: str, data: DropUpdateInput):
        current = self.items.get(slug)
        if current is None:
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

    async def delete_by_slug(self, slug: str) -> bool:
        return self.items.pop(slug, None) is not None


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


class _StubSlugCandidateGenerator(DropSlugCandidateGeneratorPort):
    def __init__(self, candidates: list[str] | None = None):
        self._candidates = list(candidates or ["generated-slug"])

    async def generate_candidate(self) -> str:
        if self._candidates:
            return self._candidates.pop(0)
        return "generated-slug"


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
        ),
        list_drops_use_case=ListDropsUseCase(
            repository=repo,
            default_page_size=10,
            max_page_size=200,
        ),
        stream_source_use_case=GetDropStreamSourceUseCase(
            repository=repo,
            storage=storage,
        ),
        update_drop_use_case=UpdateDropUseCase(uow_factory=uow_factory),
        delete_drop_use_case=DeleteDropUseCase(
            storage=storage,
            uow_factory=uow_factory,
        ),
        availability_use_case=CheckSlugAvailabilityUseCase(slug_service=slug_service),
    )


class TestDropUseCases:
    async def test_create_list_update_stream_delete_happy_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = _InMemoryRepository()
            use_cases = _build_use_cases(repo, temp_dir)

            created = await use_cases.create_drop_use_case.execute(
                CreateDropCommand(
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
                    auth=AuthIdentity(username="tester"),
                )
            )
            assert listed.total == 1
            assert listed.items[0].slug == "k1"

            updated = await use_cases.update_drop_use_case.execute(
                UpdateDropCommand(
                    slug="k1",
                    current_password="pw",
                    title="t2",
                    is_favorite=True,
                )
            )
            assert updated.title == "t2"
            assert updated.is_favorite

            detail, storage_key = await use_cases.stream_source_use_case.execute(
                DropStreamQuery(
                    slug="k1",
                    drop_password="pw",
                    auth=AuthIdentity(username="tester"),
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
                DeleteDropCommand(slug="k1", current_password="pw")
            )
            assert (
                await use_cases.list_drops_use_case.execute(
                    DropListQuery(
                        page=1,
                        page_size=20,
                        sort=DropSortField.CREATED_AT,
                        order="desc",
                        auth=AuthIdentity(username="tester"),
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
            )
            availability_use_case = CheckSlugAvailabilityUseCase(slug_service=slug_service)

            created = await create_use_case.execute(
                CreateDropCommand(
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

    def test_unset_singleton_is_shared_across_models_and_ports(self):
        from app.application.drop.models import UNSET as model_unset
        from app.application.drop.ports import UNSET as port_unset

        assert model_unset is port_unset
