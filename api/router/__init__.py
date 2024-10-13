from fastapi import APIRouter

from api.router.auth import router as auth_router
from api.router.post import router as post_router

api_router = APIRouter()
api_router.include_router(auth_router, tags=["Auth"])
api_router.include_router(post_router, tags=["Post"])
