"""Handler 레이어 패키지

비즈니스 로직을 담당하는 Handler들을 제공합니다.
각 Handler는 단일 책임 원칙을 따르며, 의존성 주입을 통해 테스트 가능한 설계를 제공합니다.

사용 예시:
    from app.handlers.drop import DropListHandler, DropCreateHandler
    from app.handlers.file import FileDownloadHandler
    from app.handlers.api_key_handlers import ApiKeyCreateHandler
    from app.handlers.auth_handlers import LoginHandler, TokenValidateHandler
    
    # Handler 인스턴스 생성 (의존성 주입)
    login_handler = LoginHandler(session=session, settings=settings)
    result = await login_handler.execute(username="admin", password="password")
"""

from .base import (
    BaseHandler,
    LoggingMixin,
    ValidationMixin, 
    TimestampMixin,
    TransactionMixin,
    PaginationMixin,
    handler_method
)

# Drop handlers
from .drop import (
    DropListHandler,
    DropDetailHandler,
    DropCreateHandler,
    DropUpdateHandler,
    DropDeleteHandler,
    DropAccessHandler
)

# File handlers (다운로드/스트리밍만 - 삭제는 DropDeleteHandler에서 처리)

from .file.stream import FileStreamHandler


# Auth handlers


__all__ = [
    # Base classes and mixins
    "BaseHandler",
    "LoggingMixin",
    "ValidationMixin",
    "TimestampMixin",
    "TransactionMixin",
    "PaginationMixin",
    "handler_method",
    
    # Drop handlers (6개)
    "DropListHandler",
    "DropDetailHandler",
    "DropCreateHandler",
    "DropUpdateHandler",
    "DropDeleteHandler",
    "DropAccessHandler",
    
    # File handlers (2개 - 다운로드/스트리밍만)
    "FileStreamHandler",
    
    
] 