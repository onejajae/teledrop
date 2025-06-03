from typing import Optional
from fastapi import Depends
from sqlmodel import Session
from datetime import datetime, timedelta, timezone
from app.handlers.base import BaseHandler
from app.models.auth import AccessToken
from app.core.exceptions import AuthenticationError
from app.core.config import Settings
# from app.utils.security import verify_password, create_access_token, create_refresh_token
from app.utils.password import verify_password
from app.utils.token import create_access_token, create_refresh_token
from app.core.dependencies import get_session, get_settings

class LoginHandler(BaseHandler):
    """로그인 처리를 담당하는 Handler
    
    사용자명과 패스워드를 검증하고 JWT 토큰을 생성합니다.
    BaseHandler의 로깅, 검증, 타임스탬프 기능을 활용합니다.
    """
    def __init__(
        self,
        session: Session = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.settings = settings
    
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
            if not verify_password(password, self.settings.WEB_PASSWORD):
                self.log_warning("Password verification failed")
                raise AuthenticationError("Invalid password")
            
            # JWT 토큰 생성
            access_token = create_access_token({"sub": username, "iat": datetime.now(timezone.utc)}, self.settings, timedelta(minutes=self.settings.JWT_EXP_MINUTES))
            refresh_token = create_refresh_token({"sub": username, "iat": datetime.now(timezone.utc)}, self.settings, timedelta(days=30))
            
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
    