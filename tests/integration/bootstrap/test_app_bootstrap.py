import asyncio
import importlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bootstrap.application import create_app
from app.bootstrap.lifespan import build_lifespan
from app.bootstrap.runtime_paths import static_files_dir, sqlite_file_path_from_url, sqlite_parent_dir_from_url, template_dir
from app.core.config import Settings
from app.infrastructure.db.schema import (
    ALEMBIC_UPGRADE_COMMAND,
    DatabaseSchemaOutOfDateError,
)
from tests.support.alembic import upgrade_sqlite_db

class _FakeSettings:

    def __init__(self, *, api_docs_enabled: bool=False, cors_allow_all: bool=False, prefix_api_base: str='/api', share_directory: str='share', sqlite_host: str='sqlite:///share/database.db'):
        self.API_DOCS_ENABLED = api_docs_enabled
        self.CORS_ALLOW_ALL = cors_allow_all
        self.PREFIX_API_BASE = prefix_api_base
        self.SHARE_DIRECTORY = share_directory
        self.SQLITE_HOST = sqlite_host

    def validate_auth_configuration(self):
        return None

class TestBootstrapRuntimePath:

    def test_static_files_dir_prefers_interface_web_static(self):
        path = static_files_dir()
        assert str(path).endswith('app/interfaces/web/static')
        assert path.is_dir()

    def test_template_dir_prefers_interface_web_templates(self):
        path = template_dir()
        assert str(path).endswith('app/interfaces/web/templates')
        assert path.is_dir()

    def test_sqlite_relative_url_parent_dir(self):
        assert sqlite_file_path_from_url('sqlite:///share/database.db') == Path('share/database.db')
        assert sqlite_parent_dir_from_url('sqlite:///share/database.db') == Path('share')

    def test_sqlite_absolute_url_parent_dir(self):
        assert sqlite_file_path_from_url('sqlite:////tmp/teledrop/database.db') == Path('/tmp/teledrop/database.db')
        assert sqlite_parent_dir_from_url('sqlite:////tmp/teledrop/database.db') == Path('/tmp/teledrop')

    def test_sqlite_memory_skips_directory(self):
        assert sqlite_file_path_from_url('sqlite:///:memory:') is None
        assert sqlite_parent_dir_from_url('sqlite:///:memory:') is None

    def test_non_sqlite_skips_directory(self):
        assert sqlite_file_path_from_url('postgresql://user:pw@db/app') is None
        assert sqlite_parent_dir_from_url('postgresql://user:pw@db/app') is None

class TestCreateAppBootstrap:

    def test_create_app_defaults_disable_docs_and_cors(self):
        settings = _FakeSettings()
        with patch('app.bootstrap.application.get_settings', return_value=settings):
            app = create_app()
        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None
        assert not any((m.cls is CORSMiddleware for m in app.user_middleware))

    def test_create_app_can_enable_docs_and_cors_explicitly(self):
        settings = _FakeSettings(api_docs_enabled=True, cors_allow_all=True)
        with patch('app.bootstrap.application.get_settings', return_value=settings):
            app = create_app()
        assert app.docs_url == '/docs'
        assert app.redoc_url == '/redoc'
        assert app.openapi_url == '/openapi.json'
        assert any((m.cls is CORSMiddleware for m in app.user_middleware))

    def test_create_app_mounts_static_and_registers_routes(self):
        settings = _FakeSettings(prefix_api_base='/api-x')
        with patch('app.bootstrap.application.get_settings', return_value=settings):
            app = create_app()
        route_paths = [getattr(route, 'path', None) for route in app.routes]
        assert '/static' in route_paths
        assert '/' in route_paths
        assert any((isinstance(path, str) and path.startswith('/api-x/') for path in route_paths))

class TestLifespanBootstrap:

    def test_lifespan_startup_creates_directories_validates_schema_and_disposes_engine(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            share_dir = tmp_path / 'share-dir'
            db_file = tmp_path / 'db-dir' / 'database.db'
            settings = _FakeSettings(share_directory=str(share_dir), sqlite_host=f'sqlite:///{db_file.as_posix()}')
            lifespan = build_lifespan(settings)
            fake_engine = MagicMock()
            fake_container = MagicMock()
            fake_container.db_engine = fake_engine

            async def run_lifespan():
                async with lifespan(FastAPI()):
                    assert share_dir.is_dir()
                    assert db_file.parent.is_dir()
            with patch('app.bootstrap.lifespan.ensure_app_container', return_value=fake_container) as ensure_mock, patch('app.bootstrap.lifespan.assert_db_schema_current') as validate_schema_mock:
                asyncio.run(run_lifespan())
            ensure_mock.assert_called_once()
            assert ensure_mock.call_args.kwargs['settings'] is settings
            validate_schema_mock.assert_called_once_with(fake_engine)
            fake_engine.dispose.assert_called_once_with()

    def test_lifespan_startup_fails_when_db_schema_is_not_migrated(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            share_dir = tmp_path / 'share-dir'
            db_file = tmp_path / 'db-dir' / 'database.db'
            settings = Settings(
                _env_file=None,
                SHARE_DIRECTORY=str(share_dir),
                SQLITE_HOST=f'sqlite:///{db_file.as_posix()}',
            )
            lifespan = build_lifespan(settings)

            async def run_lifespan():
                async with lifespan(FastAPI()):
                    raise AssertionError('lifespan should not reach application startup')

            with pytest.raises(DatabaseSchemaOutOfDateError, match=ALEMBIC_UPGRADE_COMMAND):
                asyncio.run(run_lifespan())

            assert share_dir.is_dir()
            assert db_file.parent.is_dir()

    def test_lifespan_startup_succeeds_after_alembic_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            share_dir = tmp_path / 'share-dir'
            db_file = tmp_path / 'db-dir' / 'database.db'
            sqlite_url = f'sqlite:///{db_file.as_posix()}'
            upgrade_sqlite_db(sqlite_url)

            settings = Settings(
                _env_file=None,
                SHARE_DIRECTORY=str(share_dir),
                SQLITE_HOST=sqlite_url,
            )
            lifespan = build_lifespan(settings)

            async def run_lifespan():
                async with lifespan(FastAPI()):
                    assert share_dir.is_dir()
                    assert db_file.parent.is_dir()

            asyncio.run(run_lifespan())

class TestMainEntrypointSmoke:

    def test_main_exports_app(self):
        settings = _FakeSettings()
        import app.bootstrap.application as bootstrap_application
        with patch.object(bootstrap_application, 'get_settings', return_value=settings):
            import main
            importlib.reload(main)
        assert main.app is not None
