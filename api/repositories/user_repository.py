from abc import ABC, abstractmethod

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from api.db.model import User

# from api.schemas.user_schema import UserCreateData
# from api.schemas.user.service import UserServiceRead
from api.schemas.user.repository import UserRepositoryCreate, UserRepositoryRead

from api.exceptions.user_exceptions import DuplicateUserError


class UserRepositoryInterface(ABC):
    @abstractmethod
    def create(self, user_data: UserRepositoryCreate) -> UserRepositoryRead:
        pass

    @abstractmethod
    def get_by_id(self, id: int) -> UserRepositoryRead:
        pass

    @abstractmethod
    def get_by_filter(self, *, filter_params: dict) -> UserRepositoryRead:
        pass

    @abstractmethod
    def list(self) -> list[UserRepositoryRead]:
        pass


class SQLAlchemyUserRepository(UserRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_data: UserRepositoryCreate):
        new_user = User(**user_data.model_dump())
        self.db.add(new_user)

        try:
            self.db.commit()
        except IntegrityError as e:
            raise DuplicateUserError() from e

        self.db.refresh(new_user)
        return new_user

    def get_by_id(self, id: int):
        return self.db.get(User, id)

    def get_by_filter(self, *, filter_params: dict):
        filter = [getattr(User, key) == value for key, value in filter_params.items()]
        query = select(User).where(*filter)
        return self.db.exec(query).one_or_none()

    def list(self):
        query = select(User)
        return self.db.exec(query).fetchall()
