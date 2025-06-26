import secrets
from typing import Literal
from argon2 import PasswordHasher
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    APP_MODE: Literal["prod", "dev", "test"] = "prod"

    DATABASE_URL: str = "sqlite+aiosqlite:///share/database.db"
    SQL_ECHO: bool = False

    # 파일 저장 경로
    SHARE_DIRECTORY: str = "share"

    # JWT 관련 설정
    JWT_SECRET: str = secrets.token_urlsafe(32)
    JWT_EXP_MINUTES: int = 15
    JWT_ALGORITHM: str = "HS256"

    # API 라우터 prefix
    PREFIX_API_BASE: str = "/api"

    # 웹 프로젝트 경로
    PATH_WEB_BUILD: str = "web/build/_app"
    PATH_WEB_INDEX: str = "web/build/index.html"
    PATH_WEB_STATIC: str = "web/build/static"

    # 관리자 계정 설정
    WEB_USERNAME: str = "admin"
    WEB_PASSWORD: str = PasswordHasher().hash("password")
    
    # 파일 입출력 청크 크기
    STREAM_CHUNK_SIZE: int = 1024 * 1024 * 64  # 파일 스트리밍 청크 크기
    READ_CHUNK_SIZE: int = 1024 * 1024 * 8 # 파일 읽기 청크 크기
    WRITE_CHUNK_SIZE: int = 1024 * 1024 * 4 # 파일 쓰기 청크 크기
    
    # 페이지네이션 설정
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # 로깅 설정
    LOG_LEVEL: Literal["INFO", "ERROR", "WARNING"] = "INFO"
    ENABLE_HANDLER_LOGGING: bool = True
