import uuid
from collections.abc import Mapping, Sequence

from app.application.drop.ports import DropSlugCandidateGeneratorPort
from app.core.utils.slug_generator import generate_slug


class PatternWordPoolsSlugCandidateGenerator(DropSlugCandidateGeneratorPort):
    def __init__(self, word_pools: Mapping[str, Sequence[str]]):
        self._word_pools = {
            name: tuple(words)
            for name, words in word_pools.items()
        }

    async def generate_candidate(self) -> str:
        return generate_slug(word_pools=self._word_pools)


class UuidHexSlugCandidateGenerator(DropSlugCandidateGeneratorPort):
    async def generate_candidate(self) -> str:
        return uuid.uuid4().hex
