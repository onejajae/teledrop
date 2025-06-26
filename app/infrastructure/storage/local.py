"""로컬 파일 시스템 스토리지 구현

로컬 디스크를 사용하는 스토리지 백엔드 구현입니다.
기존 content_service.py의 파일 처리 로직을 참고하여 작성되었습니다.
"""

import os
import anyio
import anyio.to_thread
from pathlib import Path
from typing import AsyncGenerator, BinaryIO
from contextlib import asynccontextmanager

from .base import StorageInterface
from app.core.exceptions import StorageError


class LocalStorage(StorageInterface):
    """로컬 파일 시스템을 사용하는 스토리지 구현"""

    def __init__(self, base_path: str = "share", read_chunk_size: int = 1024 * 1024 * 8, write_chunk_size: int = 1024 * 1024 * 4):
        """LocalStorage 초기화
        
        Args:
            base_path: 파일이 저장될 기본 디렉토리 경로
            read_chunk_size: 파일 읽기 시 사용할 청크 크기 (기본 8MB)
            write_chunk_size: 파일 쓰기 시 사용할 청크 크기 (기본 4MB)
        """
        self.base_path = Path(base_path)
        self._storage_type = "local"  # 스토리지 타입 속성 추가
        self.read_chunk_size = read_chunk_size
        self.write_chunk_size = write_chunk_size

    @property
    def storage_type(self) -> str:
        """스토리지 타입을 반환합니다."""
        return self._storage_type

    def _get_full_path(self, file_path: str) -> Path:
        """상대 경로를 전체 경로로 변환"""
        return self.base_path / file_path

    @asynccontextmanager
    async def _write_stream(self, file_path: str):
        """파일 쓰기를 위한 스트림 컨텍스트 매니저 (내부 구현)"""
        full_path = self._get_full_path(file_path)
        
        # 상위 디렉토리 생성
        await anyio.to_thread.run_sync(
            lambda: full_path.parent.mkdir(parents=True, exist_ok=True)
        )
        
        # 스토리지 파일 스트림 생성 (저장용)
        storage_stream = await anyio.open_file(full_path, mode="wb")
        
        try:
            yield storage_stream  # 스토리지 저장 스트림 반환
        finally:
            await storage_stream.aclose()

    async def read(
        self, 
        file_path: str, 
        start: int | None = None, 
        end: int | None = None
    ) -> AsyncGenerator[bytes, None]:
        """파일의 내용을 읽어서 반환합니다."""
        full_path = self._get_full_path(file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        async with await anyio.open_file(full_path, "rb") as f:
            # 범위 읽기인 경우
            if start is not None or end is not None:
                # 시작 위치 설정
                if start is not None:
                    await f.seek(start)
                    pos = start
                else:
                    pos = 0
                
                # 끝 위치 설정 (None이면 파일 끝까지)
                if end is None:
                    # 파일 크기 확인
                    await f.seek(0, 2)  # 파일 끝으로 이동
                    file_size = await f.tell()
                    end = file_size - 1
                    await f.seek(pos)  # 원래 시작 위치로 복귀
                
                # 범위 내에서 청크 단위로 읽기
                while pos <= end:
                    remaining_size = end + 1 - pos
                    if remaining_size <= 0:
                        break
                    
                    read_size = min(self.read_chunk_size, remaining_size)
                    data = await f.read(read_size)
                    
                    if not data:
                        break
                    
                    pos += len(data)
                    yield data
            else:
                # 전체 파일 읽기
                while chunk := await f.read(self.read_chunk_size):
                    yield chunk

    async def delete(self, file_path: str) -> bool:
        """파일을 삭제합니다."""
        full_path = self._get_full_path(file_path)
        
        try:
            if full_path.exists():
                await anyio.to_thread.run_sync(os.remove, full_path)
                return True
            return False
        except OSError:
            return False

    async def exists(self, file_path: str) -> bool:
        """파일이 존재하는지 확인합니다."""
        full_path = self._get_full_path(file_path)
        return full_path.exists()

    async def size(self, file_path: str) -> int:
        """파일 크기를 반환합니다."""
        full_path = self._get_full_path(file_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return full_path.stat().st_size

    async def move(self, old_path: str, new_path: str) -> None:
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
            raise StorageError(f"Failed to move file from {old_path} to {new_path}: {e}") 