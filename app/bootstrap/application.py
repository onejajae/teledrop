from fastapi import FastAPI

from app.bootstrap.app_factory import create_app_from_settings
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    return create_app_from_settings(settings)
