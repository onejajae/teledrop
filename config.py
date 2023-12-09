import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_mode: str

    db_host: str

    share_directory: str

    need_login: bool
    register_code: str

    api_server_host: str
    web_server_host: str

    jwt_secret: str
    jwt_hash_algorithm: str
    jwt_exp_minute: int

    allow_cors_origins: list[str]


class DevSettings(Settings):
    app_mode: str = "dev"
    model_config = SettingsConfigDict(env_file=".env.dev", env_file_encoding="utf-8")


class ProdSettings(Settings):
    app_mode: str = "prod"
    model_config = SettingsConfigDict(env_file=".env.prod", env_file_encoding="utf-8")


@lru_cache()
def get_settings() -> Settings:
    app_env = os.getenv("APP_MODE")
    if app_env == "prod":
        return ProdSettings()
    # if (app_env is None) | (app_env == "dev"):
    else:
        return DevSettings()
