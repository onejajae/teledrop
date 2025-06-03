from typing import Optional
from fastapi import Depends, Cookie
from sqlmodel import Session

from app.core.config import Settings
from app.core.dependencies import get_session, get_settings
from app.utils.token import verify_token
from app.utils.oauth import OAuth2PasswordBearerWithCookie

class CurrentUserHandler:
    def __init__(
        self,
        token: Optional[str] = Depends(OAuth2PasswordBearerWithCookie(
            name="access_token", tokenUrl="/api/auth/login", auto_error=False
        )),
        access_token: Optional[str] = Cookie(None),
        session: Session = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ):
        self.token = token
        self.access_token = access_token
        self.session = session
        self.settings = settings

    def execute(self) -> Optional[dict]:
        # 1. Authorization 헤더의 Bearer 토큰 확인
        if self.token:
            payload = verify_token(self.token, self.settings, "access")
            if payload:
                return {"type": "jwt", "username": payload.get("sub"), "payload": payload}
            # API Key 검증
            from app.models.api_key import ApiKey
            api_key = ApiKey.get_by_hash(self.session, self.token)
            if api_key and api_key.is_active and not api_key.is_expired:
                api_key.update_last_used()
                self.session.add(api_key)
                self.session.commit()
                return {"type": "api_key", "api_key": api_key}
        # 2. 쿠키의 액세스 토큰 확인 (웹 인터페이스용)
        if self.access_token:
            access_token = self.access_token
            if access_token.startswith("Bearer "):
                access_token = access_token[7:]
            payload = verify_token(access_token, self.settings, "access")
            if payload:
                return {"type": "jwt", "username": payload.get("sub"), "payload": payload}
        # 인증되지 않음
        return None 