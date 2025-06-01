"""API Router 패키지

새로운 Handler 아키텍처를 사용하는 API 라우터들을 제공합니다.
각 라우터는 관련된 Handler들을 사용하여 비즈니스 로직을 처리합니다.

구조:
    app/routers/api/
    ├── __init__.py           # API 라우터 패키지 초기화
    ├── auth_router.py        # 인증 관련 API
    ├── drop_router.py        # Drop 관련 API (기존 content API 호환)
    ├── file_router.py        # 파일 관련 API
    └── api_key_router.py     # API Key 관리 API

사용 예시:
    from app.routers.api import auth_router, drop_router, file_router, api_key_router
    
    app = FastAPI()
    app.include_router(auth_router) # prefix는 라우터에서 설정됨
    app.include_router(drop_router)  
    app.include_router(file_router)
    app.include_router(api_key_router)
"""

import logging

logger = logging.getLogger(__name__)

# 라우터 임포트
try:
    from .auth_router import router as auth_router
    logger.info("Successfully imported auth_router")
except ImportError as e:
    logger.warning(f"Failed to import auth_router: {e}")
    auth_router = None

try:
    from .drop_router import router as drop_router
    logger.info("Successfully imported drop_router")
except ImportError as e:
    logger.warning(f"Failed to import drop_router: {e}")
    drop_router = None

try:
    from .api_key_router import router as api_key_router
    logger.info("Successfully imported api_key_router")
except ImportError as e:
    logger.warning(f"Failed to import api_key_router: {e}")
    api_key_router = None

# 성공적으로 임포트된 라우터들만 __all__에 포함
__all__ = []
if auth_router is not None:
    __all__.append("auth_router")
if drop_router is not None:
    __all__.append("drop_router")
if api_key_router is not None:
    __all__.append("api_key_router")


def get_all_api_routers():
    """모든 API 라우터를 반환합니다.
    
    Returns:
        list: 사용 가능한 모든 API 라우터들
    """
    routers = []
    
    if auth_router is not None:
        routers.append(auth_router)
    if drop_router is not None:
        routers.append(drop_router)
    if api_key_router is not None:
        routers.append(api_key_router)
    
    logger.info(f"Returning {len(routers)} API routers")
    return routers


def get_router_info():
    """라우터 정보를 반환합니다.
    
    Returns:
        dict: 라우터별 상태 정보
    """
    return {
        "auth_router": auth_router is not None,
        "drop_router": drop_router is not None,
        "api_key_router": api_key_router is not None,
        "total_routers": len(__all__)
    } 