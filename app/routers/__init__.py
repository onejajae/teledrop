"""Router 패키지

FastAPI 라우터들을 제공합니다.
"""

from fastapi import APIRouter

from app.routers.api.auth import router as auth_router
from app.routers.api.drop import router as drop_router

# 메인 API 라우터 생성
api_router = APIRouter()

# 라우터들을 메인 라우터에 포함 (prefix를 여기서 중앙집중 관리)
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(drop_router, prefix="/content", tags=["Content"])

__all__ = [
    "api_router",
    "auth_router",
    "drop_router"
] 