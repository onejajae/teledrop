"""API Router 패키지

Handler 아키텍처를 사용하는 API 라우터들을 제공합니다.
각 라우터는 관련된 Handler들을 사용하여 비즈니스 로직을 처리합니다.

사용 예시:
    from app.routers.api.auth.login import router as login_router
    from app.routers.api.drop.create import router as create_router
"""

from .auth import router as auth_router
from .drop import router as drop_router 