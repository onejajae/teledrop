from sqlmodel import SQLModel

from app.infrastructure.db.models import AuthApiKey, AuthSession, DropRecord


def init_db(db_engine):
    SQLModel.metadata.create_all(db_engine)
