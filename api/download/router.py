from fastapi import APIRouter, Depends
from fastapi import HTTPException, status
from fastapi.responses import FileResponse

from sqlalchemy.orm import Session
from db.core import get_db

from api.common.service import is_key_exist, file_password_vaildation
from api.auth.router import get_current_user
from .service import get_info, download, get_list

from .schema import DownloadPreview, UploadListElement

from config import Settings, get_settings


router = APIRouter()


@router.get("/preview/{key}", response_model=DownloadPreview)
async def get_file_info(
    key: str,
    password: str = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not is_key_exist(key, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    file_info, user_id = await get_info(key, db, settings)

    if file_info.user_only and current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if file_info.user_only and user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if not file_password_vaildation(key, password, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return file_info


@router.get("/download/{key}")
async def download_file(
    key: str,
    password: str = None,
    access_token: str = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not is_key_exist(key, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if current_user is None and access_token is None:
        current_user = None

    if current_user is None and access_token is not None:
        current_user = await get_current_user(
            access_token=access_token, db=db, settings=settings
        )

    file_path, filename, user_id, user_only = await download(
        key=key, db=db, settings=settings
    )

    if user_only and current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if user_only and user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if not file_password_vaildation(key, password, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return FileResponse(file_path, filename=filename)


@router.post("/list/", response_model=list[UploadListElement])
async def get_file_list(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return await get_list(current_user.id, db, settings)
