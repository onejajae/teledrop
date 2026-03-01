import re
from unittest.mock import patch
from app.infrastructure.slug.candidate_generators import PatternWordPoolsSlugCandidateGenerator, UuidHexSlugCandidateGenerator

class TestSlugCandidateGenerators:

    async def test_pattern_word_pools_generator_uses_generate_slug_with_pools(self):
        generator = PatternWordPoolsSlugCandidateGenerator({'noun': ('cat',), 'verb': ('run',)})
        with patch('app.infrastructure.slug.candidate_generators.generate_slug', return_value='patched-slug') as mock_generate:
            result = await generator.generate_candidate()
        assert result == 'patched-slug'
        mock_generate.assert_called_once()
        assert 'word_pools' in mock_generate.call_args.kwargs

    async def test_uuid_generator_returns_hex(self):
        generator = UuidHexSlugCandidateGenerator()
        assert re.search(re.compile('^[0-9a-f]{32}$'), await generator.generate_candidate())
