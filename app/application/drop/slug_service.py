import uuid

from app.application.drop.ports import (
    DropRepositoryPort,
    DropSlugCandidateGeneratorPort,
)
from app.domain.drop.errors import DropSlugUnavailableError


DEFAULT_RESERVED_SLUGS = {
    "api",
    "actions",
    "static",
    "auth-panel",
    "drop-panel",
    "drop-detail",
    "upload-panel",
}


class DropSlugService:
    def __init__(
        self,
        repository: DropRepositoryPort,
        candidate_generator: DropSlugCandidateGeneratorPort,
        *,
        max_attempts: int = 10,
        reserved_slugs: set[str] | None = None,
    ):
        self.repository = repository
        self.candidate_generator = candidate_generator
        self.max_attempts = max_attempts
        self.reserved_slugs = set(reserved_slugs or DEFAULT_RESERVED_SLUGS)

    async def is_available(self, slug: str) -> bool:
        normalized = (slug or "").strip()
        if not normalized:
            return False
        if normalized in self.reserved_slugs:
            return False
        return await self.repository.get_by_slug(normalized) is None

    async def resolve(self, requested_slug: str | None) -> str:
        if requested_slug is not None and requested_slug.strip():
            slug = requested_slug.strip()
            if not await self.is_available(slug):
                raise DropSlugUnavailableError()
            return slug

        for _ in range(self.max_attempts):
            candidate = await self.candidate_generator.generate_candidate()
            if await self.is_available(candidate):
                return candidate

        return uuid.uuid4().hex
