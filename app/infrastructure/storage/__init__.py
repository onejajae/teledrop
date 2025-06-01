"""Storage Infrastructure

파일 스토리지 추상화 레이어입니다.
현재는 로컬 파일 시스템만 지원합니다.
"""

from .base import StorageInterface
from .local import LocalStorage

__all__ = ["StorageInterface", "LocalStorage"] 