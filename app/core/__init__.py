"""
Core 레이어 - 애플리케이션의 핵심 설정 및 공통 기능

이 패키지는 다음을 포함합니다:
- config: 애플리케이션 설정
- exceptions: 커스텀 예외 클래스들
- dependencies: FastAPI 의존성 주입

사용 예시:
    from app.core.config import Settings
    from app.core.exceptions import DropNotFoundError
    from app.core.dependencies import get_session
"""

# 의존성 주입은 별도 패키지로 이동
# from app.dependencies import ... 