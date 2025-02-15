from fastapi import APIRouter

from .auth_router import router as auth_router
from .content_router import router as content_router
from .api_key_router import router as api_key_router


api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(content_router, prefix="/content", tags=["Content"])
api_router.include_router(api_key_router, prefix="/apikey", tags=["API Key"])
