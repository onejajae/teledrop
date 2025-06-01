"""
설정 의존성 모듈

애플리케이션 설정 관련 의존성 주입 함수를 제공합니다.
"""

from functools import lru_cache

from app.core.config import Settings

@lru_cache
def get_settings() -> Settings:
    """애플리케이션 설정 의존성
    
    Returns:
        Settings: 애플리케이션 설정 객체
        
    Note:
        lru_cache로 캐싱되어 동일한 프로세스 내에서는 한 번만 생성됩니다.
        테스트에서는 dependency_overrides로 오버라이드할 수 있습니다.
    """
    return Settings() 