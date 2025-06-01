"""
API Key 생성 Handler

새로운 API Key를 생성하는 비즈니스 로직을 처리합니다.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlmodel import Session

from app.models import ApiKey
from app.models.api_key import ApiKeyCreate
from app.handlers.base import BaseHandler, TransactionMixin
from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.handlers.auth_handlers import generate_api_key
from app.utils.date_utils import utc_now, add_days


@dataclass
class ApiKeyCreateHandler(BaseHandler, TransactionMixin):
    """API Key 생성 Handler"""
    
    session: Session
    settings: Settings
    
    async def execute(
        self,
        api_key_data: ApiKeyCreate,
        auth_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        새로운 API Key를 생성합니다.
        
        Args:
            api_key_data: API Key 생성 데이터
            auth_data: 인증 정보 (관리자 권한 필요)
            
        Returns:
            Dict[str, Any]: 생성된 API Key 정보 (실제 키는 한 번만 반환)
            
        Raises:
            ValidationError: 입력 데이터 검증 실패
        """
        self.log_info("Creating new API key", name=api_key_data.name)
        
        # 관리자 권한 확인 (Settings 활용)
        if self.settings.REQUIRE_AUTH_FOR_SENSITIVE_OPS and not auth_data:
            raise ValidationError("Authentication required to create API key")
        
        async def create_operation():
            # API Key 생성 (Settings의 키 길이 사용)
            full_key, prefix, key_hash = generate_api_key(
                key_length=self.settings.API_KEY_LENGTH,
                prefix_length=self.settings.API_KEY_PREFIX_LENGTH
            )
            
            # 만료 시간 설정 (Settings의 기본 만료일 사용)
            expires_at = None
            expires_in_days = api_key_data.expires_in_days
            if expires_in_days is None:
                expires_in_days = self.settings.API_KEY_DEFAULT_EXPIRES_DAYS
            
            if expires_in_days and expires_in_days > 0:
                expires_at = add_days(utc_now(), expires_in_days)
            
            # API Key 레코드 생성
            api_key_dict = api_key_data.model_dump(exclude={'expires_in_days'})
            api_key_dict.update({
                "key_prefix": prefix,
                "key_hash": key_hash,
                "expires_at": expires_at
            })
            
            api_key = ApiKey(**api_key_dict)
            self.update_timestamps(api_key, update_created=True)
            
            self.session.add(api_key)
            await self.session.commit()
            await self.session.refresh(api_key)
            
            return api_key, full_key
        
        api_key, full_key = await self.rollback_on_error(
            create_operation,
            "Failed to create API key"
        )
        
        # 응답 데이터 구성 (실제 키는 한 번만 반환)
        result = {
            "id": str(api_key.id),
            "name": api_key.name,
            "key_prefix": api_key.key_prefix,
            "full_key": full_key,  # 🚨 한 번만 반환!
            "is_active": api_key.is_active,
            "expires_at": api_key.expires_at,
            "created_at": api_key.created_at,
            "warning": "이 키는 다시 표시되지 않습니다. 안전한 곳에 저장하세요."
        }
        
        self.log_info("API key created successfully", 
                     api_key_id=str(api_key.id), 
                     prefix=api_key.key_prefix)
        return result 