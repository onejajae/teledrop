from sqlmodel import Session
from fastapi import Depends
from functools import lru_cache

from app.core.config import Settings
from app.infrastructure.database.connection import get_engine
from app.infrastructure.storage.factory import StorageFactory
from app.infrastructure.storage.base import StorageInterface


@lru_cache
def get_settings() -> Settings:
    """애플리케이션 설정 의존성"""
    return Settings() 


def get_session(settings: Settings = Depends(get_settings)):
    """데이터베이스 세션 의존성"""
    with Session(get_engine(settings)) as session:
        yield session 


def get_storage(settings: Settings = Depends(get_settings)) -> StorageInterface:
    """스토리지 서비스 의존성"""
    return StorageFactory.create_from_settings(settings) 