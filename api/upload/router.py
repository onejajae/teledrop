import uuid

from fastapi import APIRouter, Depends
from fastapi import HTTPException, status
from fastapi import Form, UploadFile, File

from sqlalchemy.orm import Session
from db.core import get_db

from api.common.service import is_key_exist
from .service import upload
from .schema import UploadComplete

from api.auth.service import validate_access_token, get_user
from api.auth.router import get_current_user

from config import Settings, get_settings


router = APIRouter()


@router.post("/upload/", response_model=UploadComplete)
async def upload_file(
    key: str = Form(default=None),
    title: str = Form(default=None),
    description: str | None = Form(default=None),
    password: str | None = Form(default=None),
    is_anonymous: bool = Form(...),
    user_only: bool = Form(default=False),
    current_user=Depends(get_current_user),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    print(current_user)
    if settings.need_login and current_user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if user_only is None and current_user is None:
        print("error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if current_user is None:
        user_id = None
    else:
        user_id = current_user.id

    if key is None:
        key = str(uuid.uuid4())

    if is_key_exist(key=key, db=db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    if title is None:
        title = file.filename

    if description is not None:
        description = description.strip()

    file_size = 0
    print(file.size)
    for chunk in file.file:
        file_size += len(chunk)
        if file_size > 1024 * 1024 * 1024 * 1:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    await file.seek(0)
    data = await file.read()

    result = await upload(
        data=data,
        key=key,
        title=title,
        filename=file.filename,
        mime=file.content_type,
        description=description,
        password=password,
        is_anonymous=True,
        user_only=user_only,
        user_id=user_id,
        db=db,
        settings=settings,
    )

    return result
