"""로컬 파일 시스템 스토리지 구현

로컬 디스크를 사용하는 스토리지 백엔드 구현입니다.
기존 content_service.py의 파일 처리 로직을 참고하여 작성되었습니다.
"""

import os
import anyio
import anyio.to_thread
import tempfile
from pathlib import Path
from typing import AsyncGenerator, BinaryIO, Tuple, Callable, Awaitable

from .base import StorageInterface


class LocalStorage(StorageInterface):
    """로컬 파일 시스템을 사용하는 스토리지 구현"""

    def __init__(self, base_path: str = "share"):
        """LocalStorage 초기화
        
        Args:
            base_path: 파일이 저장될 기본 디렉토리 경로
        """
        self.base_path = Path(base_path)
        self._storage_type = "local"  # 스토리지 타입 속성 추가
        # 디렉토리가 없으면 생성
        self.base_path.mkdir(parents=True, exist_ok=True)

    @property
    def storage_type(self) -> str:
        """스토리지 타입을 반환합니다."""
        return self._storage_type

    def _get_full_path(self, file_path: str) -> Path:
        """상대 경로를 전체 경로로 변환"""
        return self.base_path / file_path

    async def save_file(self, file_stream: BinaryIO, file_path: str) -> str:
        """파일을 로컬 디스크에 저장합니다."""
        full_path = self._get_full_path(file_path)
        
        # 상위 디렉토리 생성
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 파일 저장
        async with await anyio.open_file(full_path, mode="wb") as f:
            while chunk := await anyio.to_thread.run_sync(
                file_stream.read, 1024 * 1024  # 1MB 청크
            ):
                await f.write(chunk)
        
        return str(file_path)

    async def read_file(self, file_path: str) -> AsyncGenerator[bytes, None]:
        """파일의 전체 내용을 읽어서 반환합니다."""
        full_path = self._get_full_path(file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        async with await anyio.open_file(full_path, "rb") as f:
            while chunk := await f.read(1024 * 1024):  # 1MB 청크
                yield chunk

    async def read_file_range(
        self, file_path: str, start: int, end: int
    ) -> AsyncGenerator[bytes, None]:
        """파일의 지정된 범위를 읽어서 반환합니다."""
        full_path = self._get_full_path(file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        chunk_size = 1024 * 1024  # 1MB 청크
        
        async with await anyio.open_file(full_path, "rb") as f:
            await f.seek(start)
            pos = await f.tell()
            
            while pos <= end:
                remaining_size = end + 1 - pos
                if remaining_size <= 0:
                    break
                
                read_size = min(chunk_size, remaining_size)
                data = await f.read(read_size)
                
                if not data:
                    break
                
                pos += read_size
                yield data

    async def delete_file(self, file_path: str) -> bool:
        """파일을 삭제합니다."""
        full_path = self._get_full_path(file_path)
        
        try:
            if full_path.exists():
                await anyio.to_thread.run_sync(os.remove, full_path)
                return True
            return False
        except OSError:
            return False

    async def file_exists(self, file_path: str) -> bool:
        """파일이 존재하는지 확인합니다."""
        full_path = self._get_full_path(file_path)
        return full_path.exists()

    async def get_file_size(self, file_path: str) -> int:
        """파일 크기를 반환합니다."""
        full_path = self._get_full_path(file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return full_path.stat().st_size

    def save_file_sync(self, file_stream: BinaryIO, file_path: str) -> str:
        """파일을 로컬 디스크에 동기 방식으로 저장합니다."""
        full_path = self._get_full_path(file_path)
        
        # 상위 디렉토리 생성
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 파일 저장
        with open(full_path, "wb") as f:
            while chunk := file_stream.read(1024 * 1024):  # 1MB 청크
                f.write(chunk)
        
        return str(file_path)

    def delete_file_sync(self, file_path: str) -> bool:
        """파일을 동기 방식으로 삭제합니다."""
        full_path = self._get_full_path(file_path)
        
        try:
            if full_path.exists():
                os.remove(full_path)
                return True
            return False
        except OSError:
            return False

    async def save_file_streaming(
        self, 
        file_path: str,
        chunk_size: int = 1024 * 1024
    ) -> Tuple[Callable[[bytes], Awaitable[None]], Callable[[], Awaitable[None]]]:
        """스트리밍 방식으로 파일을 저장하기 위한 컨텍스트를 반환합니다."""
        full_path = self._get_full_path(file_path)
        
        # 상위 디렉토리 생성
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 실제 파일 스트림 생성
        file_stream = await anyio.open_file(full_path, mode="wb")
        
        async def write_chunk(chunk: bytes) -> None:
            """청크를 파일에 쓴다"""
            await file_stream.write(chunk)
        
        async def finalize() -> None:
            """파일 저장 완료"""
            await file_stream.aclose()
        
        return write_chunk, finalize 

    async def move_file(self, old_path: str, new_path: str) -> None:
        """파일을 이동하거나 이름을 변경합니다."""
        old_full_path = self._get_full_path(old_path)
        new_full_path = self._get_full_path(new_path)

        if not await anyio.to_thread.run_sync(old_full_path.exists):
            raise FileNotFoundError(f"Source file not found: {old_path}")

        try:
            # 새 경로의 상위 디렉토리 생성
            await anyio.to_thread.run_sync(
                lambda: new_full_path.parent.mkdir(parents=True, exist_ok=True)
            )
            # 파일 이동
            await anyio.to_thread.run_sync(old_full_path.rename, new_full_path)
        except OSError as e:
            # app.core.exceptions.StorageError 임포트 필요
            from app.core.exceptions import StorageError
            raise StorageError(f"Failed to move file from {old_path} to {new_path}: {e}") 