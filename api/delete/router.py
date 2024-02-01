from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session
from db.core import get_db

from api.auth.router import get_current_user


router = APIRouter()


@router.delete("/{key}")
async def delete_file(
    key: str,
    password: str = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    print(key, password, current_user)
