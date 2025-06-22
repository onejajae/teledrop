"""
타임스탬프 관련 기능을 제공하는 믹스인

Handler에서 사용하는 시간 관련 공통 기능을 제공합니다.
"""

from datetime import datetime, timezone


class TimestampMixin:
    """타임스탬프 관련 기능을 제공하는 믹스인"""
    
    def get_current_timestamp(self) -> datetime:
        """현재 UTC 타임스탬프를 반환합니다."""
        return datetime.now(timezone.utc) 