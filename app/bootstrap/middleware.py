from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def register_middlewares(app: FastAPI, settings) -> None:
    if settings.APP_MODE == "prod":
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
