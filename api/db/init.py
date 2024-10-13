from sqlmodel import Session, SQLModel

from api.db.core import engine

# Must import these SQLModel db classes to initialize relationships properly
from api.db.model import User, Post


def init_db():
    SQLModel.metadata.create_all(engine)
