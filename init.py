import os

from sqlalchemy import create_engine
from db.model import Base

from config import Settings, get_settings


settings: Settings = get_settings()


engine = create_engine(settings.db_host, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)

if not os.path.isdir(settings.share_directory):
    os.mkdir(settings.share_directory)
