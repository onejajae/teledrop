"""데이터베이스 연결 및 관리 모듈

데이터베이스 연결, 세션 관리, 테이블 생성/삭제 기능을 제공합니다.
"""

from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings

# Must import all SQLModel table classes to create all tables
from app.models import Drop # noqa: F401


settings = Settings()
engine = create_async_engine(settings.DATABASE_URL, echo=settings.SQL_ECHO)


async def init_db() -> None:
    """Create all tables in the database.
    
    Args:
        settings: Application settings object
    
    Call SQLModel.metadata.create_all() to create all tables.
    Do not touch existing tables.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def drop_db() -> None:
    """Delete all tables in the database.
    
    Args:
        settings: Application settings object
    
    Warning: This function will delete all data.
    Only use in test or development environments.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)