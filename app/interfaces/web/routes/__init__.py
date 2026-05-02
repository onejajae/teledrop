from fastapi import APIRouter

from app.interfaces.web.routes.actions_auth import router as auth_actions_router
from app.interfaces.web.routes.actions_drop import router as drop_actions_router
from app.interfaces.web.routes.files import router as files_router
from app.interfaces.web.routes.pages import router as pages_router


router = APIRouter()
router.include_router(files_router)
router.include_router(pages_router)
router.include_router(auth_actions_router)
router.include_router(drop_actions_router)
