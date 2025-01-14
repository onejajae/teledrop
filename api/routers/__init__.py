from fastapi import APIRouter

from api.routers.auth_router import router as auth_router
from api.routers.content_router import router as content_router


api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(content_router, prefix="/content", tags=["Content"])
