"""
파일 읽기 Handler

파일 전체 다운로드 및 Range 요청을 통한 파일 부분 다운로드에 대한 비즈니스 로직을 처리합니다.
"""

from typing import Optional, Dict, Any, Tuple, AsyncGenerator

from sqlmodel import Session
from fastapi import Depends

from app.core.config import Settings
from app.models import Drop, File
from app.handlers.base import BaseHandler
from app.infrastructure.storage.base import StorageInterface
from app.core.exceptions import DropNotFoundError, DropFileNotFoundError

from app.core.dependencies import get_session, get_storage, get_settings


class FileStreamHandler(BaseHandler):
    """Range와 전체 다운로드를 모두 지원하는 통합 파일 스트리밍 핸들러"""
    def __init__(
        self,
        session: Session = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage = storage
        self.settings = settings

    async def execute(
        self,
        drop_key: str,
        start: int = 0,
        end: Optional[int] = None,
        password: Optional[str] = None,
        auth_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[AsyncGenerator[bytes, None], File, int, int, int]:
        """
        Range와 전체 다운로드를 모두 지원하는 파일 스트리밍
        Returns:
            Tuple[AsyncGenerator[bytes, None], File, int, int, int]:
                (비동기 파일 제너레이터, 파일 정보, 시작 바이트, 종료 바이트, 파일 크기)
        """
        self.log_info("Unified file stream request", drop_key=drop_key, start=start, end=end)
        
        # Drop 조회
        drop = Drop.get_by_key(self.session, drop_key)
        if not drop:
            raise DropNotFoundError(f"Drop not found: {drop_key}")
        if not drop.file:
            raise DropFileNotFoundError(f"No file found for drop: {drop_key}")
        
        # 접근 권한 검증
        self.validate_drop_access(drop, auth_data)
        self.validate_drop_password(drop, password)
        
        # end 값이 없으면 파일 전체 크기로 설정
        file_size = drop.file.file_size

        if end is None:
            end = file_size - 1

        # end 값이 파일 크기를 초과하지 않도록 보정
        end = min(end, file_size - 1)

        # 비동기 파일 스트림 생성 (Range 지원)
        async_file_streamer = self.storage.read_file_range(
            drop.file.storage_path, start, end
        )

        self.log_info("Unified file stream ready", file_id=str(drop.file.id), range=f"{start}-{end}/{file_size}")
        return async_file_streamer, drop.file, start, end, file_size 