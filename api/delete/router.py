from fastapi import APIRouter, Depends
from fastapi import HTTPException, status

from sqlalchemy.orm import Session
from db.core import get_db
from sqlalchemy import select
from db.model import Upload, Content

from api.common.service import is_key_exist, file_password_vaildation
from api.download.service import get_info

from api.auth.router import get_current_user
from .service import file_delete
from config import Settings, get_settings

router = APIRouter()


@router.delete("/{key}")
async def delete_file(
    key: str,
    password: str = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not is_key_exist(key, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    file_info, user_id = await get_info(key, db, settings)

    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if not file_password_vaildation(key, password, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    await file_delete(key, db, settings)
