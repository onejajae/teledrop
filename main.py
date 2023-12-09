from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from app.file.router import router as file_router
from api.router import router as api_router

from config import Settings, get_settings


def init_db(settings: Settings):
    from sqlalchemy import create_engine
    from db.model import Base

    engine = create_engine(settings.db_host, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)


def make_app(settings: Settings) -> FastAPI:
    import os

    if not os.path.exists(settings.db_host):
        init_db(settings)
    if not os.path.isdir(settings.share_directory):
        os.mkdir(settings.share_directory)

    if settings.app_mode == "prod":
        app = FastAPI(docs_url=None, redoc_url=None)
    else:
        app = FastAPI()

    return app


settings = get_settings()
app = make_app(settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")
