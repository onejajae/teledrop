"""스토리지 인터페이스 정의

파일 저장소 추상화를 위한 기본 인터페이스를 제공합니다.
로컬 스토리지, S3 등 다양한 백엔드 구현이 가능합니다.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, BinaryIO, Tuple, Callable, Awaitable
from pathlib import Path


class StorageInterface(ABC):
    """스토리지 백엔드를 위한 추상 인터페이스"""

    @property
    @abstractmethod
    def storage_type(self) -> str:
        """스토리지 타입을 반환합니다."""
        pass

    @abstractmethod
    async def save_file(self, file_stream: BinaryIO, file_path: str) -> str:
        """파일을 저장하고 저장 경로를 반환합니다.
        
        Args:
            file_stream: 저장할 파일 스트림
            file_path: 저장할 파일 경로 (상대경로)
            
        Returns:
            실제 저장된 파일의 경로
            
        Raises:
            StorageError: 파일 저장 실패 시
        """
        pass

    @abstractmethod
    async def save_file_streaming(
        self, 
        file_path: str,
        chunk_size: int = 1024 * 1024
    ) -> Tuple[Callable[[bytes], Awaitable[None]], Callable[[], Awaitable[None]]]:
        """스트리밍 방식으로 파일을 저장하기 위한 컨텍스트를 반환합니다.
        
        Args:
            file_path: 저장할 파일 경로 (상대경로)
            chunk_size: 청크 크기 (기본 1MB)
            
        Returns:
            Tuple[write_chunk, finalize]:
                - write_chunk: 청크를 쓰는 비동기 함수
                - finalize: 저장을 완료하는 비동기 함수
            
        Raises:
            StorageError: 파일 저장 실패 시
        """
        pass

    @abstractmethod
    async def read_file(self, file_path: str) -> AsyncGenerator[bytes, None]:
        """파일의 전체 내용을 읽어서 반환합니다.
        
        Args:
            file_path: 읽을 파일의 경로
            
        Yields:
            파일 데이터 청크
            
        Raises:
            FileNotFoundError: 파일이 존재하지 않을 때
            StorageError: 파일 읽기 실패 시
        """
        pass

    @abstractmethod
    async def read_file_range(
        self, file_path: str, start: int, end: int
    ) -> AsyncGenerator[bytes, None]:
        """파일의 지정된 범위를 읽어서 반환합니다.
        
        Args:
            file_path: 읽을 파일의 경로
            start: 시작 바이트 위치
            end: 끝 바이트 위치
            
        Yields:
            파일 데이터 청크
            
        Raises:
            FileNotFoundError: 파일이 존재하지 않을 때
            StorageError: 파일 읽기 실패 시
        """
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """파일을 삭제합니다.
        
        Args:
            file_path: 삭제할 파일의 경로
            
        Returns:
            삭제 성공 여부
        """
        pass

    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """파일이 존재하는지 확인합니다.
        
        Args:
            file_path: 확인할 파일의 경로
            
        Returns:
            파일 존재 여부
        """
        pass

    @abstractmethod
    async def get_file_size(self, file_path: str) -> int:
        """파일 크기를 반환합니다.
        
        Args:
            file_path: 파일 경로
            
        Returns:
            파일 크기 (바이트)
            
        Raises:
            FileNotFoundError: 파일이 존재하지 않을 때
        """
        pass

    @abstractmethod
    async def move_file(self, old_path: str, new_path: str) -> None:
        """파일을 이동하거나 이름을 변경합니다.

        Args:
            old_path: 현재 파일 경로
            new_path: 새 파일 경로

        Raises:
            StorageError: 파일 이동 실패 시
            FileNotFoundError: old_path 파일이 존재하지 않을 때
        """
        pass
