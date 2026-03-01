from fastapi import APIRouter

from app.interfaces.api.routers.auth import router as auth_router
from app.interfaces.api.routers.drop import router as drop_router


api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(drop_router)
