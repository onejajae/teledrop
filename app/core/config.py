import secrets
from typing import Literal
from argon2 import PasswordHasher
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    APP_MODE: Literal["prod", "dev", "test"] = "prod"

    # SQLITE_HOST: str = "sqlite:///share/database.db"
    DATABASE_URL: str = "sqlite:///share/database.db"
    SQL_ECHO: bool = False

    # JWT 관련 설정
    JWT_SECRET: str = secrets.token_urlsafe(32)
    JWT_EXP_MINUTES: int = 15
    JWT_ALGORITHM: str = "HS256"

    SHARE_DIRECTORY: str = "share"
    PREFIX_API_BASE: str = "/api"

    PATH_WEB_BUILD: str = "web/build/_app"
    PATH_WEB_INDEX: str = "web/build/index.html"
    PATH_WEB_STATIC: str = "web/build/static"

    # 관리자 계정 설정
    WEB_USERNAME: str = "admin"
    WEB_PASSWORD: str = PasswordHasher().hash("password")
    
    # Handler 관련 설정
    # 파일 업로드 설정
    MAX_FILE_SIZE: int = 1024 * 1024 * 1024  # 1GB
    ALLOWED_FILE_EXTENSIONS: str = ""  # 빈 문자열이면 모든 확장자 허용
    CHUNK_SIZE: int = 8192  # 파일 스트리밍 청크 크기
    
    # 페이지네이션 설정
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # API Key 설정
    API_KEY_LENGTH: int = 64
    API_KEY_PREFIX_LENGTH: int = 8
    API_KEY_DEFAULT_EXPIRES_DAYS: int = 365
    
    # Drop 설정
    DROP_KEY_LENGTH: int = 12
    MAX_DROP_TITLE_LENGTH: int = 200
    MAX_DROP_DESCRIPTION_LENGTH: int = 1000
    
    # 보안 설정
    REQUIRE_AUTH_FOR_SENSITIVE_OPS: bool = True
    ENABLE_PASSWORD_PROTECTION: bool = True
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    ENABLE_HANDLER_LOGGING: bool = True
