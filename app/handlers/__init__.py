"""Handler 레이어 패키지

비즈니스 로직을 담당하는 Handler들을 제공합니다.
각 Handler는 단일 책임 원칙을 따르며, 의존성 주입을 통해 테스트 가능한 설계를 제공합니다.

사용 예시:
    from app.handlers.drop.create import DropCreateHandler
    from app.handlers.auth.login import LoginHandler
    from app.handlers.base import BaseHandler
    from app.handlers.mixins.logging import LoggingMixin
    
    # Handler 인스턴스 생성 (의존성 주입)
    login_handler = LoginHandler(session=session, settings=settings)
    result = await login_handler.execute(username="admin", password="password")
"""

# 모든 imports는 직접 import 방식 사용
# 예: from app.handlers.drop.create import DropCreateHandler 