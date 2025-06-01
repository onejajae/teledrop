"""
파일 다운로드 Handler

Drop의 파일을 다운로드하는 비즈니스 로직을 처리합니다.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
from urllib.parse import quote

from sqlmodel import Session
from fastapi.responses import StreamingResponse

from app.models import Drop, File
from app.handlers.base import BaseHandler, FileMixin
from app.infrastructure.storage.base import StorageInterface
from app.core.config import Settings
from app.core.exceptions import (
    DropNotFoundError,
    DropFileNotFoundError,
)


@dataclass
class FileDownloadHandler(BaseHandler, FileMixin):
    """파일 다운로드 Handler"""
    
    session: Session
    storage_service: StorageInterface
    settings: Settings
    
    async def execute(
        self,
        drop_key: str,
        password: Optional[str] = None,
        auth_data: Optional[Dict[str, Any]] = None,
        as_attachment: bool = True
    ) -> Tuple[StreamingResponse, File]:
        """
        Drop의 파일을 다운로드합니다.
        
        Args:
            drop_key: Drop 키
            password: Drop 패스워드 (필요한 경우)
            auth_data: 인증 정보
            as_attachment: 첨부파일로 다운로드할지 여부
            
        Returns:
            Tuple[StreamingResponse, File]: 스트리밍 응답과 파일 정보
            
        Raises:
            DropNotFoundError: Drop을 찾을 수 없는 경우
            DropFileNotFoundError: 파일을 찾을 수 없는 경우
            DropAccessDeniedError: 접근 권한이 없는 경우
        """
        self.log_info("Downloading file", drop_key=drop_key)
        
        # Drop 조회
        drop = Drop.get_by_key(self.session, drop_key, include_file=True)
        if not drop:
            raise DropNotFoundError(f"Drop not found: {drop_key}")
        
        if not drop.file:
            raise DropFileNotFoundError(f"No file found for drop: {drop_key}")
        
        # 접근 권한 검증
        self.validate_drop_access(drop, auth_data)
        self.validate_drop_password(drop, password)
        
        # 비동기 파일 스트림 생성
        async_file_streamer = self.storage_service.read_file(drop.file.storage_path)
        
        # 응답 헤더 설정
        # RFC 6266에 따른 UTF-8 파일명 인코딩
        encoded_filename = quote(drop.file.original_filename)
        
        headers = {
            "Content-Length": str(drop.file.file_size),
            "Content-Type": drop.file.file_type,
        }
        
        if as_attachment:
            headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}"
        else:
            headers["Content-Disposition"] = f"inline; filename*=UTF-8''{encoded_filename}"
        
        # 스트리밍 응답 생성
        response = StreamingResponse(
            async_file_streamer, # 비동기 제너레이터 직접 전달
            media_type=drop.file.file_type,
            headers=headers
        )
        
        self.log_info("File download started", 
                     file_id=str(drop.file.id),
                     filename=drop.file.original_filename)
        
        return response, drop.file 