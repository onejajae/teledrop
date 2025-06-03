"""Router 패키지

FastAPI 라우터들을 제공합니다.
기존 api/routers와 동일한 구조로 구현되었습니다.
"""

from fastapi import APIRouter

# API 라우터들 직접 import
from app.routers.api.auth_router import router as auth_router
from app.routers.api.drop_router import router as drop_router
# from app.routers.api.api_key_router import router as api_key_router

# 메인 API 라우터 생성
api_router = APIRouter()

# 라우터들을 메인 라우터에 포함 (각 라우터가 이미 자체 prefix를 가지고 있음)
api_router.include_router(auth_router, tags=["Auth"])
api_router.include_router(drop_router, tags=["Content"])  # 기존 content와 호환
# api_router.include_router(api_key_router, tags=["API Keys"])

# 편의 함수들 (기존 코드와의 호환성을 위해 유지)
def get_api_routers():
    """모든 API 라우터를 반환합니다."""
    return [auth_router, drop_router]

def setup_api_routes(app, prefix="/api"):
    """FastAPI 앱에 메인 API 라우터를 등록합니다."""
    app.include_router(api_router, prefix=prefix)

def get_router_info():
    """라우터 정보를 반환합니다."""
    return {
        "auth_router": True,
        "drop_router": True,
        "api_key_router": True,
        "total_routers": 3
    } 