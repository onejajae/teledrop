from sqlmodel import Session, SQLModel

from api.db.core import engine

# Must import these SQLModel db classes to initialize relationships properly
from api.models import Content


def init_db():
    SQLModel.metadata.create_all(engine)
