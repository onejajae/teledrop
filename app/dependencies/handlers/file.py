"""
File Handler 팩토리 모듈

File 관련 Handler들의 의존성 주입 팩토리를 제공합니다.
"""

from fastapi import Depends

from sqlmodel import Session
from app.core.config import Settings
from app.infrastructure.storage.base import StorageInterface

from app.dependencies.db import get_session
from app.dependencies.storage import get_storage
from app.dependencies.settings import get_settings


def get_file_download_handler():
    """FileDownloadHandler 의존성 팩토리"""
    from app.handlers.file import FileDownloadHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ) -> FileDownloadHandler:
        return FileDownloadHandler(session=session, storage_service=storage, settings=settings)
    
    return _get_handler


def get_file_range_handler():
    """FileRangeHandler 의존성 팩토리"""
    from app.handlers.file import FileRangeHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ) -> FileRangeHandler:
        return FileRangeHandler(session=session, storage_service=storage, settings=settings)
    
    return _get_handler 