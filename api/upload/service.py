import pathlib
import aiofiles
import uuid
import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select
from db.model import Upload, Content

from .schema import UploadComplete

from config import Settings


async def upload(
    data: bytes,
    key: str,
    title: str,
    filename: str,
    mime: str,
    description: str | None,
    password: str | None,
    is_anonymous: bool,
    user_only: bool,
    user_id: int | None,
    db: Session,
    settings: Settings,
):
    upload_datetime = datetime.datetime.now()

    file_uuid = str(uuid.uuid4())

    save_path = pathlib.Path(settings.share_directory) / file_uuid
    async with aiofiles.open(save_path, mode="wb+") as f:
        await f.write(data)

    new_content = Content(location=file_uuid, size=len(data), mime=mime, is_url=False)
    db.add(new_content)
    db.flush()

    new_upload = Upload(
        title=title,
        filename=filename,
        description=description,
        datetime=upload_datetime,
        key=key,
        password=password,
        is_anonymous=is_anonymous,
        user_only=user_only,
        user_id=user_id,
        content_id=new_content.id,
    )
    db.add(new_upload)
    db.commit()

    return UploadComplete(
        filename=filename,
        file_size=len(data),
        key=key,
        title=title,
        description=description,
        datetime=upload_datetime,
        is_anonymous=is_anonymous,
        user_id=user_id,
        user_only=user_only,
    )
