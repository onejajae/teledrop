"""
검증 기능을 제공하는 믹스인

Handler에서 사용하는 공통 검증 로직을 제공합니다.
"""

import re
from typing import Optional

from app.core.config import Settings
from app.core.exceptions import DropAccessDeniedError, DropPasswordInvalidError, FileSizeExceededError


class ValidationMixin:
    """검증 기능을 제공하는 믹스인"""
    
    settings: Settings  # Settings 주입 필요
    
    def validate_drop_password(self, drop, password: Optional[str] = None):
        """Drop 패스워드를 검증합니다."""
        if not self.settings.ENABLE_PASSWORD_PROTECTION:
            return
        if drop.password and drop.password != password:
            raise DropPasswordInvalidError("Invalid password for drop")
    
    def validate_drop_access(self, drop, auth_data=None):
        """Drop 접근 권한을 검증합니다."""
        if drop.is_private and not auth_data:
            if self.settings.REQUIRE_AUTH_FOR_SENSITIVE_OPS:
                raise DropAccessDeniedError("Authentication required for private drop")
    
    def validate_api_key_format(self, api_key: str) -> bool:
        """API Key 형식을 검증합니다."""
        if not api_key or len(api_key) < self.settings.API_KEY_LENGTH:
            return False
        
        # "tk_" 접두사 확인
        if not api_key.startswith("tk_"):
            return False
        
        # 접두사 이후 부분이 hex 문자인지 확인
        hex_part = api_key[3:]  # "tk_" 이후 부분
        pattern = r'^[a-f0-9]+$'
        return bool(re.match(pattern, hex_part))
    
    def validate_file_size(self, file_size: int, max_size: Optional[int] = None) -> bool:
        """파일 크기를 검증합니다."""
        max_size = max_size or self.settings.MAX_FILE_SIZE
        if file_size > max_size:
            raise FileSizeExceededError(f"File size {file_size} exceeds maximum {max_size}")
        return 0 < file_size <= max_size
    
    def validate_drop_title_length(self, title: Optional[str] = None) -> bool:
        """Drop 제목 길이를 검증합니다."""
        if not title:
            return True
        return len(title) <= self.settings.MAX_DROP_TITLE_LENGTH
    
    def validate_drop_description_length(self, description: Optional[str] = None) -> bool:
        """Drop 설명 길이를 검증합니다."""
        if not description:
            return True
        return len(description) <= self.settings.MAX_DROP_DESCRIPTION_LENGTH 