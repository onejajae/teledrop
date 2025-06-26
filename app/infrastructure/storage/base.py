"""스토리지 인터페이스 정의

파일 저장소 추상화를 위한 기본 인터페이스를 제공합니다.
로컬 스토리지, S3 등 다양한 백엔드 구현이 가능합니다.
"""

import anyio
import anyio.to_thread
from abc import ABC, abstractmethod
from typing import AsyncGenerator, AsyncIterator, BinaryIO
from contextlib import asynccontextmanager


class StorageInterface(ABC):
    """스토리지 백엔드를 위한 추상 인터페이스"""

    @property
    @abstractmethod
    def storage_type(self) -> str:
        """스토리지 타입을 반환합니다."""
        pass

    @abstractmethod
    @asynccontextmanager
    async def _write_stream(self, file_path: str):
        """파일 쓰기를 위한 스트림 컨텍스트 매니저 (내부 구현용)
        
        이 메서드는 구현 세부사항이므로 외부에서 직접 사용하지 않습니다.
        
        Args:
            file_path: 저장할 파일 경로 (상대경로)
            
        Yields:
            파일 스트림 객체 (write, aclose 메서드 제공)
        """
        pass

    async def save(
        self, 
        chunk_iterator: AsyncIterator[bytes], 
        file_path: str
    ) -> tuple[str, int]:
        """AsyncIterator에서 chunk를 받아 파일로 저장합니다.
        
        이 메서드는 Handler에서 비즈니스 로직(해시 계산, 검증 등)을 수행하면서 동시에 파일을 저장할 수 있도록 지원합니다.
        
        Args:
            chunk_iterator: 처리된 chunk를 yield하는 비동기 iterator
            file_path: 저장할 파일 경로
            
        Returns:
            (실제 저장된 파일의 경로, 실제 저장된 파일 크기)
            
        Raises:
            StorageError: 파일 저장 실패 시
            
        Examples:
            # Handler에서 사용
            async def process_chunks():
                while chunk := await upload_file.read(chunk_size):
                    # 비즈니스 로직 수행
                    file_hash.update(chunk)
                    yield chunk
            
            path, size = await storage.save(process_chunks(), "file.bin")
        """
        async with self._write_stream(file_path) as stream:
            total_size = 0
            async for chunk in chunk_iterator:
                await stream.write(chunk)
                total_size += len(chunk)
        return file_path, total_size

    @abstractmethod
    async def read(
        self, 
        file_path: str, 
        start: int | None = None, 
        end: int | None = None
    ) -> AsyncGenerator[bytes, None]:
        """파일의 내용을 읽어서 반환합니다.
        
        Args:
            file_path: 읽을 파일의 경로
            start: 시작 바이트 위치 (None이면 처음부터)
            end: 끝 바이트 위치 (None이면 끝까지)
            
        Yields:
            파일 데이터 청크
            
        Raises:
            FileNotFoundError: 파일이 존재하지 않을 때
            StorageError: 파일 읽기 실패 시
            
        Examples:
            # 전체 파일 읽기
            async for chunk in storage.read("file.bin"):
                process(chunk)
            
            # 범위 읽기 (HTTP Range 요청)
            async for chunk in storage.read("file.bin", 0, 1023):
                process(chunk)
            
            # 특정 위치부터 끝까지
            async for chunk in storage.read("file.bin", start=1024):
                process(chunk)
        """
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """파일을 삭제합니다.
        
        Args:
            file_path: 삭제할 파일의 경로
            
        Returns:
            삭제 성공 여부
        """
        pass

    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """파일이 존재하는지 확인합니다.
        
        Args:
            file_path: 확인할 파일의 경로
            
        Returns:
            파일 존재 여부
        """
        pass

    @abstractmethod
    async def size(self, file_path: str) -> int:
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
    async def move(self, old_path: str, new_path: str) -> None:
        """파일을 이동하거나 이름을 변경합니다.

        Args:
            old_path: 현재 파일 경로
            new_path: 새 파일 경로

        Raises:
            StorageError: 파일 이동 실패 시
            FileNotFoundError: old_path 파일이 존재하지 않을 때
        """
        pass
