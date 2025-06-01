"""
의존성 타입 별칭 모듈

FastAPI Depends를 사용한 타입 별칭들을 정의합니다.
편의성과 타입 안정성을 위해 사용됩니다.
"""
from typing import Annotated, Optional
from fastapi import Depends
from app.dependencies.auth import get_current_user, get_current_user_optional, get_api_key_user

# 인증 의존성 타입 별칭들
CurrentUserDep = Annotated[dict, Depends(get_current_user)]
CurrentUserOptionalDep = Annotated[Optional[dict], Depends(get_current_user_optional)]
ApiKeyUserDep = Annotated[dict, Depends(get_api_key_user)] 