"""
Drop 읽기 관련 Handler들

Drop의 조회, 미리보기, 존재 여부 확인 등의 읽기 관련 비즈니스 로직을 처리합니다.
"""

from typing import AsyncGenerator

from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Depends

from app.models import Drop
from app.handlers.base import BaseHandler
from app.handlers.mixins import DropAccessMixin, LoggingMixin
from app.handlers.decorators import authenticate
from app.infrastructure.storage.base import StorageInterface
from app.models.drop.response import DropRead
from app.core.dependencies import get_session, get_storage, get_settings
from app.models.auth import AuthData
from app.core.config import Settings
from app.core.exceptions import DropNotFoundError, InvalidRangeHeaderError, RangeNotSatisfiableError
from app.utils.range_header import parse_range_header


class DropReadHandler(BaseHandler, DropAccessMixin, LoggingMixin):
    """Drop 읽기 Handler"""

    def __init__(
        self,
        session: AsyncSession = Depends(get_session),    
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage = storage
        self.settings = settings
    
    async def execute(
        self,
        slug: str,
        password: str | None = None,
        auth_data: AuthData | None = None
    ) -> Drop:
        """
        Drop 상세 정보를 조회합니다.
        
        Args:
            slug: Drop 키
            password: Drop 패스워드 (필요한 경우)
            auth_data: 인증 정보
            
        Returns:
            Drop: Drop 상세 정보
            
        Raises:
            DropNotFoundError: Drop을 찾을 수 없는 경우
            DropPasswordInvalidError: 패스워드가 틀린 경우
            DropAccessDeniedError: 접근 권한이 없는 경우
        """
        self.log_info("Fetching drop detail", slug=slug)
        
        # Drop 조회
        drop = await Drop.get_by_slug(self.session, slug)
        if not drop:
            raise DropNotFoundError(f"Drop not found: {slug}")
        
        # 접근 권한 검증 (DropAccessMixin 사용)
        self.validate_drop_access(drop, auth_data, password)
        
        self.log_info("Drop detail fetched successfully", drop_id=str(drop.id))
        return drop
    
    @authenticate(required=False)
    async def execute_preview(
        self,
        slug: str,
        password: str | None = None,
        auth_data: AuthData | None = None
    ) -> DropRead:
        """
        Drop 미리보기 정보를 조회합니다.
        
        @authenticate(required=False) 데코레이터에 의해 auth_data가 자동으로 처리됩니다.
        비공개 Drop은 인증이 필요하고, 패스워드가 있는 Drop은 패스워드가 필요합니다.
        
        Args:
            slug: Drop 키
            password: Drop 패스워드 (필요한 경우)
            auth_data: 인증 정보 (데코레이터에 의해 처리됨)
            
        Returns:
            DropRead: Drop 미리보기 정보
            
        Raises:
            DropNotFoundError: Drop을 찾을 수 없는 경우
            DropPasswordInvalidError: 패스워드가 틀린 경우
        """
        self.log_info("Fetching drop preview", slug=slug, authenticated=bool(auth_data))
        
        # Drop 조회
        drop = await Drop.get_by_slug(self.session, slug)
        if not drop:
            raise DropNotFoundError(f"Drop not found: {slug}")
        
        # 접근 권한 검증 (DropAccessMixin 사용)
        self.validate_drop_access(drop, auth_data, password)
        
        # DropRead 스키마로 변환
        preview = DropRead.model_validate(drop)
        
        self.log_info("Drop preview fetched successfully", drop_id=str(drop.id))
        return preview



class DropStreamHandler(BaseHandler, DropAccessMixin, LoggingMixin):
    """Range와 전체 다운로드를 모두 지원하는 통합 Drop 파일 스트리밍 핸들러"""
    def __init__(
        self,
        session: AsyncSession = Depends(get_session),    
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage = storage
        self.settings = settings

    @authenticate(required=False)  # 선택적 인증
    async def execute(
        self,
        slug: str,
        range_header: str | None = None,
        password: str | None = None,
        auth_data: AuthData | None = None,
    ) -> tuple[AsyncGenerator[bytes, None], int, int, DropRead]:
        """
        Range와 전체 다운로드를 모두 지원하는 Drop 파일 스트리밍
        
        @authenticate(required=False)로 선택적 인증을 처리합니다.
        Public Drop은 인증 없이, Private Drop은 인증 필요한 복잡한 접근 제어를 구현합니다.
        
        Args:
            slug: Drop 슬러그
            range_header: HTTP Range 헤더 값 (예: "bytes=0-1023")
            password: Drop 패스워드
            auth_data: 인증 데이터 (선택적)
            
        Returns:
            tuple[AsyncGenerator[bytes, None], int, int, DropRead]:
                (비동기 파일 제너레이터, 시작 바이트, 종료 바이트, DropRead)
        """
        self.log_info("Drop file stream request", slug=slug, range_header=range_header, authenticated=bool(auth_data))
        
        # Drop 조회 (통합된 모델에서 파일 정보 포함)
        drop = await Drop.get_by_slug(self.session, slug)
        if not drop:
            raise DropNotFoundError(f"Drop not found: {slug}")
        
        # 접근 권한 검증 (DropAccessMixin 사용)
        self.validate_drop_access(drop, auth_data, password)
        
        # 파일 크기 확인
        file_size = drop.file_size

        # Range 헤더 파싱 및 처리
        start, end = self._parse_and_validate_range(range_header, file_size)

        # 비동기 파일 스트림 생성 (Range 지원)
        async_file_streamer = self.storage.read(
            drop.storage_path, start, end
        )

        drop_result = DropRead.model_validate(drop)

        self.log_info("Drop file stream ready", drop_id=drop.id, range=f"{start}-{end}/{file_size}")
        return async_file_streamer, start, end, drop_result
    
    def _parse_and_validate_range(self, range_header: str | None, file_size: int) -> tuple[int, int]:
        """
        Range 헤더를 파싱하고 검증하여 start, end 바이트 위치를 반환합니다.
        
        Args:
            range_header: HTTP Range 헤더 값
            file_size: 파일 크기
            
        Returns:
            Tuple[int, int]: (시작 바이트, 종료 바이트)
            
        Raises:
            InvalidRangeHeaderError: Range 헤더가 유효하지 않은 경우
        """
        if not range_header:
            # Range 헤더가 없는 경우 전체 파일
            return 0, file_size - 1
        
        try:
            # Range 헤더 파싱
            start, end = parse_range_header(range_header)
            
            # suffix-byte-range-spec 처리 (예: "bytes=-500")
            if range_header.strip().lower().startswith("bytes=-"):
                # 마지막 N 바이트 요청
                suffix_length = end + 1  # parse_range_header에서 suffix_length-1을 반환하므로
                actual_start = max(0, file_size - suffix_length)
                actual_end = file_size - 1
                return actual_start, actual_end
            
            # 시작 위치 검증
            if start >= file_size:
                raise RangeNotSatisfiableError(f"Range not satisfiable: start={start}, file_size={file_size}")
            
            # 종료 위치 처리
            if end is None:
                # end가 없는 경우 (예: "bytes=1000-") 4MB 청크로 제한
                end = min(start + self.settings.STREAM_CHUNK_SIZE - 1, file_size - 1)
            else:
                # end가 파일 크기를 초과하지 않도록 보정
                end = min(end, file_size - 1)
            
            # 범위 유효성 검증
            if start > end:
                raise RangeNotSatisfiableError(f"Range not satisfiable: start={start}, end={end}")
            
            return start, end
            
        except ValueError:
            raise InvalidRangeHeaderError(f"Invalid Range header: {range_header}")
        except Exception as e:
            self.log_error("Range header parsing failed", error=str(e), range_header=range_header)
            raise InvalidRangeHeaderError(f"Invalid Range header: {range_header}") 



class DropExistsHandler(BaseHandler, LoggingMixin):
    """Drop 존재 여부 확인 핸들러"""
    
    def __init__(
        self,
        session: AsyncSession = Depends(get_session),    
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage = storage
        self.settings = settings
    
    @authenticate  # 인증 필수
    async def execute(self, slug: str, auth_data: AuthData | None = None) -> bool:
        """
        Drop의 존재 여부를 확인합니다.
        
        관리자만 사용할 수 있는 기능으로 인증이 필요합니다.
        @authenticate 데코레이터에 의해 auth_data가 자동으로 검증됩니다.
        
        Args:
            slug: Drop 슬러그
            auth_data: 인증 데이터 (데코레이터에 의해 보장됨)
            
        Returns:
            bool: Drop 존재 여부
        """
        self.log_info("Checking drop existence", slug=slug, user=auth_data.username)
        
        try:
            # Drop 존재 여부 확인
            drop = await Drop.get_by_slug(self.session, slug)
            exists = drop is not None
            
            self.log_info("Drop existence check completed", slug=slug, exists=exists)
            return exists
            
        except Exception as e:
            self.log_error("Drop existence check failed", slug=slug, error=str(e))
            raise 