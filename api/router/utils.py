from fastapi import APIRouter
from fastapi import HTTPException, status

from sqlmodel import Session

from api.db.model import User
from api.deps import SessionDep, CurrentUser
from api.utils import validate_key


router = APIRouter()


@router.get("/keycheck/")
async def get_key_exist(
    key: str,
    user: User = CurrentUser,
    session: Session = SessionDep,
):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return validate_key(key=key, session=session)
