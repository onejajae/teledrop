import pathlib
import aiofiles.os

from sqlalchemy.orm import Session
from sqlalchemy import select
from db.model import Upload, Content, User


from config import Settings


async def file_delete(key: str, db: Session, settings: Settings):
    q = select(Upload).join(Content).where(Upload.key == key)
    upload = db.execute(q).scalar()

    q = select(Content).join(Upload).where(Upload.key == key)
    content = db.execute(q).scalar()

    file_path = pathlib.Path(settings.share_directory) / content.location
    await aiofiles.os.remove(file_path)

    db.delete(upload)
    db.delete(content)
    db.commit()
