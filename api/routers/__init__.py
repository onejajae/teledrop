from fastapi import APIRouter
from api.routers.user_router import router as user_router
from api.routers.post_router import router as post_router

api_router = APIRouter()
api_router.include_router(user_router, tags=["Auth"])
api_router.include_router(post_router, tags=["Post"])
