from sqlmodel import create_engine, Session
from api.config import get_settings

settings = get_settings()

echo = False if settings.APP_MODE == "prod" else True

engine = create_engine(settings.SQLITE_HOST, echo=False)


def get_session():
    with Session(engine) as session:
        yield session
