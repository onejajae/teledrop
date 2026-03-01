from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.bootstrap.runtime_paths import static_files_dir
from app.interfaces.api.router import api_router
from app.interfaces.web.router import router as web_router


def mount_static(app: FastAPI) -> None:
    app.mount("/static", StaticFiles(directory=str(static_files_dir())), name="static")


def register_routes(app: FastAPI, settings) -> None:
    app.include_router(api_router, prefix=settings.PREFIX_API_BASE)
    app.include_router(web_router)
