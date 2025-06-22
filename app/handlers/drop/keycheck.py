"""
Drop 키 중복 확인 Handler

Drop 키의 사용 가능 여부를 확인하는 비즈니스 로직을 처리합니다.
"""

from fastapi import Depends
from sqlmodel import Session

from app.models import Drop
from app.handlers.base import BaseHandler
from app.core.config import Settings
from app.core.dependencies import get_session, get_settings


class DropSlugCheckHandler(BaseHandler):
    """Drop 키 사용 가능 여부 확인 Handler"""
    
    def __init__(
        self,
        session: Session = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.settings = settings
        self.reserved_slugs: set[str] = {"api", ""}

    def execute(self, slug: str) -> bool:
        """
        Drop 키의 사용 가능 여부를 확인합니다.
        
        Args:
            slug: 확인할 키
            
        """
        self.log_info("Checking slug availability", slug=slug)
        
        # 예약어 체크
        if slug in self.reserved_slugs:
            self.log_info("Slug is reserved", slug=slug)
            return True
        
        # DB에 이미 존재하는지 체크
        drop = Drop.get_by_slug(self.session, slug)
        
        self.log_info("Slug availability checked", slug=slug, available=drop is None)
        return drop is not None