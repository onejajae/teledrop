from fastapi import Depends
from sqlmodel import Session
from app.models import Drop
from app.core.config import Settings
from app.core.dependencies import get_session, get_settings

class DropKeyCheckHandler:
    def __init__(
        self,
        session: Session = Depends(get_session),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.settings = settings
        self.reserved_keys = ["api", ""]

    def execute(self, key: str) -> bool:
        # 예약어 체크
        if key in self.reserved_keys:
            return True
        # DB에 이미 존재하는지 체크
        existing = Drop.get_by_key(self.session, key)
        return existing is not None 