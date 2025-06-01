"""
Drop Handler 팩토리 모듈

Drop 관련 Handler들의 의존성 주입 팩토리를 제공합니다.
"""

from fastapi import Depends

from sqlmodel import Session
from app.core.config import Settings
from app.infrastructure.storage.base import StorageInterface

from app.dependencies.db import get_session
from app.dependencies.storage import get_storage
from app.dependencies.settings import get_settings

def get_drop_list_handler():
    """DropListHandler 의존성 팩토리"""
    from app.handlers.drop import DropListHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ) -> DropListHandler:
        return DropListHandler(session=session, storage_service=storage, settings=settings)
    
    return _get_handler


def get_drop_detail_handler():
    """DropDetailHandler 의존성 팩토리"""
    from app.handlers.drop import DropDetailHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ) -> DropDetailHandler:
        return DropDetailHandler(session=session, storage_service=storage, settings=settings)
    
    return _get_handler


def get_drop_create_handler():
    """DropCreateHandler 의존성 팩토리"""
    from app.handlers.drop import DropCreateHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ) -> DropCreateHandler:
        return DropCreateHandler(session=session, storage_service=storage, settings=settings)
    
    return _get_handler


def get_drop_update_handler():
    """DropUpdateHandler 의존성 팩토리"""
    from app.handlers.drop import DropUpdateHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ) -> DropUpdateHandler:
        return DropUpdateHandler(session=session, storage_service=storage, settings=settings)
    
    return _get_handler


def get_drop_delete_handler():
    """DropDeleteHandler 의존성 팩토리"""
    from app.handlers.drop import DropDeleteHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ) -> DropDeleteHandler:
        return DropDeleteHandler(session=session, storage_service=storage, settings=settings)
    
    return _get_handler


def get_drop_access_handler():
    """DropAccessHandler 의존성 팩토리"""
    from app.handlers.drop import DropAccessHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ) -> DropAccessHandler:
        return DropAccessHandler(session=session, storage_service=storage, settings=settings)
    
    return _get_handler 