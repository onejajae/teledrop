"""Handler 기본 클래스와 믹스인들

모든 Handler가 공통으로 사용하는 기능들을 제공합니다.
믹스인 패턴을 사용하여 필요한 기능만 조합할 수 있습니다.
"""

import logging
from typing import Optional, TypeVar
from datetime import datetime, timezone
from pathlib import Path
import re

from sqlmodel import Session, SQLModel

from app.core.config import Settings
from app.core.exceptions import DropAccessDeniedError, DropPasswordInvalidError, FileSizeExceededError

T = TypeVar('T', bound=SQLModel)

class LoggingMixin:
    """로깅 기능을 제공하는 믹스인"""
    
    settings: Settings  # Settings 주입 필요
    
    @property
    def logger(self) -> logging.Logger:
        """클래스 이름을 기반으로 한 로거를 반환합니다."""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(self.__class__.__name__)
            # Settings에서 로그 레벨 설정
            if hasattr(self, 'settings'):
                self._logger.setLevel(getattr(logging, self.settings.LOG_LEVEL, "INFO"))
        return self._logger
    
    def log_info(self, message: str, **kwargs):
        """정보 수준 로그를 기록합니다."""
        if not getattr(self.settings, 'ENABLE_HANDLER_LOGGING', True):
            return
        extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
        full_message = f"{message} {extra_info}".strip()
        self.logger.info(full_message)
    
    def log_error(self, message: str, **kwargs):
        """에러 수준 로그를 기록합니다."""
        if not getattr(self.settings, 'ENABLE_HANDLER_LOGGING', True):
            return
        extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
        full_message = f"{message} {extra_info}".strip()
        self.logger.error(full_message)
    
    def log_warning(self, message: str, **kwargs):
        """경고 수준 로그를 기록합니다."""
        if not getattr(self.settings, 'ENABLE_HANDLER_LOGGING', True):
            return
        extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
        full_message = f"{message} {extra_info}".strip()
        self.logger.warning(full_message)


class ValidationMixin:
    """검증 기능을 제공하는 믹스인"""
    
    settings: Settings  # Settings 주입 필요
    
    def validate_drop_password(self, drop, password: Optional[str] = None):
        """Drop 패스워드를 검증합니다."""
        if not self.settings.ENABLE_PASSWORD_PROTECTION:
            return
        if drop.password and drop.password != password:
            raise DropPasswordInvalidError("Invalid password for drop")
    
    def validate_drop_access(self, drop, auth_data=None):
        """Drop 접근 권한을 검증합니다."""
        if drop.user_only and not auth_data:
            if self.settings.REQUIRE_AUTH_FOR_SENSITIVE_OPS:
                raise DropAccessDeniedError("Authentication required for user-only drop")
    
    def validate_api_key_format(self, api_key: str) -> bool:
        """API Key 형식을 검증합니다."""
        if not api_key or len(api_key) < self.settings.API_KEY_LENGTH:
            return False
        
        # "tk_" 접두사 확인
        if not api_key.startswith("tk_"):
            return False
        
        # 접두사 이후 부분이 hex 문자인지 확인
        hex_part = api_key[3:]  # "tk_" 이후 부분
        pattern = r'^[a-f0-9]+$'
        return bool(re.match(pattern, hex_part))
    
    def validate_file_size(self, file_size: int, max_size: Optional[int] = None) -> bool:
        """파일 크기를 검증합니다."""
        max_size = max_size or self.settings.MAX_FILE_SIZE
        if file_size > max_size:
            raise FileSizeExceededError(f"File size {file_size} exceeds maximum {max_size}")
        return 0 < file_size <= max_size
    
    def validate_file_extension(self, filename: str) -> bool:
        """파일 확장자를 검증합니다."""
        if not self.settings.ALLOWED_FILE_EXTENSIONS:
            return True  # 모든 확장자 허용
        
        allowed_extensions = [ext.strip().lower() for ext in self.settings.ALLOWED_FILE_EXTENSIONS.split(',')]
        file_extension = Path(filename).suffix.lower().lstrip('.')
        return file_extension in allowed_extensions
    
    def validate_drop_title_length(self, title: str) -> bool:
        """Drop 제목 길이를 검증합니다."""
        return len(title) <= self.settings.MAX_DROP_TITLE_LENGTH
    
    def validate_drop_description_length(self, description: Optional[str]) -> bool:
        """Drop 설명 길이를 검증합니다."""
        if not description:
            return True
        return len(description) <= self.settings.MAX_DROP_DESCRIPTION_LENGTH


# class HashingMixin:
#     """해시 관련 기능을 제공하는 믹스인"""
    
#     def calculate_file_hash(self, content: bytes) -> str:
#         """파일 내용의 SHA256 해시를 계산합니다."""
#         return hashlib.sha256(content).hexdigest()
    
#     def generate_file_path(self, identifier: str, extension: Optional[str] = None) -> str:
#         """식별자(해시 또는 UUID)를 기반으로 저장 경로를 생성합니다.
#         확장자가 제공되면 파일명에 포함됩니다.
#         파일은 스토리지 루트에 바로 저장됩니다 (하위 디렉토리 없음).
#         """
#         # 확장자가 있으면 파일명에 추가
#         filename = f"{identifier}.{extension}" if extension else identifier
#         return filename


class TimestampMixin:
    """타임스탬프 관련 기능을 제공하는 믹스인"""
    
    def get_current_timestamp(self) -> datetime:
        """현재 UTC 타임스탬프를 반환합니다."""
        return datetime.now(timezone.utc)
    
    def update_timestamps(self, model, update_created: bool = False):
        """모델의 타임스탬프를 업데이트합니다."""
        now = self.get_current_timestamp()
        
        if update_created and hasattr(model, 'created_at'):
            model.created_at = now
            
        if hasattr(model, 'updated_at'):
            model.updated_at = now


class TransactionMixin:
    """트랜잭션 관련 기능을 제공하는 믹스인"""
    
    session: Session  # 세션 주입 필요
    
    def execute_in_transaction(self, operation_func, *args, **kwargs):
        """트랜잭션 내에서 작업을 실행합니다.
        
        Args:
            operation_func: 실행할 함수
            *args: 함수에 전달할 위치 인수
            **kwargs: 함수에 전달할 키워드 인수
            
        Returns:
            함수 실행 결과
            
        Example:
            def create_drop_with_file(drop_data, file_data):
                # 데이터베이스 작업
                return result
                
            result = self.execute_in_transaction(
                create_drop_with_file, 
                drop_data, 
                file_data=file_content
            )
        """
        try:
            self.session.begin()
            result = operation_func(*args, **kwargs)
            self.session.commit()
            return result
        except Exception:
            self.session.rollback()
            raise
    
    async def execute_in_transaction_async(self, operation_func, *args, **kwargs):
        """비동기 트랜잭션 내에서 작업을 실행합니다.
        
        Args:
            operation_func: 실행할 async 함수
            *args: 함수에 전달할 위치 인수
            **kwargs: 함수에 전달할 키워드 인수
            
        Returns:
            함수 실행 결과
            
        Example:
            async def create_drop_with_file_async(drop_data, file_data):
                # 비동기 데이터베이스 작업
                return result
                
            result = await self.execute_in_transaction_async(
                create_drop_with_file_async, 
                drop_data, 
                file_data=file_content
            )
        """
        try:
            self.session.begin()
            result = await operation_func(*args, **kwargs)
            self.session.commit()
            return result
        except Exception:
            self.session.rollback()
            raise
    
    def rollback_on_error(self, operation_func, error_message: str = "Operation failed", *args, **kwargs):
        """에러 발생 시 롤백을 수행합니다.
        
        Args:
            operation_func: 실행할 함수
            error_message: 에러 로그 메시지
            *args: 함수에 전달할 위치 인수
            **kwargs: 함수에 전달할 키워드 인수
            
        Returns:
            함수 실행 결과
        """
        try:
            result = operation_func(*args, **kwargs)
            return result
        except Exception as e:
            self.session.rollback()
            if hasattr(self, 'log_error'):
                self.log_error(error_message, error=str(e))
            raise
    
    async def rollback_on_error_async(self, operation_func, error_message: str = "Operation failed", *args, **kwargs):
        """비동기 함수에서 에러 발생 시 롤백을 수행합니다."""
        try:
            result = await operation_func(*args, **kwargs)
            return result
        except Exception as e:
            self.session.rollback()
            if hasattr(self, 'log_error'):
                self.log_error(error_message, error=str(e))
            raise


class PaginationMixin:
    """페이지네이션 기능을 제공하는 믹스인"""
    
    settings: Settings  # Settings 주입 필요
    
    def calculate_offset(self, page: int, page_size: int) -> int:
        """페이지 번호와 크기로 오프셋을 계산합니다."""
        return (page - 1) * page_size
    
    def validate_pagination(self, page: int, page_size: Optional[int] = None) -> tuple[int, int]:
        """페이지네이션 파라미터를 검증하고 정규화합니다."""
        page = max(1, page)
        
        # page_size가 제공되지 않으면 기본값 사용
        if page_size is None:
            page_size = self.settings.DEFAULT_PAGE_SIZE
        
        # 최대 페이지 크기 제한
        page_size = max(1, min(page_size, self.settings.MAX_PAGE_SIZE))
        return page, page_size


# class FileMixin:
#     """파일 관련 기능을 제공하는 믹스인"""
    
#     settings: Settings  # Settings 주입 필요
    
#     def file_streamer(self, file_stream, chunk_size: Optional[int] = None):
#         """파일 스트림을 청크 단위로 읽어서 제공합니다."""
#         chunk_size = chunk_size or self.settings.CHUNK_SIZE
#         try:
#             while True:
#                 chunk = file_stream.read(chunk_size)
#                 if not chunk:
#                     break
#                 yield chunk
#         finally:
#             if hasattr(file_stream, 'close'):
#                 file_stream.close()
    
#     def parse_range_header(self, range_header: str, file_size: int) -> tuple[int, int]:
#         """HTTP Range 헤더를 파싱합니다."""
#         try:
#             # "bytes=start-end" 형식에서 start, end 추출
#             range_spec = range_header.replace('bytes=', '')
#             parts = range_spec.split('-')
            
#             start = int(parts[0]) if parts[0] else 0
#             end = int(parts[1]) if parts[1] else file_size - 1
            
#             # 범위 검증
#             start = max(0, min(start, file_size - 1))
#             end = max(start, min(end, file_size - 1))
            
#             return start, end
#         except (ValueError, IndexError):
#             # 잘못된 Range 헤더인 경우 전체 파일 반환
#             return 0, file_size - 1


class BaseHandler(LoggingMixin, ValidationMixin, TimestampMixin):
    """모든 Handler의 기본 베이스 클래스
    
    공통적으로 필요한 기능들을 제공합니다.
    추가적인 기능이 필요한 Handler는 다른 믹스인들을 상속받을 수 있습니다.
    """
    
    settings: Settings  # Settings 주입 필수


# Handler 데코레이터 (선택적)
def handler_method(operation_name: str):
    """Handler 메서드를 위한 데코레이터"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            if hasattr(self, 'log_info'):
                self.log_info(f"Starting {operation_name}")
            try:
                result = func(self, *args, **kwargs)
                if hasattr(self, 'log_info'):
                    self.log_info(f"Completed {operation_name}")
                return result
            except Exception as e:
                if hasattr(self, 'log_error'):
                    self.log_error(f"Failed {operation_name}", error=str(e))
                raise
        return wrapper
    return decorator 