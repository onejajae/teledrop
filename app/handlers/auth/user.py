from typing import Optional
from fastapi import Depends, Cookie
from sqlmodel import Session

from app.core.config import Settings
from app.core.dependencies import get_session, get_settings
from app.models.auth import AuthData
from app.utils.token import verify_token
from app.utils.oauth import OAuth2PasswordBearerWithCookie

class CurrentUserHandler:
    def __init__(
        self,
        token: Optional[str] = Depends(OAuth2PasswordBearerWithCookie(
            tokenUrl="/api/auth/login", auto_error=False
        )),
        session: Session = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ):
        self.token = token
        self.session = session
        self.settings = settings

    def execute(self) -> Optional[AuthData]:
        # 1. Authorization 헤더의 Bearer 토큰 확인
        if self.token:
            payload = verify_token(self.token, self.settings, "access")
            if payload:
                username = payload.get("sub")
                # 인증된 사용자는 기본적으로 읽기/쓰기 권한 모두 부여
                return AuthData(
                    username=username,
                    can_read=True,
                    can_write=True
                )
        # 인증되지 않음
        return None 