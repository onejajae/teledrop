from abc import ABC, abstractmethod

from sqlmodel import Session, select
from sqlalchemy import func

from typing import Literal

from api.db.model import Post
from api.schemas.post.post_schema import PostCreate
from api.schemas.post.repository import (
    PostRepositoryCreate,
    PostRepositoryRead,
    PostRepositoryUpdate,
)


class PostRepositoryInterface(ABC):
    @abstractmethod
    def create(self, post: PostRepositoryCreate) -> PostRepositoryRead:
        pass

    @abstractmethod
    def list(
        self,
        filter_params: dict,
        limit: int = 10,
        offset: int = 0,
        sortby: Literal["created_at", "title", "filesize"] | None = "created_at",
        orderby: Literal["asc", "desc"] | None = "desc",
    ) -> list[PostRepositoryRead]:
        pass

    @abstractmethod
    def get_by_id(self, id: int) -> PostRepositoryRead:
        pass

    @abstractmethod
    def get_by_key(self, key: str) -> PostRepositoryRead:
        pass

    @abstractmethod
    def update_by_key(
        self, key: str, new_post: PostRepositoryUpdate
    ) -> PostRepositoryRead:
        pass

    @abstractmethod
    def delete_by_key(self, key: str):
        pass


class SQLAlchemyPostRepository(PostRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def create(self, post: PostRepositoryCreate):
        new_post = Post(**post.model_dump())
        self.db.add(new_post)
        self.db.commit()
        self.db.refresh(new_post)
        return new_post

    def list(
        self,
        filter_params: dict,
        limit: int = 10,
        offset: int = 0,
        sortby: Literal["created_at", "title", "filesize"] | None = "created_at",
        orderby: Literal["asc", "desc"] | None = "desc",
    ) -> list[PostRepositoryRead]:

        sort_column = getattr(Post, sortby)
        if sortby == "title":
            sort_column = func.coalesce(Post.title, Post.filename)

        if orderby == "asc":
            sort_column = sort_column.asc()
        else:
            sort_column = sort_column.desc()

        filter = [getattr(Post, key) == value for key, value in filter_params.items()]
        query = (
            select(Post)
            .where(*filter)
            .order_by(sort_column)
            .limit(limit)
            .offset(offset)
        )

        return self.db.exec(query).fetchall()

    def get_by_id(self, id: int):
        return self.db.get(Post, id)

    def get_by_key(self, key: str) -> PostRepositoryRead:
        query = select(Post).where(Post.key == key)
        return self.db.exec(query).one_or_none()

    def update_by_key(
        self, key: str, new_post: PostRepositoryUpdate
    ) -> PostRepositoryRead:
        query = select(Post).where(Post.key == key)
        post = self.db.exec(query).one_or_none()

        if post is None:
            return None

        new_post = new_post.model_dump(exclude_unset=True)
        post.sqlmodel_update(new_post)

        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)

        return post

    def delete_by_key(self, key: str):
        query = select(Post).where(Post.key == key)
        post = self.db.exec(query).one_or_none()
        self.db.delete(post)
        self.db.commit()
