from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlmodel import Session

from app.bootstrap.container import get_app_container


def get_session(request: Request) -> Generator[Session, None, None]:
    container = get_app_container(request)
    session = container.db_session_factory()
    try:
        yield session
    finally:
        session.close()


DbSessionDep = Annotated[Session, Depends(get_session)]
