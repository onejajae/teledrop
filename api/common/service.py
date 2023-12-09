from sqlalchemy.orm import Session
from sqlalchemy import select
from db.model import Upload


def is_key_exist(key: str, db: Session):
    if key == "api":
        return False

    q = select(Upload.key).where(Upload.key == key)
    res = db.execute(q).scalar()

    if res:
        return True
    else:
        return False


def file_password_vaildation(key: str, password: str, db: Session):
    q = select(Upload.key, Upload.password).where(Upload.key == key)
    res = db.execute(q).one()
    return password == res.password
