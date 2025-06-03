from typing import Optional
from fastapi import Depends
from sqlmodel import Session
from datetime import datetime, timezone
from app.handlers.base import BaseHandler
from app.models.auth import TokenPayload
from app.core.exceptions import AuthenticationError
from app.core.config import Settings
from app.utils.token import verify_token
from app.core.dependencies import get_session, get_settings


class TokenValidateHandler(BaseHandler):
    """JWT 토큰 검증을 담당하는 Handler
    
    JWT 토큰의 서명, 만료시간, 형식을 검증합니다.
    """
    def __init__(
        self,
        session: Optional[Session] = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.settings = settings
    
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
            payload = verify_token(token, self.settings)
            
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


# class TokenRefreshHandler(BaseHandler):
#     """토큰 갱신을 담당하는 Handler
    
#     리프레시 토큰으로 새로운 액세스 토큰을 발급합니다.
#     """
#     def __init__(
#         self,
#         session: Optional[Session] = Depends(get_session),
#         settings: Settings = Depends(get_settings)
#     ):
#         self.session = session
#         self.settings = settings
    
#     async def execute(self, refresh_token: str) -> AccessToken:
#         """리프레시 토큰으로 새 액세스 토큰을 생성합니다.
        
#         Args:
#             refresh_token: 리프레시 토큰
            
#         Returns:
#             AccessToken: 새로운 액세스 토큰
            
#         Raises:
#             AuthenticationError: 리프레시 토큰이 유효하지 않을 때
#         """
#         self.log_info("Token refresh requested")
        
#         try:
#             # 리프레시 토큰 검증
#             validator = TokenValidateHandler(session=None, settings=self.settings)
#             token_payload = await validator.execute(refresh_token)
            
#             # 리프레시 토큰 타입 확인
#             if token_payload.token_type != "refresh":
#                 self.log_warning("Invalid token type for refresh", token_type=token_payload.token_type)
#                 raise AuthenticationError("Invalid token type")
            
#             # 새 액세스 토큰 생성
#             login_handler = LoginHandler(session=None, settings=self.settings)
#             access_token = await login_handler._create_access_token(token_payload.username)
            
#             self.log_info("Token refresh successful", username=token_payload.username)
            
#             return AccessToken(
#                 access_token=access_token,
#                 refresh_token=refresh_token,  # 기존 리프레시 토큰 재사용
#                 token_type="bearer",
#                 expires_in=self.settings.JWT_EXP_MINUTES * 60
#             )
            
#         except AuthenticationError:
#             self.log_error("Token refresh failed")
#             raise
#         except Exception as e:
#             self.log_error("Token refresh error", error=str(e))
#             raise AuthenticationError("Token refresh failed")