"""
Auth Handler 팩토리 모듈

인증 관련 Handler들의 의존성 주입 팩토리를 제공합니다.
"""

from fastapi import Depends

from sqlmodel import Session
from app.core.config import Settings

from app.dependencies.db import get_session
from app.dependencies.settings import get_settings


def get_login_handler():
    """LoginHandler 의존성 팩토리"""
    from app.handlers.auth_handlers import LoginHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ) -> LoginHandler:
        return LoginHandler(session=session, settings=settings)
    
    return _get_handler


def get_token_validate_handler():
    """TokenValidateHandler 의존성 팩토리"""
    from app.handlers.auth_handlers import TokenValidateHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ) -> TokenValidateHandler:
        return TokenValidateHandler(session=session, settings=settings)
    
    return _get_handler


def get_token_refresh_handler():
    """TokenRefreshHandler 의존성 팩토리"""
    from app.handlers.auth_handlers import TokenRefreshHandler
    
    def _get_handler(
        session: Session = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ) -> TokenRefreshHandler:
        return TokenRefreshHandler(session=session, settings=settings)
    
    return _get_handler 