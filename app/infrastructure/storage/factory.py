"""스토리지 팩토리

설정에 따라 적절한 스토리지 백엔드를 생성하는 팩토리 클래스입니다.
현재는 로컬 스토리지만 지원합니다.
"""

from typing import Optional

from .base import StorageInterface
from .local import LocalStorage


class StorageFactory:
    """스토리지 백엔드 팩토리"""

    @staticmethod
    def create_storage(
        storage_type: str,
        storage_path: Optional[str] = None,
    ) -> StorageInterface:
        """설정에 따라 스토리지 백엔드를 생성합니다.
        
        Args:
            storage_type: 스토리지 타입 (현재는 "local"만 지원)
            storage_path: 로컬 스토리지 경로
            
        Returns:
            생성된 스토리지 인스턴스
            
        Raises:
            ValueError: 지원하지 않는 스토리지 타입인 경우
        """
        if storage_type.lower() == "local":
            return LocalStorage(base_path=storage_path or "share")
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}. Only 'local' is supported.")

    @staticmethod
    def create_from_settings(settings) -> StorageInterface:
        """설정 객체로부터 스토리지 백엔드를 생성합니다.
        
        Args:
            settings: 애플리케이션 설정 객체
            
        Returns:
            생성된 스토리지 인스턴스
        """
        storage_type = getattr(settings, "STORAGE_TYPE", "local")
        storage_path = getattr(settings, "STORAGE_PATH", "share")
        
        return StorageFactory.create_storage(storage_type, storage_path=storage_path) 