from typing import AsyncGenerator
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Depends
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from functools import lru_cache

from app.core.config import Settings
from app.infrastructure.database.connection import engine
from app.infrastructure.storage.base import StorageInterface
from app.infrastructure.storage.local import LocalStorage
from app.models.auth import AuthData
from app.utils.oauth import OAuth2PasswordBearerWithCookie
from app.utils.token import verify_jwt_token


@lru_cache
def get_settings() -> Settings:
    """애플리케이션 설정 의존성"""
    return Settings() 


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """데이터베이스 세션 의존성 (자동 세션 리소스 관리)
    
    전역 engine을 사용하여 세션을 생성합니다.
    SQLModel Session의 컨텍스트 매니저를 사용하여 세션 리소스를 자동 관리합니다.
    예외 발생 시 자동으로 롤백하고 항상 세션을 닫습니다.
    정상 완료 시에는 모델에서 명시적으로 commit을 호출해야 합니다.
    
    Yields:
        Session: SQLModel 세션 객체
    """
    async with AsyncSession(engine) as session:
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
            read_chunk_size=settings.READ_CHUNK_SIZE,
            write_chunk_size=settings.WRITE_CHUNK_SIZE
        )
    else:
        # 미래 확장성을 위한 예외
        raise ValueError(f"Unsupported storage type: {storage_type}. Currently only 'local' is supported.") 


# ===============================================
# 🔐 인증 관련 의존성 함수들
# ===============================================

# OAuth2 스킴들
oauth2_bearer_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False
)

oauth2_cookie_scheme = OAuth2PasswordBearerWithCookie(
    tokenUrl="/api/auth/login", 
    auto_error=False
)

# API Key 헤더 스킴
api_key_header = APIKeyHeader(
    name="API-KEY",
    auto_error=False
)


async def get_auth_data(
    cookie_jwt: str | None = Depends(oauth2_cookie_scheme),
    settings: Settings = Depends(get_settings)
) -> AuthData | None:
    """현재 요청의 인증 데이터 추출 - 현재는 쿠키 기반 JWT만 지원
    
    이 함수는 원시 인증 데이터를 제공하며, 실제 인증 검증은
    핸들러의 @authenticate 데코레이터에서 수행됩니다.
    
    Returns:
        Optional[AuthData]: 인증 데이터 (인증되지 않은 경우 None)
    """
    # 현재는 쿠키 JWT만 사용
    if cookie_jwt:
        payload = verify_jwt_token(cookie_jwt, settings)
        if payload: 
            return AuthData(
                username=payload.username,
                auth_type="jwt",
            )
        
    return None
    