from sqlmodel import Session
from fastapi import Depends

from app.core.config import Settings
from app.dependencies.settings import get_settings
from app.infrastructure.database.connection import get_engine

def get_session(settings: Settings = Depends(get_settings)):
    """데이터베이스 세션 의존성 (settings를 의존성으로 주입)"""
    with Session(get_engine(settings)) as session:
        yield session 