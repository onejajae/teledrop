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
    handler_method
)

# All mixins
from .mixins import (
    LoggingMixin,
    ValidationMixin,
    TimestampMixin,
    PaginationMixin,

)

# Drop handlers
from .drop import (
    DropListHandler,
    DropReadHandler,
    DropCreateHandler,
    DropDeleteHandler,
    DropAccessHandler,
    DropStreamHandler
)

# File handlers (다운로드/스트리밍만 - 삭제는 DropDeleteHandler에서 처리)

# Auth handlers


__all__ = [
    # Base classes and mixins
    "BaseHandler",
    "LoggingMixin",
    "ValidationMixin",
    "TimestampMixin",
    "PaginationMixin",
    "handler_method",
    
    # Query mixins

    
    # Drop handlers (7개 - 파일 스트리밍 포함)
    "DropListHandler",
    "DropReadHandler",
    "DropCreateHandler",
    "DropUpdateHandler",
    "DropDeleteHandler",
    "DropAccessHandler",
    "DropStreamHandler",
    
    
] 