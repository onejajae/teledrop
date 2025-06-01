"""Infrastructure 레이어

데이터베이스와 스토리지 인터페이스를 제공하는 레이어입니다.
"""

# 데이터베이스는 항상 필요하므로 일반 import
from . import database

# 스토리지는 선택적 import (boto3 의존성 때문에)
try:
    from . import storage
    HAS_STORAGE = True
except ImportError as e:
    # boto3나 기타 의존성이 없는 경우
    HAS_STORAGE = False
    storage = None

__all__ = ["database"]

if HAS_STORAGE:
    __all__.append("storage") 