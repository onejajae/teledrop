from types import SimpleNamespace

from argon2 import PasswordHasher

from app.infrastructure.db.engine import create_db_engine
from app.infrastructure.db.schema import initialize_database_schema


def initialize_sqlite_db(sqlite_url: str):
    settings = SimpleNamespace(
        SQLITE_HOST=sqlite_url,
        WEB_USERNAME="admin",
        WEB_PASSWORD=PasswordHasher().hash("password"),
        BOOTSTRAP_ALLOW_INSECURE_DEFAULTS=True,
    )
    engine = create_db_engine(settings)
    try:
        initialize_database_schema(engine, settings)
    finally:
        engine.dispose()


__all__ = ["initialize_sqlite_db"]
