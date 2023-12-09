import pathlib

from sqlalchemy.orm import Session
from sqlalchemy import select
from db.model import Upload, Content, User

from .schema import DownloadPreview, UploadListElement

from config import Settings


async def get_info(key: str, db: Session, settings: Settings):
    q = select(Upload).join(Content).where(Upload.key == key)
    upload = db.execute(q).scalar()

    return (
        DownloadPreview(
            filename=upload.filename,
            file_size=upload.content.size,
            content_type=upload.content.mime,
            title=upload.title,
            description=upload.description,
            datetime=upload.datetime,
            key=upload.key,
            is_anonymous=upload.is_anonymous,
            user_only=upload.user_only,
            url=f"{settings.api_server_host}/api/download/{upload.key}",
        ),
        upload.user_id,
    )


async def download(
    key: str,
    db: Session,
    settings: Settings,
):
    q = select(Upload).join(Content).where(Upload.key == key)
    upload = db.execute(q).scalar()

    file_path = pathlib.Path(settings.share_directory) / upload.content.location
    filename = upload.filename
    return (file_path, filename, upload.user_id, upload.user_only)


async def get_list(user_id: int, db: Session, settings: Settings):
    q = select(Upload).join(Content).where(Upload.user_id == user_id)
    uploads = db.execute(q).scalars().all()

    return uploads
