import hashlib

from fastapi import Request, Response

from app.core.config import Settings
from app.domain.drop.grants import DropPasswordCredential
from app.domain.drop.policies import normalize_drop_password

DROP_GRANT_COOKIE_PREFIX = "tdg_"


def drop_grant_cookie_name(slug: str) -> str:
    slug_hash = hashlib.sha256(slug.encode("utf-8")).hexdigest()
    return f"{DROP_GRANT_COOKIE_PREFIX}{slug_hash}"


def get_drop_grant_from_request(request: Request, settings: Settings, slug: str) -> str | None:
    return request.cookies.get(drop_grant_cookie_name(slug))


def build_drop_password_credential(
    *,
    password: str | None = None,
    grant_token: str | None = None,
) -> DropPasswordCredential | None:
    normalized_password = normalize_drop_password(password)
    if normalized_password is None and grant_token is None:
        return None
    return DropPasswordCredential(
        password=normalized_password,
        grant_token=grant_token,
    )


def request_drop_password_credential(
    request: Request,
    settings: Settings,
    slug: str,
    *,
    password: str | None = None,
) -> DropPasswordCredential | None:
    return build_drop_password_credential(
        password=password,
        grant_token=get_drop_grant_from_request(request, settings, slug),
    )


def set_drop_grant_cookie(
    response: Response,
    settings: Settings,
    slug: str,
    grant_token: str,
):
    response.set_cookie(
        key=drop_grant_cookie_name(slug),
        value=grant_token,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=settings.SESSION_TTL_SECONDS,
        path=settings.SESSION_COOKIE_PATH,
    )


def clear_drop_grant_cookie(response: Response, settings: Settings, slug: str):
    response.delete_cookie(
        key=drop_grant_cookie_name(slug),
        path=settings.SESSION_COOKIE_PATH,
    )


def clear_drop_grant_cookies(response: Response, request: Request, settings: Settings):
    for cookie_name in list(request.cookies.keys()):
        if cookie_name.startswith(DROP_GRANT_COOKIE_PREFIX):
            response.delete_cookie(
                key=cookie_name,
                path=settings.SESSION_COOKIE_PATH,
            )
