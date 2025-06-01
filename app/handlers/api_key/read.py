"""
API Key 조회 Handler

API Key 목록 조회 관련 비즈니스 로직을 처리합니다.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlmodel import Session

from app.models import ApiKey
from app.handlers.base import BaseHandler, PaginationMixin
from app.core.config import Settings
from app.core.exceptions import ValidationError


@dataclass
class ApiKeyListHandler(BaseHandler, PaginationMixin):
    """API Key 목록 조회 Handler"""
    
    session: Session
    settings: Settings
    
    async def execute(
        self,
        active_only: bool = True,
        page: int = 1,
        page_size: Optional[int] = None,
        auth_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        API Key 목록을 조회합니다.
        
        Args:
            active_only: 활성 키만 조회할지 여부
            page: 페이지 번호
            page_size: 페이지 크기 (None이면 설정값 사용)
            auth_data: 인증 정보 (관리자 권한 필요)
            
        Returns:
            Dict[str, Any]: 페이지네이션된 API Key 목록
        """
        self.log_info("Fetching API key list", active_only=active_only, page=page, page_size=page_size)
        
        # 관리자 권한 확인 (Settings 활용)
        if self.settings.REQUIRE_AUTH_FOR_SENSITIVE_OPS and not auth_data:
            raise ValidationError("Authentication required to list API keys")
        
        # 페이지네이션 검증 (Settings의 기본값 사용)
        page, page_size = self.validate_pagination(page, page_size)
        offset = self.calculate_offset(page, page_size)
        
        # API Key 목록 조회
        if active_only:
            api_keys = await ApiKey.list_active(
                session=self.session,
                limit=page_size,
                offset=offset
            )
            total_count = await ApiKey.count_active(self.session)
        else:
            api_keys = await ApiKey.list_all(
                session=self.session,
                limit=page_size,
                offset=offset
            )
            total_count = await ApiKey.count_all(self.session)
        
        # 응답 데이터 구성 (보안상 해시는 제외)
        api_key_list = []
        for api_key in api_keys:
            api_key_info = {
                "id": str(api_key.id),
                "name": api_key.name,
                "key_prefix": api_key.key_prefix,
                "is_active": api_key.is_active,
                "expires_at": api_key.expires_at,
                "last_used_at": api_key.last_used_at,
                "created_at": api_key.created_at,
                "updated_at": api_key.updated_at,
                "status": api_key.status,  # computed_field
                "is_expired": api_key.is_expired  # computed_field
            }
            api_key_list.append(api_key_info)
        
        result = {
            "api_keys": api_key_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size,
                "has_next": offset + page_size < total_count,
                "has_prev": page > 1
            }
        }
        
        self.log_info("API key list fetched successfully", count=len(api_keys), total=total_count)
        return result 