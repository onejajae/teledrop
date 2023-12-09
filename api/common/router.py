from fastapi import APIRouter, Depends
from fastapi import HTTPException, status

from sqlalchemy.orm import Session
from db.core import get_db

from .service import is_key_exist
from api.auth.router import get_current_user

from .schema import KeyCheck

from config import Settings, get_settings

router = APIRouter()


@router.get("/keycheck/", response_model=KeyCheck)
async def get_key_exist(
    key: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if settings.need_login and current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return KeyCheck(key=key, exist=is_key_exist(key, db))
