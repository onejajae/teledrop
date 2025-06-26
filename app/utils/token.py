import jwt
from app.core.config import Settings
from app.models.auth import TokenPayload


def create_jwt_token(
    payload: TokenPayload,
    settings: Settings
) -> str:
    return jwt.encode(payload.model_dump(), settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
   

def verify_jwt_token(token: str, settings: Settings) -> TokenPayload | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return TokenPayload(**payload)
    except jwt.PyJWTError:
        return None