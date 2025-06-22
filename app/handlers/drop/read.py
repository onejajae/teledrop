"""
Drop 읽기 Handler

Drop의 상세 조회, 미리보기 등의 읽기 관련 비즈니스 로직을 처리합니다.
"""

from typing import Optional, Dict, Any
from sqlmodel import Session
from fastapi import Depends

from app.models import Drop
from app.handlers.base import BaseHandler
from app.handlers.mixins import ValidationMixin
from app.infrastructure.storage.base import StorageInterface
from app.models.drop import DropRead
from app.core.config import Settings
from app.core.exceptions import DropNotFoundError
from app.core.dependencies import get_session, get_storage, get_settings


class DropReadHandler(BaseHandler, ValidationMixin):
    """Drop 읽기 Handler"""

    def __init__(
        self,
        session: Session = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage = storage
        self.settings = settings
    
    def execute(
        self,
        slug: str,
        password: Optional[str] = None,
        auth_data: Optional[Dict[str, Any]] = None
    ) -> Drop:
        """
        Drop 상세 정보를 조회합니다.
        
        Args:
            slug: Drop 키
            password: Drop 패스워드 (필요한 경우)
            auth_data: 인증 정보
            
        Returns:
            Drop: Drop 상세 정보
            
        Raises:
            DropNotFoundError: Drop을 찾을 수 없는 경우
            DropPasswordInvalidError: 패스워드가 틀린 경우
            DropAccessDeniedError: 접근 권한이 없는 경우
        """
        self.log_info("Fetching drop detail", slug=slug)
        
        # Drop 조회
        drop = Drop.get_by_slug(self.session, slug)
        if not drop:
            raise DropNotFoundError(f"Drop not found: {slug}")
        
        # 접근 권한 검증
        self.validate_drop_access(drop, auth_data)
        
        # 패스워드 검증
        self.validate_drop_password(drop, password)
        
        self.log_info("Drop detail fetched successfully", drop_id=str(drop.id))
        return drop
    
    def execute_preview(
        self,
        slug: str,
        password: Optional[str] = None,
        auth_data: Optional[Dict[str, Any]] = None
    ) -> DropRead:
        """
        Drop 미리보기 정보를 조회합니다.
        
        Args:
            slug: Drop 키
            password: Drop 패스워드 (필요한 경우)
            auth_data: 인증 정보
            
        Returns:
            DropRead: Drop 미리보기 정보
            
        Raises:
            DropNotFoundError: Drop을 찾을 수 없는 경우
            DropPasswordInvalidError: 패스워드가 틀린 경우
            DropAccessDeniedError: 접근 권한이 없는 경우
        """
        self.log_info("Fetching drop preview", slug=slug)
        
        # 기본 상세 조회 로직 재사용
        drop = self.execute(slug, password, auth_data)
        
        # DropRead 스키마로 변환 (model_validate 사용)
        preview = DropRead.model_validate(drop)
        
        self.log_info("Drop preview fetched successfully", drop_id=str(drop.id))
        return preview 