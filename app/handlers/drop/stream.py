"""
Drop 파일 스트리밍 Handler

Drop의 파일 전체 다운로드 및 Range 요청을 통한 파일 부분 다운로드에 대한 비즈니스 로직을 처리합니다.
통합된 Drop 모델에서 파일 스트리밍 기능을 담당합니다.
"""

from typing import Optional, Dict, Any, Tuple, AsyncGenerator

from sqlmodel import Session
from fastapi import Depends

from app.core.config import Settings
from app.models import Drop
from app.handlers.base import BaseHandler
from app.handlers.mixins import ValidationMixin
from app.infrastructure.storage.base import StorageInterface
from app.core.exceptions import DropNotFoundError

from app.core.dependencies import get_session, get_storage, get_settings


class DropStreamHandler(BaseHandler, ValidationMixin):
    """Range와 전체 다운로드를 모두 지원하는 통합 Drop 파일 스트리밍 핸들러"""
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
        slug: str,
        start: int = 0,
        end: Optional[int] = None,
        password: Optional[str] = None,
        auth_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[AsyncGenerator[bytes, None], int, int, int, Dict[str, str]]:
        """
        Range와 전체 다운로드를 모두 지원하는 Drop 파일 스트리밍
        Returns:
            Tuple[AsyncGenerator[bytes, None], int, int, int, Dict[str, str]]:
                (비동기 파일 제너레이터, 시작 바이트, 종료 바이트, 파일 크기, 파일 메타데이터)
        """
        self.log_info("Drop file stream request", slug=slug, start=start, end=end)
        
        # Drop 조회 (통합된 모델에서 파일 정보 포함)
        drop = Drop.get_by_slug(self.session, slug)
        if not drop:
            raise DropNotFoundError(f"Drop not found: {slug}")
        
        # 접근 권한 검증
        self.validate_drop_access(drop, auth_data)
        self.validate_drop_password(drop, password)
        
        # 파일 크기 확인
        file_size = drop.file_size

        if end is None:
            # Range 헤더가 없는 경우 (전체 파일 다운로드)
            end = file_size - 1
        else:
            # Range 헤더가 있는 경우 (라우터에서 이미 4MB 제한 적용됨)
            # end 값이 파일 크기를 초과하지 않도록 보정만 수행
            end = min(end, file_size - 1)

        # 비동기 파일 스트림 생성 (Range 지원)
        async_file_streamer = self.storage.read_file_range(
            drop.storage_path, start, end
        )

        # 파일 메타데이터 구성
        file_metadata = {
            "filename": drop.file_name,
            "content_type": drop.file_type,
            "file_hash": drop.file_hash
        }

        self.log_info("Drop file stream ready", drop_id=drop.id, range=f"{start}-{end}/{file_size}")
        return async_file_streamer, start, end, file_size, file_metadata 