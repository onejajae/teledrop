"""
Drop 관련 API 라우터 모듈

각 Drop 기능별로 분리된 라우터들을 통합하여 메인 라우터를 제공합니다.
"""

from fastapi import APIRouter

from .list import router as list_router
from .create import router as create_router
from .read import router as read_router
from .update import router as update_router
from .delete import router as delete_router
from .keycheck import router as keycheck_router


# 메인 drop 라우터 생성 (prefix는 상위에서 설정)
router = APIRouter()

# 각 기능별 라우터들을 메인 라우터에 포함
router.include_router(list_router)        # GET /
router.include_router(create_router)      # POST /
router.include_router(read_router)        # GET /{slug}/preview, GET /{slug}
router.include_router(update_router)      # PATCH /{slug}/detail, /permission, /password, /reset, /favorite
router.include_router(delete_router)      # DELETE /{slug}
router.include_router(keycheck_router)    # GET /keycheck/{slug}


__all__ = [
    "router",
    "list_router",
    "create_router",
    "read_router",
    "update_router",
    "delete_router",
    "keycheck_router"
] 