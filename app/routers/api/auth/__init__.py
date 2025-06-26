"""
인증 관련 API 라우터 모듈

각 인증 기능별로 분리된 라우터들을 통합하여 메인 라우터를 제공합니다.
"""

from fastapi import APIRouter

from .login import router as login_router
from .logout import router as logout_router
from .user import router as user_router


# 메인 auth 라우터 생성 (prefix는 상위에서 설정)
router = APIRouter()

# 각 기능별 라우터들을 메인 라우터에 포함
router.include_router(login_router)
router.include_router(logout_router)
router.include_router(user_router) 