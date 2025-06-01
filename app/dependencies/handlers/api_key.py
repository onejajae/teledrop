"""
API Key Handler 팩토리 모듈

API Key 관련 Handler들의 의존성 주입 팩토리를 제공합니다.
"""

from fastapi import Depends

from sqlmodel import Session
from app.core.config import Settings

from app.dependencies.db import get_session
from app.dependencies.settings import get_settings


def get_api_key_create_handler():
    """ApiKeyCreateHandler 의존성 팩토리"""
    from app.handlers.api_key import ApiKeyCreateHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ) -> ApiKeyCreateHandler:
        return ApiKeyCreateHandler(session=session, settings=settings)
    
    return _get_handler


def get_api_key_list_handler():
    """ApiKeyListHandler 의존성 팩토리"""
    from app.handlers.api_key import ApiKeyListHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ) -> ApiKeyListHandler:
        return ApiKeyListHandler(session=session, settings=settings)
    
    return _get_handler


def get_api_key_update_handler():
    """ApiKeyUpdateHandler 의존성 팩토리"""
    from app.handlers.api_key import ApiKeyUpdateHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ) -> ApiKeyUpdateHandler:
        return ApiKeyUpdateHandler(session=session, settings=settings)
    
    return _get_handler


def get_api_key_delete_handler():
    """ApiKeyDeleteHandler 의존성 팩토리"""
    from app.handlers.api_key import ApiKeyDeleteHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ) -> ApiKeyDeleteHandler:
        return ApiKeyDeleteHandler(session=session, settings=settings)
    
    return _get_handler


def get_api_key_validate_handler():
    """ApiKeyValidateHandler 의존성 팩토리"""
    from app.handlers.api_key import ApiKeyValidateHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ) -> ApiKeyValidateHandler:
        return ApiKeyValidateHandler(session=session, settings=settings)
    
    return _get_handler 