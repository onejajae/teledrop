"""
로깅 기능을 제공하는 믹스인

Handler에서 일관된 로깅을 위한 공통 기능을 제공합니다.
"""

import logging
from app.core.config import Settings


class LoggingMixin:
    """로깅 기능을 제공하는 믹스인"""
    
    settings: Settings  # Settings 주입 필요
    
    @property
    def logger(self) -> logging.Logger:
        """클래스 이름을 기반으로 한 로거를 반환합니다."""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(self.__class__.__name__)
            # Settings에서 로그 레벨 설정
            if hasattr(self, 'settings'):
                self._logger.setLevel(getattr(logging, self.settings.LOG_LEVEL, "INFO"))
        return self._logger
    
    def log_info(self, message: str, **kwargs):
        """정보 수준 로그를 기록합니다."""
        if not getattr(self.settings, 'ENABLE_HANDLER_LOGGING', True):
            return
        extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
        full_message = f"{message} {extra_info}".strip()
        self.logger.info(full_message)
    
    def log_error(self, message: str, **kwargs):
        """에러 수준 로그를 기록합니다."""
        if not getattr(self.settings, 'ENABLE_HANDLER_LOGGING', True):
            return
        extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
        full_message = f"{message} {extra_info}".strip()
        self.logger.error(full_message)
    
    def log_warning(self, message: str, **kwargs):
        """경고 수준 로그를 기록합니다."""
        if not getattr(self.settings, 'ENABLE_HANDLER_LOGGING', True):
            return
        extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
        full_message = f"{message} {extra_info}".strip()
        self.logger.warning(full_message) 