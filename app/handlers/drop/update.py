"""
Drop 수정 Handler

Drop의 메타데이터 수정 관련 비즈니스 로직을 처리합니다.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

from sqlmodel import Session

from app.models import Drop
from app.handlers.base import BaseHandler, TransactionMixin
from app.infrastructure.storage.base import StorageInterface
from app.models.drop import DropUpdate
from app.core.config import Settings
from app.core.exceptions import (
    DropNotFoundError,
    ValidationError,
)


@dataclass
class DropUpdateHandler(BaseHandler, TransactionMixin):
    """Drop 수정 Handler"""
    
    session: Session
    storage_service: StorageInterface
    settings: Settings
    
    def execute(
        self,
        drop_key: str,
        update_data: DropUpdate,
        auth_data: Optional[Dict[str, Any]] = None
    ) -> Drop:
        """
        Drop 정보를 수정합니다.
        
        Args:
            drop_key: Drop 키
            update_data: 수정할 데이터
            auth_data: 인증 정보 (라우터에서 이미 검증됨)
            
        Returns:
            Drop: 수정된 Drop
            
        Raises:
            DropNotFoundError: Drop을 찾을 수 없는 경우
            ValidationError: 수정 데이터가 유효하지 않은 경우
        """
        self.log_info("Updating drop", drop_key=drop_key)
        
        try:
            # Drop 조회 (라우터에서 이미 존재 여부 검증됨)
            drop = Drop.get_by_key(self.session, drop_key, include_file=False)
            if not drop:
                raise DropNotFoundError(f"Drop not found: {drop_key}")
            
            # 수정할 필드만 업데이트
            update_dict = update_data.model_dump(exclude_unset=True)
            
            # 수정 데이터 검증
            self._validate_update_data(update_dict)
            
            # 필드 업데이트
            for field, value in update_dict.items():
                setattr(drop, field, value)
            
            self.update_timestamps(drop)
            
            self.session.commit()
            self.session.refresh(drop)
            
            self.log_info("Drop updated successfully", drop_id=str(drop.id))
            return drop
            
        except Exception as e:
            self.session.rollback()
            self.log_error("Failed to update drop", error=str(e))
            raise
    
    def _validate_update_data(self, update_dict: Dict[str, Any]):
        """수정 데이터 검증"""
        if 'title' in update_dict and not self.validate_drop_title_length(update_dict['title']):
            raise ValidationError(f"Drop title exceeds maximum length ({self.settings.MAX_DROP_TITLE_LENGTH})")
        
        if 'description' in update_dict and update_dict['description'] and not self.validate_drop_description_length(update_dict['description']):
            raise ValidationError(f"Drop description exceeds maximum length ({self.settings.MAX_DROP_DESCRIPTION_LENGTH})") 