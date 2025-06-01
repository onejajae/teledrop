"""인증 관련 Handler들

사용자 로그인, JWT 토큰 검증 및 갱신, 보안 유틸리티를 담당하는 통합 모듈입니다.
"""

import hashlib
import secrets
from dataclasses import dataclass
from typing import Optional, Any, Dict
from datetime import datetime, timedelta, timezone

import argon2
import jwt
from argon2.exceptions import VerifyMismatchError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request, HTTPException, status
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel

from app.handlers.base import BaseHandler
from app.core.config import Settings
from app.core.exceptions import AuthenticationError
from app.models.auth import AccessToken, TokenPayload

# Password hasher 인스턴스
password_hasher = argon2.PasswordHasher()


class OAuth2PasswordBearerWithCookie(OAuth2):
    """쿠키 기반 OAuth2 인증을 위한 클래스"""
    
    def __init__(
        self,
        name: str,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        auto_error: bool = True,
    ):
        self.name = name

        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        authorization: str = request.cookies.get(self.name)
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param


class SecurityUtils:
    """보안 관련 유틸리티 클래스"""
    
    @staticmethod
    def create_access_token(
        data: Dict[str, Any], 
        settings: Settings,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """JWT 액세스 토큰 생성"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXP_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def create_refresh_token(
        data: Dict[str, Any], 
        settings: Settings,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """JWT 리프레시 토큰 생성"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=30)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def verify_token(token: str, settings: Settings, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """JWT 토큰 검증"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            
            # 토큰 타입 검증
            if payload.get("type") != token_type:
                return None
                
            return payload
        except jwt.PyJWTError:
            return None
    
    @staticmethod
    def hash_password(password: str) -> str:
        """패스워드 해시 생성"""
        return password_hasher.hash(password)
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """패스워드 검증"""
        try:
            password_hasher.verify(hashed_password, password)
            return True
        except VerifyMismatchError:
            return False
    
    @staticmethod
    def generate_api_key() -> tuple[str, str, str]:
        """
        API Key 생성
        
        Returns:
            tuple[str, str, str]: (full_key, prefix, hash)
                - full_key: 사용자에게 제공할 완전한 키 (한 번만 표시)
                - prefix: 공개적으로 식별 가능한 접두사 (예: "tk_abc123")
                - hash: 데이터베이스에 저장할 해시값
        """
        # 32바이트 랜덤 키 생성
        key_bytes = secrets.token_bytes(32)
        key_hex = key_bytes.hex()
        
        # 접두사 생성 (처음 6자리)
        prefix = f"tk_{key_hex[:6]}"
        
        # 전체 키 생성
        full_key = f"tk_{key_hex}"
        
        # 해시 생성 (SHA-256)
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        
        return full_key, prefix, key_hash
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """API Key 해시 생성"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def verify_api_key(api_key: str, stored_hash: str) -> bool:
        """API Key 검증"""
        computed_hash = SecurityUtils.hash_api_key(api_key)
        return secrets.compare_digest(computed_hash, stored_hash)
    
    @staticmethod
    def generate_drop_key(length: int = 8) -> str:
        """Drop 키 생성 (URL-safe)"""
        return secrets.token_urlsafe(length)[:length]
    
    @staticmethod
    def generate_secure_filename(original_filename: str) -> str:
        """보안을 위한 파일명 생성"""
        # 파일 확장자 추출
        if "." in original_filename:
            name, ext = original_filename.rsplit(".", 1)
            return f"{secrets.token_urlsafe(16)}.{ext}"
        else:
            return secrets.token_urlsafe(16)


@dataclass
class LoginHandler(BaseHandler):
    """로그인 처리를 담당하는 Handler
    
    사용자명과 패스워드를 검증하고 JWT 토큰을 생성합니다.
    BaseHandler의 로깅, 검증, 타임스탬프 기능을 활용합니다.
    """
    session: AsyncSession
    settings: Settings
    
    async def execute(self, username: str, password: str) -> AccessToken:
        """사용자 인증 후 JWT 토큰을 생성합니다.
        
        Args:
            username: 사용자명
            password: 패스워드
            
        Returns:
            AccessToken: JWT 액세스 토큰과 리프레시 토큰
            
        Raises:
            AuthenticationError: 인증 실패 시
        """
        self.log_info("Login attempt", username=username)
        
        try:
            # 사용자명 검증 (Settings에서 관리자 계정 확인)
            if username != self.settings.WEB_USERNAME:
                self.log_warning("Invalid username", username=username)
                raise AuthenticationError("Invalid username")
            
            # 패스워드 검증 (SecurityUtils 사용)
            if not SecurityUtils.verify_password(password, self.settings.WEB_PASSWORD):
                self.log_warning("Password verification failed")
                raise AuthenticationError("Invalid password")
            
            # JWT 토큰 생성
            access_token = await self._create_access_token(username)
            refresh_token = await self._create_refresh_token(username)
            
            self.log_info("Login successful", username=username)
            
            return AccessToken(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=self.settings.JWT_EXP_MINUTES * 60
            )
            
        except AuthenticationError:
            self.log_error("Authentication failed", username=username)
            raise
        except Exception as e:
            self.log_error("Login error", username=username, error=str(e))
            raise AuthenticationError("Authentication failed")
    
    async def _create_access_token(self, username: str) -> str:
        """JWT 액세스 토큰을 생성합니다.
        
        Args:
            username: 사용자명
            
        Returns:
            str: JWT 액세스 토큰
        """
        # JWT 페이로드 구성
        payload = {
            "sub": username,  # subject (사용자)
            "iat": int(self.get_current_timestamp().timestamp()),  # issued at
        }
        
        # SecurityUtils를 사용하여 토큰 생성
        token = SecurityUtils.create_access_token(payload, self.settings)
        
        self.log_info("Access token created", username=username)
        return token
    
    async def _create_refresh_token(self, username: str) -> str:
        """JWT 리프레시 토큰을 생성합니다.
        
        Args:
            username: 사용자명
            
        Returns:
            str: JWT 리프레시 토큰
        """
        # JWT 페이로드 구성
        payload = {
            "sub": username,  # subject (사용자)
            "iat": int(self.get_current_timestamp().timestamp()),  # issued at
        }
        
        # SecurityUtils를 사용하여 토큰 생성 (30일 만료)
        expires_delta = timedelta(days=30)
        token = SecurityUtils.create_refresh_token(payload, self.settings, expires_delta)
        
        self.log_info("Refresh token created", username=username)
        return token


@dataclass
class TokenValidateHandler(BaseHandler):
    """JWT 토큰 검증을 담당하는 Handler
    
    JWT 토큰의 서명, 만료시간, 형식을 검증합니다.
    """
    session: Optional[AsyncSession]  # 토큰 검증에는 DB 세션이 필요없음
    settings: Settings
    
    async def execute(self, token: str) -> TokenPayload:
        """JWT 토큰을 검증하고 페이로드를 반환합니다.
        
        Args:
            token: 검증할 JWT 토큰
            
        Returns:
            TokenPayload: 토큰 페이로드 정보
            
        Raises:
            AuthenticationError: 토큰이 유효하지 않을 때
        """
        self.log_info("Token validation requested")
        
        try:
            # SecurityUtils를 사용하여 토큰 검증
            payload = SecurityUtils.verify_token(token, self.settings)
            
            if not payload:
                self.log_warning("Token verification failed")
                raise AuthenticationError("Invalid token")
            
            # 토큰 타입 검증
            token_type = payload.get("type")
            if token_type not in ["access", "refresh"]:
                self.log_warning("Invalid token type", token_type=token_type)
                raise AuthenticationError("Invalid token type")
            
            # 사용자명 검증
            username = payload.get("sub")
            if not username:
                self.log_warning("Missing username in token")
                raise AuthenticationError("Invalid token format")
            
            self.log_info("Token validation successful", username=username, token_type=token_type)
            
            return TokenPayload(
                username=username,
                token_type=token_type,
                issued_at=datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc),
                expires_at=datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc)
            )
            
        except AuthenticationError:
            self.log_error("Token validation failed")
            raise
        except Exception as e:
            self.log_error("Token validation error", error=str(e))
            raise AuthenticationError("Token validation failed")


@dataclass
class TokenRefreshHandler(BaseHandler):
    """토큰 갱신을 담당하는 Handler
    
    리프레시 토큰으로 새로운 액세스 토큰을 발급합니다.
    """
    session: Optional[AsyncSession]  # 토큰 갱신에는 DB 세션이 필요없음
    settings: Settings
    
    async def execute(self, refresh_token: str) -> AccessToken:
        """리프레시 토큰으로 새 액세스 토큰을 생성합니다.
        
        Args:
            refresh_token: 리프레시 토큰
            
        Returns:
            AccessToken: 새로운 액세스 토큰
            
        Raises:
            AuthenticationError: 리프레시 토큰이 유효하지 않을 때
        """
        self.log_info("Token refresh requested")
        
        try:
            # 리프레시 토큰 검증
            validator = TokenValidateHandler(session=None, settings=self.settings)
            token_payload = await validator.execute(refresh_token)
            
            # 리프레시 토큰 타입 확인
            if token_payload.token_type != "refresh":
                self.log_warning("Invalid token type for refresh", token_type=token_payload.token_type)
                raise AuthenticationError("Invalid token type")
            
            # 새 액세스 토큰 생성
            login_handler = LoginHandler(session=None, settings=self.settings)
            access_token = await login_handler._create_access_token(token_payload.username)
            
            self.log_info("Token refresh successful", username=token_payload.username)
            
            return AccessToken(
                access_token=access_token,
                refresh_token=refresh_token,  # 기존 리프레시 토큰 재사용
                token_type="bearer",
                expires_in=self.settings.JWT_EXP_MINUTES * 60
            )
            
        except AuthenticationError:
            self.log_error("Token refresh failed")
            raise
        except Exception as e:
            self.log_error("Token refresh error", error=str(e))
            raise AuthenticationError("Token refresh failed")


# 편의를 위한 함수들
def create_access_token(
    data: Dict[str, Any], 
    settings: Settings,
    expires_delta: Optional[timedelta] = None
) -> str:
    """JWT 액세스 토큰 생성 (편의 함수)"""
    return SecurityUtils.create_access_token(data, settings, expires_delta)


def create_refresh_token(
    data: Dict[str, Any], 
    settings: Settings,
    expires_delta: Optional[timedelta] = None
) -> str:
    """JWT 리프레시 토큰 생성 (편의 함수)"""
    return SecurityUtils.create_refresh_token(data, settings, expires_delta)


def verify_token(token: str, settings: Settings, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """JWT 토큰 검증 (편의 함수)"""
    return SecurityUtils.verify_token(token, settings, token_type)


def hash_password(password: str) -> str:
    """패스워드 해시 생성 (편의 함수)"""
    return SecurityUtils.hash_password(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """패스워드 검증 (편의 함수)"""
    return SecurityUtils.verify_password(password, hashed_password)


def generate_api_key() -> tuple[str, str, str]:
    """API Key 생성 (편의 함수)"""
    return SecurityUtils.generate_api_key()


def hash_api_key(api_key: str) -> str:
    """API Key 해시 생성 (편의 함수)"""
    return SecurityUtils.hash_api_key(api_key)


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """API Key 검증 (편의 함수)"""
    return SecurityUtils.verify_api_key(api_key, stored_hash)


def generate_drop_key(length: int = 8) -> str:
    """Drop 키 생성 (편의 함수)"""
    return SecurityUtils.generate_drop_key(length)


def generate_secure_filename(original_filename: str) -> str:
    """보안을 위한 파일명 생성 (편의 함수)"""
    return SecurityUtils.generate_secure_filename(original_filename) 