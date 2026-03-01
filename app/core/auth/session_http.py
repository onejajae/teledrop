from fastapi import Request, Response

from app.core.config import Settings


def set_session_cookie(response: Response, settings: Settings, session_id: str):
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=settings.SESSION_TTL_SECONDS,
        path=settings.SESSION_COOKIE_PATH,
    )


def clear_session_cookie(response: Response, settings: Settings):
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path=settings.SESSION_COOKIE_PATH,
    )


def get_session_id_from_request(request: Request, settings: Settings) -> str | None:
    return request.cookies.get(settings.SESSION_COOKIE_NAME)
