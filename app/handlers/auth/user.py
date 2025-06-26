from fastapi import Depends

from app.core.config import Settings
from app.core.dependencies import get_settings
from app.handlers.decorators import authenticate
from app.models.auth import AuthData

class CurrentUserHandler:
    def __init__(
        self,
        settings: Settings = Depends(get_settings)
    ):
        self.settings = settings

    @authenticate
    def execute(self, auth_data: AuthData | None = None) -> AuthData | None:
        return auth_data