"""
Drop 모델 패키지

모든 Drop 관련 스키마와 모델을 외부에서 쉽게 import할 수 있도록 제공합니다.
실제 API에서 사용되는 Form 스키마들과 응답 스키마들을 중심으로 구성합니다.
"""

# 테이블 모델
from .table import Drop

# 응답 스키마들
from .response import DropSummary, DropRead, DropList

# Form 요청 스키마들
from .request import (
    DropCreateForm,
    DropUpdateDetailForm, 
    DropUpdatePermissionForm, 
    DropSetPasswordForm, 
    DropUpdateFavoriteForm
)

# 필드 그룹들은 내부 구현이므로 export하지 않음
# 필요한 경우 직접 import: from app.models.drop.base import DropCore


__all__ = [
    # 공개 API - 실제로 외부에서 사용되는 클래스들
    "Drop",
    
    # 응답 스키마들
    "DropSummary", 
    "DropRead",
    "DropList",
    
    # Form 요청 스키마들
    "DropCreateForm",
    "DropUpdateDetailForm",
    "DropUpdatePermissionForm", 
    "DropSetPasswordForm",
    "DropUpdateFavoriteForm",
] 