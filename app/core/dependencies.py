from sqlmodel import Session
from fastapi import Depends
from functools import lru_cache

from app.core.config import Settings
from app.infrastructure.database.connection import get_engine
from app.infrastructure.storage.base import StorageInterface
from app.infrastructure.storage.local import LocalStorage


@lru_cache
def get_settings() -> Settings:
    """애플리케이션 설정 의존성"""
    return Settings() 


def get_session(settings: Settings = Depends(get_settings)):
    """데이터베이스 세션 의존성 (자동 세션 리소스 관리)
    
    SQLModel Session의 컨텍스트 매니저를 사용하여 세션 리소스를 자동 관리합니다.
    예외 발생 시 자동으로 롤백하고 항상 세션을 닫습니다.
    정상 완료 시에는 모델에서 명시적으로 commit을 호출해야 합니다.
    
    Yields:
        Session: SQLModel 세션 객체
    """
    with Session(get_engine(settings)) as session:
        yield session


def get_storage(settings: Settings = Depends(get_settings)) -> StorageInterface:
    """스토리지 서비스 의존성
    
    현재는 LocalStorage만 지원하지만, 미래 확장성을 위해
    설정 기반으로 다른 스토리지 타입을 추가할 수 있습니다.
    """
    # 현재는 LocalStorage만 지원
    # 미래에 S3 등 다른 스토리지 지원 시 조건부 로직 추가 예정
    storage_type = getattr(settings, "STORAGE_TYPE", "local").lower()
    
    if storage_type == "local":
        return LocalStorage(
            base_path=settings.SHARE_DIRECTORY,
            chunk_size=settings.CHUNK_SIZE
        )
    else:
        # 미래 확장성을 위한 예외
        raise ValueError(f"Unsupported storage type: {storage_type}. Currently only 'local' is supported.") 