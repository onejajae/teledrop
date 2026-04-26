import hashlib
import os
import uuid
from contextlib import suppress
from pathlib import Path
from typing import AsyncIterator, BinaryIO

import anyio
import anyio.to_thread

from app.domain.drop.errors import DropUploadTooLargeError


class LocalFileStorage:
    def __init__(self, share_directory: str):
        self.share_directory = Path(share_directory)

    async def write_stream(
        self, file_stream: BinaryIO, *, max_bytes: int | None = None
    ) -> tuple[str, str]:
        self.share_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with suppress(OSError):
            os.chmod(self.share_directory, 0o700)

        storage_key = str(uuid.uuid4())
        write_path = self.share_directory / storage_key
        digest = hashlib.sha256()
        written = 0

        try:
            async with await anyio.open_file(write_path, mode="wb") as f:
                while chunk := await anyio.to_thread.run_sync(file_stream.read, 1024 * 1024):
                    written += len(chunk)
                    if max_bytes is not None and written > max_bytes:
                        raise DropUploadTooLargeError()
                    await f.write(chunk)
                    digest.update(chunk)
            with suppress(OSError):
                os.chmod(write_path, 0o600)
        except Exception:
            with suppress(FileNotFoundError, OSError):
                os.remove(write_path)
            raise

        return storage_key, digest.hexdigest()

    async def discard_upload(self, storage_key: str) -> None:
        await anyio.to_thread.run_sync(self._discard_upload_sync, storage_key)

    def _discard_upload_sync(self, storage_key: str) -> None:
        path = self._storage_path(storage_key)
        with suppress(FileNotFoundError, OSError):
            os.remove(path)

    async def stage_delete(self, storage_key: str) -> tuple[str, str | None]:
        return await anyio.to_thread.run_sync(self._stage_delete_sync, storage_key)

    def _stage_delete_sync(self, storage_key: str) -> tuple[str, str | None]:
        source_path = self._storage_path(storage_key)
        if not source_path.exists():
            return storage_key, None

        pending_dir = self.share_directory / ".pending_delete"
        pending_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        with suppress(OSError):
            os.chmod(pending_dir, 0o700)
        staged_name = f"{Path(storage_key).name}.{uuid.uuid4().hex}.delete"
        staged_path = pending_dir / staged_name
        os.replace(source_path, staged_path)
        return storage_key, staged_name

    async def rollback_staged_delete(self, source_key: str, staged_key: str) -> None:
        await anyio.to_thread.run_sync(self._rollback_staged_delete_sync, source_key, staged_key)

    def _rollback_staged_delete_sync(self, source_key: str, staged_key: str) -> None:
        source_path = self._storage_path(source_key)
        staged_path = self._pending_delete_path(staged_key)
        source_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged_path, source_path)

    async def finalize_staged_delete(self, staged_key: str) -> None:
        await anyio.to_thread.run_sync(self._finalize_staged_delete_sync, staged_key)

    def _finalize_staged_delete_sync(self, staged_key: str) -> None:
        staged_path = self._pending_delete_path(staged_key)
        with suppress(FileNotFoundError, OSError):
            os.remove(staged_path)

    async def stream_range(
        self, storage_key: str, start: int, end: int, chunk_size: int = 1024 * 1024
    ) -> AsyncIterator[bytes]:
        path = self._storage_path(storage_key)
        async with await anyio.open_file(path, mode="rb") as f:
            await f.seek(start)
            pos = await f.tell()
            while pos <= end:
                remaining = end + 1 - pos
                if remaining <= 0:
                    break
                data = await f.read(min(chunk_size, remaining))
                if not data:
                    break
                pos += len(data)
                yield data

    def _storage_path(self, storage_key: str) -> Path:
        key_name = Path(storage_key).name
        if key_name != storage_key or not key_name:
            raise ValueError("Invalid storage key.")
        path = (self.share_directory / key_name).resolve()
        share_root = self.share_directory.resolve()
        if path.parent != share_root:
            raise ValueError("Invalid storage key.")
        return path

    def _pending_delete_path(self, staged_key: str) -> Path:
        key_name = Path(staged_key).name
        if key_name != staged_key or not key_name:
            raise ValueError("Invalid staged delete key.")
        return self.share_directory / ".pending_delete" / key_name
