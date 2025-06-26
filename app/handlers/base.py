"""Handler 기본 클래스

모든 Handler가 상속받을 기본 베이스 클래스를 제공합니다.
공통으로 필요한 기능들은 별도 믹스인으로 분리되어 있습니다.
"""

from sqlmodel import Session

from app.core.config import Settings
from app.handlers.mixins import LoggingMixin


class BaseHandler(LoggingMixin):
    """모든 Handler의 기본 베이스 클래스
    
    공통적으로 필요한 기능들을 제공합니다.
    추가적인 기능이 필요한 Handler는 다른 믹스인들을 상속받을 수 있습니다.
    
    Notes:
        - 트랜잭션 관리는 의존성 레벨에서 자동 처리됩니다.
        - 모델의 create/update/delete 메서드에서 명시적 commit을 수행합니다.
        - 예외 발생 시 의존성에서 자동 롤백이 처리됩니다.
    """
    
    settings: Settings  # Settings 주입 필수
    session: Session    # Session 주입 필수 (대부분의 핸들러에서 필요)


