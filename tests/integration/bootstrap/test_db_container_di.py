from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from argon2 import PasswordHasher
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from app.bootstrap.container import AppContainer, attach_app_container, build_app_container, ensure_app_container, get_app_container, get_app_settings
from app.infrastructure.slug.candidate_generators import PatternWordPoolsSlugCandidateGenerator, UuidHexSlugCandidateGenerator

class _FakeSettings:

    def __init__(self, *, sqlite_host: str='sqlite:///:memory:', share_directory: str='share'):
        self.SQLITE_HOST = sqlite_host
        self.SHARE_DIRECTORY = share_directory
        self.DEFAULT_PAGE_SIZE = 10
        self.MAX_PAGE_SIZE = 200
        self.SESSION_TTL_SECONDS = 3600
        self.SESSION_COOKIE_SECURE = True
        self.SESSION_COOKIE_SAMESITE = "lax"
        self.API_DOCS_ENABLED = False
        self.CORS_ALLOW_ALL = False
        self.WEB_USERNAME = 'admin'
        self.WEB_PASSWORD = PasswordHasher().hash('password')
        self.CSRF_SECRET_KEY = 'test-csrf-secret'

    def validate_auth_configuration(self):
        return None

class TestAppContainer:

    def test_build_app_container_creates_shared_objects(self):
        settings = _FakeSettings(share_directory='share-x')
        container = build_app_container(settings)
        assert container.settings is settings
        assert container.db_engine is not None
        assert container.db_session_factory is not None
        assert container.csrf_token_service is not None
        assert container.file_storage.share_directory == Path('share-x')
        assert container.drop_slug_candidate_generator is not None
        assert isinstance(container.drop_slug_candidate_generator, PatternWordPoolsSlugCandidateGenerator)
        container.db_engine.dispose()

    def test_build_app_container_uses_uuid_generator_when_slug_words_fail(self):
        settings = _FakeSettings(share_directory='share-x')
        with patch('app.bootstrap.container.load_slug_word_pools_from_dir', side_effect=ValueError('bad data')):
            container = build_app_container(settings)
        assert isinstance(container.drop_slug_candidate_generator, UuidHexSlugCandidateGenerator)
        container.db_engine.dispose()

    def test_build_app_container_uses_uuid_generator_when_file_mode_disabled(self):
        settings = _FakeSettings(share_directory='share-x')
        settings.SLUG_WORDS_FILES_ENABLED = False
        container = build_app_container(settings)
        assert isinstance(container.drop_slug_candidate_generator, UuidHexSlugCandidateGenerator)
        container.db_engine.dispose()

    def test_attach_and_get_container_from_request(self):
        app = FastAPI()
        container = MagicMock(spec=AppContainer)
        attach_app_container(app, container)
        request = SimpleNamespace(app=app)
        assert get_app_container(request) is container

    def test_get_app_settings_reads_container_settings(self):
        app = FastAPI()
        settings = _FakeSettings()
        container = MagicMock(spec=AppContainer)
        container.settings = settings
        app.state.container = container
        request = SimpleNamespace(app=app)
        assert get_app_settings(request) is settings

    def test_ensure_app_container_autocreates_with_warning(self):
        app = FastAPI()
        settings = _FakeSettings()
        fake_container = MagicMock(spec=AppContainer)
        with patch('app.bootstrap.container.get_settings', return_value=settings) as get_settings_mock, patch('app.bootstrap.container.build_app_container', return_value=fake_container) as build_mock, patch('app.bootstrap.container.logger.warning') as warning_mock:
            result = ensure_app_container(app)
        assert result is fake_container
        assert app.state.container is fake_container
        get_settings_mock.assert_called_once_with()
        build_mock.assert_called_once_with(settings)
        warning_mock.assert_called_once()

    def test_ensure_app_container_reuses_existing_container(self):
        app = FastAPI()
        existing = MagicMock(spec=AppContainer)
        app.state.container = existing
        with patch('app.bootstrap.container.build_app_container') as build_mock:
            result = ensure_app_container(app)
        assert result is existing
        build_mock.assert_not_called()

class TestBareFastApiFallback:

    def test_bare_fastapi_route_can_use_get_app_settings_fallback(self):
        app = FastAPI()

        @app.get('/cfg')
        def read_cfg(settings=Depends(get_app_settings)):
            return {'cookie_secure': settings.SESSION_COOKIE_SECURE}
        client = TestClient(app)
        with patch('app.bootstrap.container.get_settings', return_value=_FakeSettings()):
            response = client.get('/cfg')
        assert response.status_code == 200
        assert response.json() == {'cookie_secure': True}
