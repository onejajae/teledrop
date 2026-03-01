from fastapi import FastAPI

from app.bootstrap.lifespan import build_lifespan
from app.bootstrap.middleware import register_middlewares
from app.bootstrap.routing import mount_static, register_routes
from app.core.config import Settings


def create_app_from_settings(settings: Settings) -> FastAPI:
    settings.validate_auth_configuration()

    if settings.APP_MODE == "prod":
        app = FastAPI(
            lifespan=build_lifespan(settings),
            docs_url=None,
            redoc_url=None,
            openapi_url=None,
        )
    else:
        app = FastAPI(lifespan=build_lifespan(settings))

    register_middlewares(app, settings)
    mount_static(app)
    register_routes(app, settings)

    return app
