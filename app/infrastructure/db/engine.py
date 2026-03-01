from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine

from app.core.config import Settings


def create_db_engine(settings: Settings) -> Engine:
    return create_engine(settings.SQLITE_HOST, echo=False)


def create_db_session_factory(db_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=db_engine, class_=Session)
