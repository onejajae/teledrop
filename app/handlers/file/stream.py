"""
파일 스트리밍 Handler

Range 요청을 통한 파일 부분 다운로드 및 스트리밍 비즈니스 로직을 처리합니다.
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
class FileRangeHandler(BaseHandler, FileMixin):
    """파일 Range 요청 Handler (부분 다운로드/스트리밍)"""
    
    session: Session
    storage_service: StorageInterface
    settings: Settings
    
    async def execute(
        self,
        drop_key: str,
        range_header: Optional[str] = None,
        password: Optional[str] = None,
        auth_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[StreamingResponse, File]:
        """
        Drop의 파일을 Range 요청으로 다운로드합니다.
        
        Args:
            drop_key: Drop 키
            range_header: HTTP Range 헤더 값
            password: Drop 패스워드 (필요한 경우)
            auth_data: 인증 정보
            
        Returns:
            Tuple[StreamingResponse, File]: 스트리밍 응답과 파일 정보
            
        Raises:
            DropNotFoundError: Drop을 찾을 수 없는 경우
            DropFileNotFoundError: 파일을 찾을 수 없는 경우
            DropAccessDeniedError: 접근 권한이 없는 경우
        """
        self.log_info("Processing range request", drop_key=drop_key, range=range_header)
        
        # Drop 조회
        drop = Drop.get_by_key(self.session, drop_key, include_file=True)
        if not drop:
            raise DropNotFoundError(f"Drop not found: {drop_key}")
        
        if not drop.file:
            raise DropFileNotFoundError(f"No file found for drop: {drop_key}")
        
        # 접근 권한 검증
        self.validate_drop_access(drop, auth_data)
        self.validate_drop_password(drop, password)
        
        file_size = drop.file.file_size
        start = 0
        end = file_size - 1
        
        # Range 헤더 파싱 (Settings의 parse_range_header 메서드 사용)
        if range_header:
            start, end = self.parse_range_header(range_header, file_size)
        
        content_length = end - start + 1
        
        # 비동기 파일 스트림 생성 (Range 지원)
        async_file_streamer = self.storage_service.read_file_range(
            drop.file.storage_path, start, end
        )
        
        # 응답 헤더 설정
        # RFC 6266에 따른 UTF-8 파일명 인코딩
        encoded_filename = quote(drop.file.original_filename)
        
        headers = {
            "Content-Length": str(content_length),
            "Content-Type": drop.file.file_type,
            "Accept-Ranges": "bytes",
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}"
        }
        
        # 206 Partial Content 응답 생성
        status_code = 206 if range_header and (start > 0 or end < file_size - 1) else 200
        
        response = StreamingResponse(
            async_file_streamer, # 비동기 제너레이터 직접 전달
            status_code=status_code,
            media_type=drop.file.file_type,
            headers=headers
        )
        
        self.log_info("Range request processed", 
                     file_id=str(drop.file.id),
                     range=f"{start}-{end}/{file_size}")
        
        return response, drop.file 