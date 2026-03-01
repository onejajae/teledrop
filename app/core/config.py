import secrets

from functools import lru_cache
from typing import Literal

from argon2 import PasswordHasher
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    APP_MODE: Literal["prod", "dev", "test"] = "prod"

    SQLITE_HOST: str = "sqlite:///share/database.db"

    SHARE_DIRECTORY: str = "share"
    PREFIX_API_BASE: str = "/api"
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 200
    SLUG_WORDS_FILES_ENABLED: bool = True
    SLUG_WORDS_FILES_DIR: str = "app/core/data/slug_words"

    WEB_USERNAME: str = "admin"
    WEB_PASSWORD: str = PasswordHasher().hash("password")
    CSRF_SECRET_KEY: str = secrets.token_urlsafe(32)

    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_TTL_SECONDS: int = 60 * 60 * 24
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    SESSION_COOKIE_PATH: str = "/"

    def validate_auth_configuration(self):
        # In prod, default to secure cookies unless explicitly overridden.
        if self.APP_MODE == "prod" and "SESSION_COOKIE_SECURE" not in self.model_fields_set:
            self.SESSION_COOKIE_SECURE = True

        if not self.CSRF_SECRET_KEY:
            raise ValueError("CSRF_SECRET_KEY must not be empty.")

        if self.SESSION_TTL_SECONDS <= 0:
            raise ValueError("SESSION_TTL_SECONDS must be greater than 0.")

        if self.SESSION_COOKIE_SAMESITE == "none" and not self.SESSION_COOKIE_SECURE:
            raise ValueError("SESSION_COOKIE_SECURE must be true when SESSION_COOKIE_SAMESITE is 'none'.")

        if self.APP_MODE == "prod":
            if not self.SESSION_COOKIE_SECURE:
                raise ValueError("SESSION_COOKIE_SECURE must be true in prod mode.")

            is_default_password = False
            try:
                PasswordHasher().verify(self.WEB_PASSWORD, "password")
                is_default_password = True
            except Exception:
                is_default_password = False

            if self.WEB_USERNAME == "admin" and is_default_password:
                raise ValueError("Default WEB_USERNAME/WEB_PASSWORD cannot be used in prod mode.")

        return None


@lru_cache
def get_settings():
    return Settings()
