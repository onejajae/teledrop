import secrets
from typing import Literal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    APP_MODE: Literal["prod", "dev", "test"] = "prod"

    SQLITE_HOST: str = "sqlite:///share/database.db"

    JWT_SECRET: str = secrets.token_urlsafe(32)
    JWT_EXP_MINUTES: int = 15
    JWT_ALGORITHM: str = "HS256"

    SHARE_DIRECTORY: str = "share"
    PREFIX_API_BASE: str = "/api"
    HOST_DOMAIN: str = "localhost"

    PATH_WEB_BUILD: str = "web/build/_app"
    PATH_WEB_INDEX: str = "web/build/index.html"
    PATH_WEB_STATIC: str = "web/build/static"

    WEB_USERNAME: str = "admin"
    WEB_PASSWORD: str = "password"


@lru_cache
def get_settings():
    return Settings()
