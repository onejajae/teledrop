"""
Drop 접근 권한 검증 Handler

Drop의 접근 권한 검증 관련 비즈니스 로직을 처리합니다.
보안과 관련된 횡단 관심사를 담당합니다.
"""

from typing import Optional, Dict, Any

from sqlmodel import Session
from fastapi import Depends

from app.core.config import Settings
from app.core.dependencies import get_session, get_settings
from app.core.exceptions import DropNotFoundError, DropPasswordInvalidError, DropAccessDeniedError
from app.handlers.base import BaseHandler
from app.models import Drop

class DropAccessHandler(BaseHandler):
    """Drop 접근 권한 검증 Handler"""
    
    def __init__(
        self,
        session: Session = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.settings = settings
    
    def execute(
        self,
        slug: str,
        password: Optional[str] = None,
        auth_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Drop 접근 권한을 검증하고 접근 정보를 반환합니다.
        
        Args:
            slug: Drop 키
            password: Drop 패스워드 (필요한 경우)
            auth_data: 인증 정보
            
        Returns:
            Dict[str, Any]: 접근 권한 정보
            
        Raises:
            DropNotFoundError: Drop을 찾을 수 없는 경우
            DropPasswordInvalidError: 패스워드가 틀린 경우
            DropAccessDeniedError: 접근 권한이 없는 경우
        """
        self.log_info("Validating drop access", slug=slug)
        
        # Drop 조회
        drop = self._get_drop(slug)
        
        # 접근 권한 검증
        access_granted = True
        requires_auth = drop.is_private and self.settings.REQUIRE_AUTH_FOR_SENSITIVE_OPS
        requires_password = bool(drop.password) and self.settings.ENABLE_PASSWORD_PROTECTION
        
        try:
            # 사용자 전용 Drop 검증
            if requires_auth:
                self._validate_user_access(drop, auth_data)
            
            # 패스워드 검증
            if requires_password:
                self._validate_password(drop, password)
                
        except (DropAccessDeniedError, DropPasswordInvalidError):
            access_granted = False
            raise
        
        result = {
            "slug": slug,
            "access_granted": access_granted,
            "requires_auth": requires_auth,
            "requires_password": requires_password,
            "drop_info": {
                "title": drop.title,
                "description": drop.description,
                "created_time": drop.created_time,
                "favorite": drop.is_favorite
            }
        }
        
        self.log_info("Drop access validated", slug=slug, granted=access_granted)
        return result
    
    def validate_access(
        self,
        slug: str,
        password: Optional[str] = None,
        auth_data: Optional[Dict[str, Any]] = None,
        require_auth: bool = True
    ) -> Drop:
        """
        Drop의 접근 권한을 검증합니다. (라우터에서 사용)
        
        인증, 패스워드, 권한을 모두 검증하여 Drop 객체를 반환합니다.
        
        Args:
            slug: Drop 키
            password: 입력된 패스워드
            auth_data: 인증 정보
            require_auth: 인증 필수 여부 (기본값: True)
            
        Returns:
            Drop: 검증된 Drop 객체
            
        Raises:
            DropNotFoundError: Drop을 찾을 수 없는 경우
            DropPasswordInvalidError: 패스워드가 틀린 경우
            DropAccessDeniedError: 접근 권한이 없는 경우
        """
        self.log_info("Validating drop access", slug=slug, require_auth=require_auth)
        
        # Drop 조회
        drop = self._get_drop(slug)
        
        # 1. 인증 검증 (필요한 경우)
        if require_auth and self.settings.REQUIRE_AUTH_FOR_SENSITIVE_OPS:
            self._validate_authentication(auth_data)
        
        # 2. 사용자 전용 Drop 검증
        if drop.is_private and self.settings.REQUIRE_AUTH_FOR_SENSITIVE_OPS:
            self._validate_user_access(drop, auth_data)
        
        # 3. 패스워드 검증
        if drop.password:
            self._validate_password(drop, password)
        
        self.log_info("Drop access validated", slug=slug)
        return drop
    
    # === 내부 메서드들 ===
    
    def _get_drop(self, slug: str) -> Drop:
        """Drop을 조회합니다."""
        drop = Drop.get_by_slug(self.session, slug)
        if not drop:
            raise DropNotFoundError(f"Drop not found: {slug}")
        return drop
    
    def _validate_authentication(self, auth_data: Optional[Dict[str, Any]]):
        """기본 인증을 검증합니다."""
        if not auth_data:
            self.log_warning("Authentication required but not provided")
            raise DropAccessDeniedError("Authentication required")
    
    def _validate_user_access(self, drop: Drop, auth_data: Optional[Dict[str, Any]]):
        """사용자 전용 Drop 접근 권한을 검증합니다."""
        if not auth_data:
            self.log_warning("Private drop access denied", drop_slug=drop.slug)
            raise DropAccessDeniedError("Authentication required for private drop")
    
    def _validate_password(self, drop: Drop, password: Optional[str]):
        """Drop 패스워드를 검증합니다."""
        if not password or drop.password != password:
            self.log_warning("Invalid password attempt", drop_slug=drop.slug)
            raise DropPasswordInvalidError("Invalid password") 