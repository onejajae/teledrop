from datetime import datetime, timedelta
from bcrypt import hashpw, gensalt, checkpw
import jwt

from sqlalchemy.orm import Session
from sqlalchemy import select
from db.model import User

from config import Settings


def is_user_exist(username: str, db: Session):
    q = select(User).where(User.username == username)
    user = db.execute(q).one_or_none()

    if user is None:
        return False
    else:
        return True


def get_user(username: str, db: Session):
    q = select(User).where(User.username == username)
    return db.execute(q).scalar_one_or_none()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def authenticate_user(username: str, password: str, db: Session) -> bool:
    user = get_user(username, db)
    return verify_password(password, user.password)


def create_user(username, password: str, db: Session, settings: Settings):
    hashed_password = hashpw(password.encode("utf-8"), gensalt())
    hashed_password = hashed_password.decode("utf-8")

    new_user = User(username=username, password=hashed_password)
    db.add(new_user)
    db.commit()

    return generate_token(username, settings)


def generate_token(username: str, settings: Settings):
    payload = {
        "username": username,
        "exp": datetime.now() + timedelta(minutes=settings.jwt_exp_minute),
    }
    return jwt.encode(
        payload, key=settings.jwt_secret, algorithm=settings.jwt_hash_algorithm
    )


def validate_token(token: str, settings: Settings):
    return jwt.decode(
        token, key=settings.jwt_secret, algorithms=settings.jwt_hash_algorithm
    )


def validate_access_token(token: str, settings: Settings):
    return validate_token(token, settings)
