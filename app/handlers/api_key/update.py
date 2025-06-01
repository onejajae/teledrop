"""
API Key 수정 Handler

API Key 정보 수정 관련 비즈니스 로직을 처리합니다.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlmodel import Session

from app.models import ApiKey
from app.models.api_key import ApiKeyUpdate
from app.handlers.base import BaseHandler, TransactionMixin
from app.core.config import Settings
from app.core.exceptions import ApiKeyNotFoundError, ValidationError
from app.utils.date_utils import utc_now, add_days


@dataclass
class ApiKeyUpdateHandler(BaseHandler, TransactionMixin):
    """API Key 수정 Handler"""
    
    session: Session
    settings: Settings
    
    async def execute(
        self,
        api_key_id: str,
        update_data: ApiKeyUpdate,
        auth_data: Optional[Dict[str, Any]] = None
    ) -> ApiKey:
        """
        API Key 정보를 수정합니다.
        
        Args:
            api_key_id: API Key ID
            update_data: 수정할 데이터
            auth_data: 인증 정보 (관리자 권한 필요)
            
        Returns:
            ApiKey: 수정된 API Key
            
        Raises:
            ApiKeyNotFoundError: API Key를 찾을 수 없는 경우
            ValidationError: 입력 데이터 검증 실패
        """
        self.log_info("Updating API key", api_key_id=api_key_id)
        
        # 관리자 권한 확인 (Settings 활용)
        if self.settings.REQUIRE_AUTH_FOR_SENSITIVE_OPS and not auth_data:
            raise ValidationError("Authentication required to update API key")
        
        async def update_operation():
            # API Key 조회
            api_key = await ApiKey.get_by_id(self.session, api_key_id)
            if not api_key:
                raise ApiKeyNotFoundError(f"API key not found: {api_key_id}")
            
            # 수정할 필드만 업데이트
            update_dict = update_data.model_dump(exclude_unset=True)
            
            # 만료 시간 업데이트 처리
            if 'expires_in_days' in update_dict:
                expires_in_days = update_dict.pop('expires_in_days')
                if expires_in_days and expires_in_days > 0:
                    api_key.expires_at = add_days(utc_now(), expires_in_days)
                else:
                    api_key.expires_at = None
            
            # 나머지 필드 업데이트
            for field, value in update_dict.items():
                setattr(api_key, field, value)
            
            self.update_timestamps(api_key)
            
            await self.session.commit()
            await self.session.refresh(api_key)
            
            return api_key
        
        api_key = await self.rollback_on_error(
            update_operation,
            "Failed to update API key"
        )
        
        self.log_info("API key updated successfully", api_key_id=str(api_key.id))
        return api_key 