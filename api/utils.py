import jwt
from typing import BinaryIO

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from api.db.model import User, Post
from api.config import Settings


def create_access_token(
    user: User, settings: Settings, expires_delta: timedelta | None = None
):
    if expires_delta is None:
        expires_delta = timedelta(minutes=15)
    
    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.now(tz=timezone.utc) + expires_delta,
    }

    return jwt.encode(
        payload, key=settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )


async def validate_key(key: str, session: Session):
    if key == "api":
        return False

    if key == "":
        return False

    statement = select(Post).where(Post.key == key)
    post = session.exec(statement).one_or_none()

    return post is None


# reference: reusable streaming response for any filetypes
# https://github.com/fastapi/fastapi/issues/1240#issuecomment-1055396884
def send_bytes_range_requests(
    file_obj: BinaryIO, start: int, end: int, chunk_size: int = 10_000
):
    """Send a file in chunks using Range Requests specification RFC7233

    `start` and `end` parameters are inclusive due to specification
    """
    with file_obj as f:
        f.seek(start)
        while (pos := f.tell()) <= end:
            read_size = min(chunk_size, end + 1 - pos)
            yield f.read(read_size)
