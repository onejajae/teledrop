"""
인증 의존성 모듈

JWT 토큰, API Key 등 인증 관련 의존성을 제공합니다.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status, Header, Cookie
from sqlmodel import Session

from app.core.config import Settings
from app.handlers.auth_handlers import verify_token, OAuth2PasswordBearerWithCookie
from app.dependencies.db import get_session
from app.dependencies.settings import get_settings
from app.models.api_key import ApiKey


def get_current_user_optional(
    token: Optional[str] = Depends(OAuth2PasswordBearerWithCookie(
                name="access_token", tokenUrl="/api/auth/login", auto_error=False
            )),
    access_token: Optional[str] = Cookie(None),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings)
) -> Optional[dict]:
    """
    선택적 사용자 인증 (인증되지 않아도 허용)
    
    JWT 토큰 또는 API Key를 통한 인증을 시도하지만,
    인증 실패 시에도 None을 반환하여 요청을 계속 처리합니다.
    """
    # 1. Authorization 헤더의 Bearer 토큰 확인
    if token:
        # JWT 토큰 검증 시도
        payload = verify_token(token, settings, "access")
        if payload:
            return {"type": "jwt", "username": payload.get("sub"), "payload": payload}
        
        # API Key 검증 시도
        api_key = ApiKey.get_by_hash(session, token)
        if api_key and api_key.is_active and not api_key.is_expired:
            # 마지막 사용 시간 업데이트
            api_key.update_last_used()
            session.add(api_key)
            session.commit()
            return {"type": "api_key", "api_key": api_key}
    
    # 2. 쿠키의 액세스 토큰 확인 (웹 인터페이스용)
    if access_token:
        # "Bearer " 접두사가 있다면 제거
        if access_token.startswith("Bearer "):
            access_token = access_token[7:]  # "Bearer " 제거
        
        payload = verify_token(access_token, settings, "access")
        if payload:
            return {"type": "jwt", "username": payload.get("sub"), "payload": payload}
    
    # 인증되지 않음
    return None


def get_current_user(
    user: Optional[dict] = Depends(get_current_user_optional)
) -> dict:
    """
    필수 사용자 인증 (인증되지 않으면 401 에러)
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_api_key_user(
    authorization: Optional[str] = Header(None),
    session: Session = Depends(get_session)
) -> dict:
    """
    API Key 전용 인증 (API 엔드포인트용)
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key가 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Bearer 스키마 확인
    try:
        scheme, api_key = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise ValueError()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 인증 헤더 형식입니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # API Key 검증
    db_api_key = ApiKey.get_by_hash(session, api_key)
    if not db_api_key or not db_api_key.is_active or db_api_key.is_expired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 API Key입니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 마지막 사용 시간 업데이트
    db_api_key.update_last_used()
    session.add(db_api_key)
    session.commit()
    
    return {"type": "api_key", "api_key": db_api_key} 