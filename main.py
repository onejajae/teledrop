import os

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.db.init import init_db
from api.router import api_router
from api.config import get_settings


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.isdir(settings.SHARE_DIRECTORY):
        os.mkdir(settings.SHARE_DIRECTORY)
    if not os.path.exists(settings.SQLITE_HOST):
        init_db()

    yield

    # after app shutdown


def make_app() -> FastAPI:
    if settings.APP_MODE == "prod":
        app = FastAPI(
            lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None
        )
    else:
        print(settings)
        app = FastAPI(lifespan=lifespan)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    return app


app = make_app()
app.include_router(api_router, prefix=settings.PREFIX_API_BASE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/_app", StaticFiles(directory=settings.PATH_WEB_BUILD))
app.mount("/static", StaticFiles(directory=settings.PATH_WEB_STATIC))


@app.get("/{catchall:path}")
async def index(catchall: str):
    return FileResponse(settings.PATH_WEB_INDEX)
