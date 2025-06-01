"""
스토리지 의존성 모듈

스토리지 서비스 관련 의존성 주입 함수를 제공합니다.
"""

from fastapi import Depends

from app.core.config import Settings
from app.dependencies.settings import get_settings
from app.infrastructure.storage.factory import StorageFactory
from app.infrastructure.storage.base import StorageInterface

def get_storage(settings: Settings = Depends(get_settings)) -> StorageInterface:
    """스토리지 서비스 의존성"""
    return StorageFactory.create_from_settings(settings) 