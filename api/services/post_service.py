import uuid
import os
import anyio.to_thread
import hashlib

from pathlib import Path
from datetime import datetime, timezone

from typing import Literal
from typing import BinaryIO

from api.config import Settings

from api.repositories.post_repository import PostRepositoryInterface
from api.schemas.post.repository import PostRepositoryCreate, PostRepositoryUpdate
from api.schemas.post.service import (
    PostServiceCreate,
    PostServiceRead,
    PostServiceUpdate,
)
from api.exceptions.post_exceptions import *


class PostService:
    def __init__(self, post_repository: PostRepositoryInterface, settings: Settings):
        self.post_repository = post_repository
        self.settings = settings

    async def create(self, user_id: int, file: BinaryIO, post_data: PostServiceCreate):
        file_uuid = str(uuid.uuid4())
        file_hash = hashlib.sha256()

        write_path = Path(self.settings.SHARE_DIRECTORY) / file_uuid

        async with await anyio.open_file(write_path, mode="wb") as f:
            while chunk := await anyio.to_thread.run_sync(file.read, 1024 * 1024):
                await f.write(chunk)
                file_hash.update(chunk)

        new_post = self.post_repository.create(
            PostRepositoryCreate(
                key=post_data.key,
                is_user_only=post_data.is_user_only,
                password=post_data.password,
                filename=post_data.filename,
                filetype=post_data.filetype,
                filesize=post_data.filesize,
                location=file_uuid,
                title=post_data.title,
                description=post_data.description,
                created_at=datetime.now(timezone.utc),
                user_id=user_id,
            )
        )
        return PostServiceRead(**new_post.model_dump(), user=new_post.user)

    def list(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
        sortby: Literal["created_at", "title", "filesize"] | None = "created_at",
        orderby: Literal["asc", "desc"] | None = "desc",
    ) -> list[PostServiceRead]:
        posts = self.post_repository.list(
            filter_params={"user_id": user_id},
            limit=page_size,
            offset=(page - 1) * page_size,
            sortby=sortby,
            orderby=orderby,
        )

        return [PostServiceRead(**post.model_dump(), user=post.user) for post in posts]

    def get_by_id(self, id: int, user_id: int, password: str | None = None):
        post = self.post_repository.get_by_id(id)
        if post is None:
            raise PostNotExist()

        if post.is_user_only and user_id is None:
            raise PostNeedLogin()

        if post.is_user_only and user_id != post.user.id:
            raise UserNotHavePostPermission()

        if post.password != password:
            raise PostPasswordInvalid()

        return PostServiceRead(**post.model_dump(), user=post.user)

    def get_by_key(self, key: str, user_id: int, password: str | None = None):
        post = self.post_repository.get_by_key(key)
        if post is None:
            raise PostNotExist()

        if post.is_user_only and user_id is None:
            raise PostNeedLogin()

        if post.is_user_only and user_id != post.user.id:
            raise UserNotHavePostPermission()

        if post.password != password:
            raise PostPasswordInvalid()

        return PostServiceRead(**post.model_dump(), user=post.user)

    def update_by_key(
        self,
        key: str,
        user_id: int,
        post_data: PostServiceUpdate,
        password: str | None = None,
    ):
        post = self.post_repository.get_by_key(key)
        if post is None:
            raise PostNotExist()

        if post.is_user_only and user_id is None:
            raise PostNeedLogin()

        if post.is_user_only and user_id != post.user.id:
            raise UserNotHavePostPermission()

        if post.password != password:
            raise PostPasswordInvalid()

        new_post = PostRepositoryUpdate(
            title=post_data.title,
            description=post_data.description,
            favorite=post.favorite,
            is_user_only=post_data.is_user_only,
            updated_at=datetime.now(timezone.utc),
        )

        if post_data.new_password:
            new_post.password = post_data.new_password
        else:
            if post_data.delete_password:
                new_post.password = None

        updated_post = self.post_repository.update_by_key(key=key, new_post=new_post)
        return PostServiceRead(**updated_post.model_dump(), user=updated_post.user)

    def delete_by_key(self, key: str, user_id: int, password: str = None):
        post = self.post_repository.get_by_key(key)
        if post is None:
            raise PostNotExist()

        if post.is_user_only and user_id is None:
            raise PostNeedLogin()

        if post.is_user_only and user_id != post.user.id:
            raise UserNotHavePostPermission()

        if post.password != password:
            raise PostPasswordInvalid()

        delete_path = Path(self.settings.SHARE_DIRECTORY) / post.location
        os.remove(delete_path)

        self.post_repository.delete_by_key(key=key)

    def update_favorite_by_key(
        self, key: str, user_id: int, password: str, favorite: bool
    ):
        post = self.post_repository.get_by_key(key)
        if post is None:
            raise PostNotExist()

        if post.is_user_only and user_id is None:
            raise PostNeedLogin()

        if post.is_user_only and user_id != post.user.id:
            raise UserNotHavePostPermission()

        if post.password != password:
            raise PostPasswordInvalid()

        new_post = PostRepositoryUpdate(
            title=post.title,
            description=post.description,
            favorite=favorite,
            is_user_only=post.is_user_only,
            password=post.password,
            updated_at=datetime.now(timezone.utc),
        )

        updated_post = self.post_repository.update_by_key(key=key, new_post=new_post)
        return PostServiceRead(**updated_post.model_dump(), user=updated_post.user)

    def update_password_by_key(self, key: str, user_id: int, new_password: str):
        post = self.post_repository.get_by_key(key)
        if post is None:
            raise PostNotExist()
        if user_id != post.user.id:
            raise UserNotHavePostPermission()

        new_post = PostRepositoryUpdate(
            title=post.title,
            description=post.description,
            favorite=post.favorite,
            is_user_only=post.is_user_only,
            password=new_password,
            updated_at=datetime.now(timezone.utc),
        )

        updated_post = self.post_repository.update_by_key(key=key, new_post=new_post)
        return PostServiceRead(**updated_post.model_dump(), user=updated_post.user)

    def generate_key(self):
        return str(uuid.uuid4())

    def is_key_valid(self, key: str):
        if key == "api":
            return False

        if key == "":
            return False

        post = self.post_repository.get_by_key(key)
        return post is None

    async def get_file_range_by_key(
        self, user_id: int, key: str, start: int, end: int, password: str | None = None
    ):
        post = self.post_repository.get_by_key(key)
        if post is None:
            raise PostNotExist()

        if post.is_user_only and user_id is None:
            raise PostNeedLogin()

        if post.is_user_only and user_id != post.user.id:
            raise UserNotHavePostPermission()

        if post.password != password:
            raise PostPasswordInvalid()

        file_path = Path(self.settings.SHARE_DIRECTORY) / post.location

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
