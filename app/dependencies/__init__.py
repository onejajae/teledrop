"""
의존성 주입 패키지

FastAPI 애플리케이션의 모든 의존성 주입을 관리합니다.
도메인별로 분리되어 있으며, 단일 책임 원칙을 준수합니다.

구조:
- base: 기본 의존성 (DB, Storage)
- settings: 설정 관련 의존성
- auth: 인증 관련 의존성
- types: 타입 별칭들
- handlers/: Handler 팩토리들 (도메인별 분리)
"""

# 기본 의존성들
from .db import get_session
from .storage import get_storage

# 설정 의존성
from .settings import get_settings

# 인증 의존성들
from .auth import (
    get_current_user_optional,
    get_current_user,
    get_api_key_user,
)

# 타입 별칭들
from .types import (
    CurrentUserDep,
    CurrentUserOptionalDep,
    ApiKeyUserDep,
)

# Handler 팩토리들
from .handlers import (
    # Drop handlers
    get_drop_list_handler,
    get_drop_detail_handler,
    get_drop_create_handler,
    get_drop_update_handler,
    get_drop_delete_handler,
    get_drop_access_handler,
    
    # File handlers
    get_file_download_handler,
    get_file_range_handler,
    
    # API Key handlers
    get_api_key_create_handler,
    get_api_key_list_handler,
    get_api_key_update_handler,
    get_api_key_delete_handler,
    get_api_key_validate_handler,
    
    # Auth handlers
    get_login_handler,
    get_token_validate_handler,
    get_token_refresh_handler,
)

__all__ = [
    # 기본 의존성
    "get_session",
    "get_settings",
    "get_storage",
    
    # 인증 의존성
    "get_current_user_optional",
    "get_current_user",
    "get_api_key_user",
    
    # 타입 별칭
    "DatabaseDep",
    "StorageDep",
    "SettingsDep",
    "CurrentUserDep",
    "CurrentUserOptionalDep",
    "ApiKeyUserDep",
    
    # Handler 팩토리들
    "get_drop_list_handler",
    "get_drop_detail_handler",
    "get_drop_create_handler",
    "get_drop_update_handler",
    "get_drop_delete_handler",
    "get_drop_access_handler",
    "get_file_download_handler",
    "get_file_range_handler",
    "get_api_key_create_handler",
    "get_api_key_list_handler",
    "get_api_key_update_handler",
    "get_api_key_delete_handler",
    "get_api_key_validate_handler",
    "get_login_handler",
    "get_token_validate_handler",
    "get_token_refresh_handler",
] 