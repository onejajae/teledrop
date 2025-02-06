import uuid
import os
import anyio.to_thread
import hashlib

from pathlib import Path
from datetime import datetime, timezone

from typing import Literal
from typing import BinaryIO

from api.config import Settings

from api.repositories.content_repository import ContentRepositoryInterface

from api.models import ContentCreate, ContentUpdate, AuthData
from api.exceptions import *


class ContentService:
    def __init__(
        self, content_repository: ContentRepositoryInterface, settings: Settings
    ):
        self.content_repository = content_repository
        self.settings = settings

    async def create(
        self,
        file_stream: BinaryIO,
        file_name: str,
        file_type: str,
        file_size: int,
        key: str,
        password: str | None,
        title: str | None,
        description: str | None,
        user_only: bool = False,
    ):
        file_uuid = str(uuid.uuid4())
        file_hash = hashlib.sha256()

        write_path = Path(self.settings.SHARE_DIRECTORY) / file_uuid

        async with await anyio.open_file(write_path, mode="wb") as f:
            while chunk := await anyio.to_thread.run_sync(
                file_stream.read, 1024 * 1024
            ):
                await f.write(chunk)
                file_hash.update(chunk)

        new_content = self.content_repository.create(
            ContentCreate(
                key=key,
                password=password,
                user_only=user_only,
                file_name=file_name,
                file_hash=file_hash.hexdigest(),
                file_type=file_type,
                file_size=file_size,
                location=file_uuid,
                title=title,
                description=description,
                created_at=datetime.now(timezone.utc),
            )
        )

        return new_content

    def list(
        self,
        page: int = 1,
        page_size: int = 10,
        sortby: Literal["created_at", "title", "file_size"] | None = "created_at",
        orderby: Literal["asc", "desc"] | None = "desc",
    ):
        contents = self.content_repository.list(
            filter_params={},
            limit=page_size,
            offset=(page - 1) * page_size,
            sortby=sortby,
            orderby=orderby,
        )

        return contents

    def get_by_id(self, id: uuid.UUID, password: str | None = None):
        content = self.content_repository.get_by_id(id)
        if content is None:
            raise ContentNotExist()

        if content.password != password:
            raise ContentPasswordInvalid()

        return content

    def check_access_permission_by_key(self, key: str, auth_data: AuthData):
        content = self.content_repository.get_by_key(key)
        if content is None:
            raise ContentNotExist()

        if content.user_only:
            if auth_data.username is None:
                raise ContentNeedLogin

        return content

    def get_by_key(self, key: str, password: str | None = None):
        content = self.content_repository.get_by_key(key)
        if content is None:
            raise ContentNotExist()

        if content.password != password:
            raise ContentPasswordInvalid()

        return content

    def delete_by_key(self, key: str, password: str = None):
        content = self.content_repository.get_by_key(key)
        if content is None:
            raise ContentNotExist()

        if content.password != password:
            raise ContentPasswordInvalid()

        delete_path = Path(self.settings.SHARE_DIRECTORY) / content.location
        os.remove(delete_path)

        self.content_repository.delete_by_key(key=key)

    def update_detail(self, key: str, password: str, title: str, description: str):
        content = self.content_repository.get_by_key(key)
        if content is None:
            raise ContentNotExist()

        if content.password != password:
            raise ContentPasswordInvalid()

        new_content = ContentUpdate(
            title=title,
            description=description,
            updated_at=datetime.now(timezone.utc),
        )
        return self.content_repository.update_by_key(key=key, new_content=new_content)

    def update_permission(self, key: str, password: str, user_only: bool):
        content = self.content_repository.get_by_key(key)
        if content is None:
            raise ContentNotExist()

        if content.password != password:
            raise ContentPasswordInvalid()

        new_content = ContentUpdate(
            user_only=user_only,
            updated_at=datetime.now(timezone.utc),
        )
        return self.content_repository.update_by_key(key=key, new_content=new_content)

    def update_password(self, key: str, new_password: str):
        content = self.content_repository.get_by_key(key)
        if content is None:
            raise ContentNotExist()

        new_content = ContentUpdate(
            password=new_password,
            updated_at=datetime.now(timezone.utc),
        )
        return self.content_repository.update_by_key(key=key, new_content=new_content)

    def update_favorite_by_key(self, key: str, password: str, favorite: bool):
        content = self.content_repository.get_by_key(key)
        if content is None:
            raise ContentNotExist()

        if content.password != password:
            raise ContentPasswordInvalid()

        new_content = ContentUpdate(
            favorite=favorite,
            updated_at=datetime.now(timezone.utc),
        )

        return self.content_repository.update_by_key(key=key, new_content=new_content)

    def generate_key(self):
        return uuid.uuid4().hex

    def is_key_valid(self, key: str):
        if key == "api":
            return False

        if key == "":
            return False

        content = self.content_repository.get_by_key(key)
        return content is None

    async def get_file_range_by_key(
        self, key: str, start: int, end: int, password: str | None = None
    ):
        content = self.content_repository.get_by_key(key)

        if content is None:
            raise ContentNotExist()

        if content.password != password:
            raise ContentPasswordInvalid()

        file_path = Path(self.settings.SHARE_DIRECTORY) / content.location

        return self.__read_file_range(file_path, start, end)

    async def __read_file_range(
        self, path: Path, start: int, end: int, chunk_size: int = 1024 * 1024
    ):
        async with await anyio.open_file(path, "rb") as f:
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
