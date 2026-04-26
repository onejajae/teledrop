import os
import logging

from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI

from app.bootstrap.container import ensure_app_infra
from app.bootstrap.runtime_paths import sqlite_parent_dir_from_url
from app.core.config import Settings
from app.infrastructure.db.schema import initialize_database_schema


logger = logging.getLogger(__name__)


def build_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        share_directory = Path(settings.SHARE_DIRECTORY)
        share_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with suppress(OSError):
            os.chmod(share_directory, 0o700)

        sqlite_dir = sqlite_parent_dir_from_url(settings.SQLITE_HOST)
        if sqlite_dir is not None:
            sqlite_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            with suppress(OSError):
                os.chmod(sqlite_dir, 0o700)

        ensure_app_infra(_app, settings=settings)
        db_engine = _app.state.infra.db_engine

        try:
            initialize_database_schema(db_engine, settings)
            yield
        finally:
            db_engine.dispose()
            logger.info("Server is shutting down")

    return lifespan
