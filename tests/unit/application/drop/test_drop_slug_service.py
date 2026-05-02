from datetime import datetime, timezone
import re

import pytest

from app.application.drop.ports import (
    DropCreateInput,
    DropSlugCandidateGeneratorPort,
    DropUpdateInput,
)
from app.application.drop.slug_service import DropSlugService
from app.domain.drop.entities import DropEntity
from app.domain.drop.errors import DropSlugUnavailableError
from app.domain.drop.value_objects import AccessScope, DropSortField


class _Repo:

    def __init__(self):
        self.items: dict[str, DropEntity] = {}

    async def create(self, data: DropCreateInput) -> DropEntity:
        now = datetime.now(timezone.utc)
        entity = DropEntity(id=data.slug, owner_user_id=data.owner_user_id, slug=data.slug, access_scope=AccessScope.PRIVATE, is_favorite=False, drop_password=None, file_name='f', mime_type='application/octet-stream', size_bytes=0, sha256='sha', storage_key='s', title=None, description=None, created_at=now, updated_at=None)
        self.items[data.slug] = entity
        return entity

    async def list(self, *, owner_user_id: str, limit: int, offset: int, sort: DropSortField, order: str):
        _ = (owner_user_id, limit, offset, sort, order)
        return []

    async def count(self, *, owner_user_id: str) -> int:
        _ = owner_user_id
        return len(self.items)

    async def get_by_slug(self, slug: str) -> DropEntity | None:
        return self.items.get(slug)

    async def get_owned_by_slug(self, slug: str, *, owner_user_id: str) -> DropEntity | None:
        item = self.items.get(slug)
        if item is None or item.owner_user_id != owner_user_id:
            return None
        return item

    async def update_by_slug(self, slug: str, *, owner_user_id: str, data: DropUpdateInput) -> DropEntity | None:
        _ = (slug, owner_user_id, data)
        return None

    async def delete_by_slug(self, slug: str, *, owner_user_id: str) -> bool:
        item = self.items.get(slug)
        if item is None or item.owner_user_id != owner_user_id:
            return False
        self.items.pop(slug, None)
        return True

class _CandidateGenerator(DropSlugCandidateGeneratorPort):

    def __init__(self, candidates: list[str]):
        self.candidates = list(candidates)
        self.calls = 0

    async def generate_candidate(self) -> str:
        self.calls += 1
        if self.candidates:
            return self.candidates.pop(0)
        return 'fallback-candidate'

class TestDropSlugService:

    async def test_manual_slug_available_returns_same_slug(self):
        repo = _Repo()
        generator = _CandidateGenerator(['unused'])
        service = DropSlugService(repository=repo, candidate_generator=generator)
        resolved = await service.resolve('custom-slug')
        assert resolved == 'custom-slug'
        assert generator.calls == 0

    async def test_manual_slug_reserved_raises(self):
        repo = _Repo()
        service = DropSlugService(repository=repo, candidate_generator=_CandidateGenerator(['x']))
        with pytest.raises(DropSlugUnavailableError):
            await service.resolve('api')
        with pytest.raises(DropSlugUnavailableError):
            await service.resolve('drops')
        with pytest.raises(DropSlugUnavailableError):
            await service.resolve('register')
        with pytest.raises(DropSlugUnavailableError):
            await service.resolve('login')
        with pytest.raises(DropSlugUnavailableError):
            await service.resolve('logout')

    async def test_manual_slug_duplicate_raises(self):
        repo = _Repo()
        repo.items['dup'] = DropEntity(id='1', owner_user_id='user-1', slug='dup', access_scope=AccessScope.PRIVATE, is_favorite=False, drop_password=None, file_name='f', mime_type='text/plain', size_bytes=1, sha256='sha', storage_key='s', title=None, description=None, created_at=datetime.now(timezone.utc), updated_at=None)
        service = DropSlugService(repository=repo, candidate_generator=_CandidateGenerator(['x']))
        with pytest.raises(DropSlugUnavailableError):
            await service.resolve('dup')

    async def test_auto_slug_retries_and_succeeds(self):
        repo = _Repo()
        repo.items['taken'] = DropEntity(id='1', owner_user_id='user-1', slug='taken', access_scope=AccessScope.PRIVATE, is_favorite=False, drop_password=None, file_name='f', mime_type='text/plain', size_bytes=1, sha256='sha', storage_key='s', title=None, description=None, created_at=datetime.now(timezone.utc), updated_at=None)
        generator = _CandidateGenerator(['taken', 'free-slug'])
        service = DropSlugService(repository=repo, candidate_generator=generator, max_attempts=3)
        resolved = await service.resolve(None)
        assert resolved == 'free-slug'
        assert generator.calls == 2

    async def test_auto_slug_falls_back_to_uuid_after_max_attempts(self):
        repo = _Repo()
        repo.items['taken'] = DropEntity(id='1', owner_user_id='user-1', slug='taken', access_scope=AccessScope.PRIVATE, is_favorite=False, drop_password=None, file_name='f', mime_type='text/plain', size_bytes=1, sha256='sha', storage_key='s', title=None, description=None, created_at=datetime.now(timezone.utc), updated_at=None)
        generator = _CandidateGenerator(['taken', 'taken', 'taken'])
        service = DropSlugService(repository=repo, candidate_generator=generator, max_attempts=3)
        resolved = await service.resolve(None)
        assert generator.calls == 3
        assert re.search(re.compile('^[0-9a-f]{32}$'), resolved)

    async def test_is_available_rejects_blank_reserved_and_existing(self):
        repo = _Repo()
        repo.items['used'] = DropEntity(id='1', owner_user_id='user-1', slug='used', access_scope=AccessScope.PRIVATE, is_favorite=False, drop_password=None, file_name='f', mime_type='text/plain', size_bytes=1, sha256='sha', storage_key='s', title=None, description=None, created_at=datetime.now(timezone.utc), updated_at=None)
        service = DropSlugService(repository=repo, candidate_generator=_CandidateGenerator(['x']))
        assert not await service.is_available('')
        assert not await service.is_available('api')
        assert not await service.is_available('register')
        assert not await service.is_available('used')
        assert await service.is_available('free')
