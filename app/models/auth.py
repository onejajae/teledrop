from datetime import datetime
from sqlmodel import SQLModel
from typing import Literal


# Auth Models (Handler와 호환되도록 업데이트)
class AccessToken(SQLModel):
    """액세스 토큰 응답용"""
    access_token: str
    token_type: str = "bearer"  # 소문자로 통일
    expires_in: int  # 만료까지 초 단위


class TokenPayload(SQLModel):
    """JWT 토큰 페이로드"""
    username: str
    token_type: str  # "access" or "refresh"
    exp: datetime


class AuthData(SQLModel):
    """통합 인증 정보"""
    username: str
    auth_type: Literal["jwt", "api_key"]  # 인증 방식
    authenticated_at: datetime = datetime.now()
