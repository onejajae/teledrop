from fastapi import APIRouter

from .auth.router import router as auth_router
from .common.router import router as common_router
from .delete.router import router as delete_router
from .download.router import router as download_router
from .upload.router import router as upload_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(common_router, tags=["Commons"])
router.include_router(delete_router, tags=["Delete"])
router.include_router(download_router, tags=["Download"])
router.include_router(upload_router, tags=["Upload"])
