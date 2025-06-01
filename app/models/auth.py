from datetime import datetime
from sqlmodel import SQLModel


# Auth Models (Handler와 호환되도록 업데이트)
class AccessToken(SQLModel):
    """액세스 토큰 응답용"""
    access_token: str
    refresh_token: str | None = None  # 리프레시 토큰 추가
    token_type: str = "bearer"  # 소문자로 통일
    expires_in: int  # 만료까지 초 단위


class TokenPayload(SQLModel):
    """JWT 토큰 페이로드"""
    username: str
    token_type: str  # "access" or "refresh"
    issued_at: datetime
    expires_at: datetime


class AuthData(SQLModel):
    """인증 데이터"""
    username: str | None
    can_read: bool = False
    can_write: bool = False
