from importlib import import_module

__all__ = ["get_session", "init_db"]


def __getattr__(name: str):
    if name == "get_session":
        return import_module("app.infrastructure.db.session").get_session
    if name == "init_db":
        return import_module("app.infrastructure.db.init").init_db
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
