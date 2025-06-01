"""
API Key 검증 Handler

API Key 유효성 검증 관련 비즈니스 로직을 처리합니다.
"""

from dataclasses import dataclass
from typing import Any, Dict

from sqlmodel import Session

from app.models import ApiKey
from app.handlers.base import BaseHandler
from app.core.config import Settings
from app.core.exceptions import ApiKeyInvalidError
from app.handlers.auth_handlers import hash_api_key


@dataclass
class ApiKeyValidateHandler(BaseHandler):
    """API Key 검증 Handler"""
    
    session: Session
    settings: Settings
    
    async def execute(
        self,
        api_key: str,
        update_last_used: bool = True
    ) -> Dict[str, Any]:
        """
        API Key를 검증하고 관련 정보를 반환합니다.
        
        Args:
            api_key: 검증할 API Key
            update_last_used: 마지막 사용 시간 업데이트 여부
            
        Returns:
            Dict[str, Any]: 검증 결과 및 API Key 정보
            
        Raises:
            ApiKeyInvalidError: 유효하지 않은 API Key
        """
        self.log_info("Validating API key", key_prefix=api_key[:10] + "..." if len(api_key) > 10 else api_key)
        
        # API Key 형식 검증 (Settings 활용)
        if not self.validate_api_key_format(api_key):
            raise ApiKeyInvalidError("Invalid API key format")
        
        # 해시 계산
        key_hash = hash_api_key(api_key)
        
        # 데이터베이스에서 API Key 조회
        db_api_key = await ApiKey.get_by_hash(self.session, key_hash)
        if not db_api_key:
            raise ApiKeyInvalidError("API key not found")
        
        # 활성 상태 확인
        if not db_api_key.is_active:
            raise ApiKeyInvalidError("API key is inactive")
        
        # 만료 확인
        if db_api_key.is_expired:
            raise ApiKeyInvalidError("API key has expired")
        
        # 마지막 사용 시간 업데이트
        if update_last_used:
            await db_api_key.update_last_used(self.session)
        
        # 검증 결과 반환
        result = {
            "valid": True,
            "api_key_info": {
                "id": str(db_api_key.id),
                "name": db_api_key.name,
                "key_prefix": db_api_key.key_prefix,
                "is_active": db_api_key.is_active,
                "expires_at": db_api_key.expires_at,
                "last_used_at": db_api_key.last_used_at,
                "created_at": db_api_key.created_at,
                "status": db_api_key.status
            }
        }
        
        self.log_info("API key validated successfully", 
                     api_key_id=str(db_api_key.id),
                     name=db_api_key.name)
        return result 