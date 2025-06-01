"""
Drop 삭제 Handler

Drop과 연관된 파일을 함께 삭제하는 비즈니스 로직을 처리합니다.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

from sqlmodel import Session

from app.models import Drop
from app.handlers.base import BaseHandler, TransactionMixin
from app.infrastructure.storage.base import StorageInterface
from app.core.config import Settings
from app.core.exceptions import (
    DropNotFoundError,
)


@dataclass
class DropDeleteHandler(BaseHandler, TransactionMixin):
    """Drop 삭제 Handler"""
    
    session: Session
    storage_service: StorageInterface
    settings: Settings
    
    def execute(
        self,
        drop_key: str,
        auth_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Drop을 삭제합니다.
        
        Args:
            drop_key: Drop 키
            auth_data: 인증 정보 (라우터에서 이미 검증됨)
            
        Returns:
            bool: 삭제 성공 여부
            
        Raises:
            DropNotFoundError: Drop을 찾을 수 없는 경우
        """
        self.log_info("Deleting drop", drop_key=drop_key)
        
        try:
            # Drop 조회 (파일 정보 포함, 라우터에서 이미 존재 여부 검증됨)
            drop = Drop.get_by_key(self.session, drop_key, include_file=True)
            if not drop:
                raise DropNotFoundError(f"Drop not found: {drop_key}")
            
            # 연관된 파일 삭제 (모든 Drop은 반드시 file을 가지므로)
            self._delete_associated_file(drop)
            
            # 파일 레코드 삭제 (CASCADE로 Drop과 함께 삭제됨)
            self.session.delete(drop.file)
            
            # Drop 삭제
            self.session.delete(drop)
            self.session.commit()
            
            self.log_info("Drop deleted successfully", drop_key=drop_key)
            return True
            
        except Exception as e:
            self.session.rollback()
            self.log_error("Failed to delete drop", error=str(e))
            raise
    
    def _delete_associated_file(self, drop: Drop):
        """연관된 파일을 스토리지에서 삭제"""
        try:
            self.storage_service.delete_file_sync(drop.file.storage_path)
            self.log_info("File deleted from storage", path=drop.file.storage_path)
        except Exception as e:
            # 파일 삭제 실패는 경고로 처리 (DB 삭제는 계속 진행)
            self.log_warning("Failed to delete file from storage", 
                           path=drop.file.storage_path, error=str(e)) 