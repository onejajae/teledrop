"""
API Key 삭제 Handler

API Key 삭제 관련 비즈니스 로직을 처리합니다.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlmodel import Session

from app.models import ApiKey
from app.handlers.base import BaseHandler, TransactionMixin
from app.core.config import Settings
from app.core.exceptions import ApiKeyNotFoundError, ValidationError


@dataclass
class ApiKeyDeleteHandler(BaseHandler, TransactionMixin):
    """API Key 삭제 Handler"""
    
    session: Session
    settings: Settings
    
    async def execute(
        self,
        api_key_id: str,
        auth_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        API Key를 삭제합니다.
        
        Args:
            api_key_id: API Key ID
            auth_data: 인증 정보 (관리자 권한 필요)
            
        Returns:
            bool: 삭제 성공 여부
            
        Raises:
            ApiKeyNotFoundError: API Key를 찾을 수 없는 경우
            ValidationError: 권한 검증 실패
        """
        self.log_info("Deleting API key", api_key_id=api_key_id)
        
        # 관리자 권한 확인 (Settings 활용)
        if self.settings.REQUIRE_AUTH_FOR_SENSITIVE_OPS and not auth_data:
            raise ValidationError("Authentication required to delete API key")
        
        async def delete_operation():
            # API Key 조회
            api_key = await ApiKey.get_by_id(self.session, api_key_id)
            if not api_key:
                raise ApiKeyNotFoundError(f"API key not found: {api_key_id}")
            
            # API Key 삭제
            await self.session.delete(api_key)
            await self.session.commit()
            
            return True
        
        success = await self.rollback_on_error(
            delete_operation,
            "Failed to delete API key"
        )
        
        self.log_info("API key deleted successfully", api_key_id=api_key_id)
        return success 