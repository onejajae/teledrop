from pathlib import Path
from unittest.mock import patch

from argon2 import PasswordHasher
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest

from app.bootstrap.container import (
    AppInfra,
    attach_app_infra,
    build_drop_slug_candidate_generator,
    ensure_app_infra,
    get_app_settings,
    get_csrf_token_service,
    get_db_session_factory,
    get_file_storage,
)
from app.infrastructure.slug.candidate_generators import (
    PatternWordPoolsSlugCandidateGenerator,
    UuidHexSlugCandidateGenerator,
)


class _FakeSettings:
    def __init__(self, *, sqlite_host: str = "sqlite:///:memory:", share_directory: str = "share"):
        self.SQLITE_HOST = sqlite_host
        self.SHARE_DIRECTORY = share_directory
        self.DEFAULT_PAGE_SIZE = 10
        self.MAX_PAGE_SIZE = 200
        self.SESSION_TTL_SECONDS = 3600
        self.SESSION_COOKIE_SECURE = True
        self.SESSION_COOKIE_SAMESITE = "lax"
        self.API_DOCS_ENABLED = False
        self.CORS_ALLOW_ALL = False
        self.WEB_USERNAME = "admin"
        self.WEB_PASSWORD = PasswordHasher().hash("password")
        self.CSRF_SECRET_KEY = "test-csrf-secret"

    def validate_auth_configuration(self):
        return None


class TestAppInfra:
    def test_attach_app_infra_creates_shared_resources(self):
        app = FastAPI()
        settings = _FakeSettings(share_directory="share-x")

        attach_app_infra(app, settings)

        assert isinstance(app.state.infra, AppInfra)
        assert app.state.infra.settings is settings
        assert app.state.infra.db_engine is not None
        assert app.state.infra.db_session_factory is not None
        assert app.state.infra.csrf_token_service is not None
        assert app.state.infra.file_storage.share_directory == Path("share-x")
        assert isinstance(
            app.state.infra.drop_slug_candidate_generator,
            PatternWordPoolsSlugCandidateGenerator,
        )
        app.state.infra.db_engine.dispose()

    def test_build_drop_slug_candidate_generator_uses_uuid_when_slug_words_fail(self):
        settings = _FakeSettings(share_directory="share-x")

        with patch(
            "app.bootstrap.container.load_slug_word_pools_from_dir",
            side_effect=ValueError("bad data"),
        ):
            generator = build_drop_slug_candidate_generator(settings)

        assert isinstance(generator, UuidHexSlugCandidateGenerator)

    def test_build_drop_slug_candidate_generator_uses_uuid_when_file_mode_disabled(self):
        settings = _FakeSettings(share_directory="share-x")
        settings.SLUG_WORDS_FILES_ENABLED = False

        generator = build_drop_slug_candidate_generator(settings)

        assert isinstance(generator, UuidHexSlugCandidateGenerator)

    def test_ensure_app_infra_attaches_resources_when_settings_are_provided(self):
        app = FastAPI()
        settings = _FakeSettings()

        with patch("app.bootstrap.container.attach_app_infra") as attach_mock:
            ensure_app_infra(app, settings=settings)

        attach_mock.assert_called_once_with(app, settings)

    def test_ensure_app_infra_requires_explicit_settings(self):
        app = FastAPI()

        with pytest.raises(RuntimeError, match="App infrastructure is not attached"):
            ensure_app_infra(app)

    def test_ensure_app_infra_reuses_existing_resources(self):
        app = FastAPI()
        app.state.infra = object()
        settings = _FakeSettings()

        with patch("app.bootstrap.container.attach_app_infra") as attach_mock:
            ensure_app_infra(app, settings=settings)

        attach_mock.assert_not_called()


class TestProviderAccess:
    def test_bare_fastapi_route_reads_attached_infra_providers(self):
        app = FastAPI()
        settings = _FakeSettings(share_directory="share-y")
        attach_app_infra(app, settings)

        @app.get("/infra")
        def read_infra(
            cfg=Depends(get_app_settings),
            session_factory=Depends(get_db_session_factory),
            csrf_service=Depends(get_csrf_token_service),
            file_storage=Depends(get_file_storage),
        ):
            return {
                "cookie_secure": cfg.SESSION_COOKIE_SECURE,
                "has_session_factory": session_factory is not None,
                "has_csrf_token": bool(csrf_service.generate("sid")),
                "share_directory": str(file_storage.share_directory),
            }

        client = TestClient(app)
        response = client.get("/infra")

        assert response.status_code == 200
        assert response.json() == {
            "cookie_secure": True,
            "has_session_factory": True,
            "has_csrf_token": True,
            "share_directory": "share-y",
        }
        app.state.infra.db_engine.dispose()
