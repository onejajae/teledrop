"""
Drop 삭제 Handler

Drop과 연관된 파일을 함께 삭제하는 비즈니스 로직을 처리합니다.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

from sqlmodel import Session
from fastapi import Depends

from app.models import Drop
from app.handlers.base import BaseHandler
from app.infrastructure.storage.base import StorageInterface
from app.core.config import Settings
from app.core.exceptions import DropNotFoundError
from app.core.dependencies import get_session, get_storage, get_settings


class DropDeleteHandler(BaseHandler):
    """Drop 삭제 Handler"""
    
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
    ) -> Dict[str, str]:
        """
        Drop을 삭제합니다.
        
        Args:
            slug: Drop 키
            auth_data: 인증 정보 (라우터에서 이미 검증됨)
            
        Returns:
            Dict[str, str]: 삭제 성공 메시지
            
        Raises:
            DropNotFoundError: Drop을 찾을 수 없는 경우
        """
        self.log_info("Deleting drop", slug=slug)
        
        try:
            # Drop 조회 (파일 정보 포함, 라우터에서 이미 존재 여부 검증됨)
            drop = Drop.get_by_slug(self.session, slug)
            if not drop:
                raise DropNotFoundError(f"Drop not found: {slug}")
            
            # 스토리지에서 파일 삭제
            try:
                self.storage.delete_file_sync(drop.storage_path)
                self.log_info("File deleted from storage", path=drop.storage_path)
            except Exception as e:
                # 파일 삭제 실패는 경고로 처리 (DB 삭제는 계속 진행)
                self.log_warning("Failed to delete file from storage", 
                               path=drop.storage_path, error=str(e))
            
            # Drop을 데이터베이스에서 삭제 (통합된 모델이므로 파일 정보도 함께 삭제됨)
            drop.delete(self.session)
            
            self.log_info("Drop deleted successfully", slug=slug)
            return {
                "message": "Drop deleted successfully",
                "deleted_slug": slug
            }
            
        except Exception as e:
            # 의존성에서 자동 롤백 처리됨
            self.log_error("Failed to delete drop", error=str(e))
            raise 