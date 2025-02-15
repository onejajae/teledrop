import uuid
from abc import ABC, abstractmethod

from sqlmodel import Session, select

from api.models import APIKey, APIKeyRead, APIKeyCreate, APIKeyUpdate


class APIKeyRepositoryInterface(ABC):
    @abstractmethod
    def create(self, api_key: APIKeyCreate) -> APIKey:
        pass

    @abstractmethod
    def list(self) -> list[APIKeyRead]:
        pass

    @abstractmethod
    def get_by_id(self, id: uuid.UUID) -> APIKeyRead:
        pass

    @abstractmethod
    def get_by_key(self, key: str) -> APIKeyRead:
        pass

    @abstractmethod
    def update_by_key(self, key: str, new_api_key: APIKeyUpdate) -> APIKeyRead:
        pass

    @abstractmethod
    def delete_by_key(self, key: str):
        pass


class SQLAlchemyAPIKeyRepository(APIKeyRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def create(self, api_key: APIKeyCreate):
        new_api_key = APIKey(**api_key.model_dump())
        self.db.add(new_api_key)
        self.db.commit()
        self.db.refresh(new_api_key)
        return new_api_key

    def list(self):
        query = select(APIKey)
        return self.db.exec(query).fetchall()

    def get_by_id(self, id: uuid.UUID):
        return self.db.get(APIKey, id)

    def get_by_key(self, key: str):
        query = select(APIKey).where(APIKey.key == key)
        return self.db.exec(query).one_or_none()

    def update_by_key(self, key: str, new_api_key: APIKeyUpdate):
        query = select(APIKey).where(APIKey.key == key)
        api_key = self.db.exec(query).one_or_none()

        if api_key is None:
            return None

        new_api_key = new_api_key.model_dump(exclude_unset=True)
        api_key.sqlmodel_update(new_api_key)

        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)

        return api_key

    def delete_by_key(self, key: str):
        query = select(APIKey).where(APIKey.key == key)
        api_key = self.db.exec(query).one_or_none()
        self.db.delete(api_key)
        self.db.commit()
