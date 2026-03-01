import pytest
import importlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from argon2 import PasswordHasher
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import app.infrastructure.db as db_package
import app.infrastructure.db.session as db_session_module
from app.bootstrap.container import AppContainer, attach_app_container, build_app_container, ensure_app_container, get_app_container, get_app_settings
from app.infrastructure.slug.candidate_generators import PatternWordPoolsSlugCandidateGenerator, UuidHexSlugCandidateGenerator
from app.infrastructure.db.init import init_db
from app.infrastructure.db.session import get_session

class _FakeSettings:

    def __init__(self, *, sqlite_host: str='sqlite:///:memory:', share_directory: str='share', app_mode: str='test'):
        self.SQLITE_HOST = sqlite_host
        self.SHARE_DIRECTORY = share_directory
        self.APP_MODE = app_mode
        self.DEFAULT_PAGE_SIZE = 10
        self.MAX_PAGE_SIZE = 200
        self.SESSION_TTL_SECONDS = 3600
        self.WEB_USERNAME = 'admin'
        self.WEB_PASSWORD = PasswordHasher().hash('password')
        self.CSRF_SECRET_KEY = 'test-csrf-secret'

    def validate_auth_configuration(self):
        return None

class TestDbPackageContract:

    def test_session_module_has_no_global_engine_export(self):
        module = importlib.reload(db_session_module)
        assert not hasattr(module, 'engine')

    def test_db_package_no_longer_exports_engine(self):
        module = importlib.reload(db_package)
        assert sorted(module.__all__) == ['get_session', 'init_db']
        assert 'engine' not in module.__all__

    def test_init_db_requires_engine_argument(self):
        with pytest.raises(TypeError):
            init_db()

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

class TestSessionDependency:

    def test_get_session_uses_container_factory_and_closes_session(self):
        app = FastAPI()
        fake_session = MagicMock()
        fake_container = MagicMock(spec=AppContainer)
        fake_container.db_session_factory.return_value = fake_session
        app.state.container = fake_container
        request = SimpleNamespace(app=app)
        session_gen = get_session(request)
        yielded_session = next(session_gen)
        assert yielded_session is fake_session
        with pytest.raises(StopIteration):
            next(session_gen)
        fake_container.db_session_factory.assert_called_once_with()
        fake_session.close.assert_called_once_with()

class TestBareFastApiFallback:

    def test_bare_fastapi_route_can_use_get_app_settings_fallback(self):
        app = FastAPI()

        @app.get('/cfg')
        def read_cfg(settings=Depends(get_app_settings)):
            return {'mode': settings.APP_MODE}
        client = TestClient(app)
        with patch('app.bootstrap.container.get_settings', return_value=_FakeSettings(app_mode='test')):
            response = client.get('/cfg')
        assert response.status_code == 200
        assert 'mode' in response.json()
