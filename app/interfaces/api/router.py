from fastapi import APIRouter

from app.interfaces.api.routers.drop import router as drop_router


api_router = APIRouter()
api_router.include_router(drop_router)
