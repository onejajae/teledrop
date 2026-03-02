from fastapi import FastAPI

from app.bootstrap.lifespan import build_lifespan
from app.bootstrap.middleware import register_middlewares
from app.bootstrap.routing import mount_static, register_routes
from app.core.config import Settings


def create_app_from_settings(settings: Settings) -> FastAPI:
    settings.validate_auth_configuration()

    docs_url = "/docs" if settings.API_DOCS_ENABLED else None
    redoc_url = "/redoc" if settings.API_DOCS_ENABLED else None
    openapi_url = "/openapi.json" if settings.API_DOCS_ENABLED else None

    app = FastAPI(
        lifespan=build_lifespan(settings),
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    register_middlewares(app, settings)
    mount_static(app)
    register_routes(app, settings)

    return app
