from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from config import get_settings

settings = get_settings()

engine = create_engine(settings.db_host, connect_args={"check_same_thread": False})
db_session = sessionmaker(bind=engine)


def get_db():
    db = db_session()
    try:
        yield db
    finally:
        db.close()
