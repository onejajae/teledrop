"""데이터베이스 연결 및 관리 모듈

데이터베이스 연결, 세션 관리, 테이블 생성/삭제 기능을 제공합니다.
"""

from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy.engine import Engine

from app.core.config import Settings

# 모든 SQLModel 테이블 클래스들을 import해야 metadata.create_all()이 정상 작동합니다
from app.models import Drop

# 순환 import를 피하기 위해 여기서는 설정을 직접 import하지 않음
engine = None


def get_engine(settings: Settings) -> Engine:
    """데이터베이스 엔진을 가져옵니다.
    
    Args:
        settings: 애플리케이션 설정 객체 (None인 경우 기본 설정 사용)
        
    Returns:
        SQLModel 엔진 인스턴스
    """
    global engine
    if engine is None:
        engine = create_engine(settings.DATABASE_URL, echo=settings.SQL_ECHO)
    return engine



def init_db(settings: Settings) -> None:
    """데이터베이스 테이블들을 생성합니다.
    
    Args:
        settings: 애플리케이션 설정 객체 (None인 경우 기본 설정 사용)
    
    SQLModel.metadata.create_all()을 호출하여 정의된 모든 테이블을 생성합니다.
    이미 존재하는 테이블은 건드리지 않습니다.
    """
    SQLModel.metadata.create_all(get_engine(settings))


def drop_db(settings: Settings) -> None:
    """모든 데이터베이스 테이블을 삭제합니다.
    
    Args:
        settings: 애플리케이션 설정 객체 (None인 경우 기본 설정 사용)
    
    주의: 이 함수는 모든 데이터를 삭제합니다. 
    테스트 환경이나 개발 환경에서만 사용해야 합니다.
    """
    SQLModel.metadata.drop_all(get_engine(settings)) 