import uuid
from abc import ABC, abstractmethod

from sqlmodel import Session, select
from sqlalchemy import func

from typing import Literal

from api.models import ContentRead, ContentCreate, Content, ContentUpdate


class ContentRepositoryInterface(ABC):
    @abstractmethod
    def create(self, content: ContentCreate) -> ContentRead:
        pass

    @abstractmethod
    def list(
        self,
        filter_params: dict,
        limit: int = 10,
        offset: int = 0,
        sortby: Literal["created_at", "title", "filesize"] | None = "created_at",
        orderby: Literal["asc", "desc"] | None = "desc",
    ) -> list[ContentRead]:
        pass

    @abstractmethod
    def get_by_id(self, id: uuid.UUID) -> ContentRead:
        pass

    @abstractmethod
    def get_by_key(self, key: str) -> ContentRead:
        pass

    @abstractmethod
    def update_by_key(self, key: str, new_content) -> ContentRead:
        pass

    @abstractmethod
    def delete_by_key(self, key: str):
        pass


class SQLAlchemyContentRepository(ContentRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def create(self, content: ContentCreate):
        new_content = Content(**content.model_dump())
        self.db.add(new_content)
        self.db.commit()
        self.db.refresh(new_content)
        return new_content

    def list(
        self,
        filter_params: dict,
        limit: int = 10,
        offset: int = 0,
        sortby: Literal["created_at", "title", "file_size"] | None = "created_at",
        orderby: Literal["asc", "desc"] | None = "desc",
    ):

        sort_column = getattr(Content, sortby)
        if sortby == "title":
            sort_column = func.coalesce(Content.title, Content.file_name)

        if orderby == "asc":
            sort_column = sort_column.asc()
        else:
            sort_column = sort_column.desc()

        filter = [
            getattr(Content, key) == value for key, value in filter_params.items()
        ]
        query = (
            select(Content)
            .where(*filter)
            .order_by(sort_column)
            .limit(limit)
            .offset(offset)
        )

        return self.db.exec(query).fetchall()

    def get_by_id(self, id: uuid.UUID):
        return self.db.get(Content, id)

    def get_by_key(self, key: str):
        query = select(Content).where(Content.key == key)
        return self.db.exec(query).one_or_none()

    def update_by_key(self, key: str, new_content: ContentUpdate):
        query = select(Content).where(Content.key == key)
        content = self.db.exec(query).one_or_none()

        if content is None:
            return None

        new_content = new_content.model_dump(exclude_unset=True)
        content.sqlmodel_update(new_content)

        self.db.add(content)
        self.db.commit()
        self.db.refresh(content)

        return content

    def delete_by_key(self, key: str):
        query = select(Content).where(Content.key == key)
        post = self.db.exec(query).one_or_none()
        self.db.delete(post)
        self.db.commit()
