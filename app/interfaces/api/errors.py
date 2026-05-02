from fastapi import HTTPException, status

from app.domain.drop.errors import (
    DropAccessDeniedError,
    DropNotFoundError,
    DropPasswordInvalidError,
    DropUploadTooLargeError,
)


def _api_auth_unauthorized_headers(
    set_cookie: str | None = None,
    authenticate: str = "ApiKey",
) -> dict[str, str]:
    headers = {"WWW-Authenticate": authenticate}
    if set_cookie is not None:
        headers["set-cookie"] = set_cookie
    return headers


def api_auth_unauthorized_exception(
    *,
    detail: str,
    set_cookie: str | None = None,
    authenticate: str = "ApiKey",
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers=_api_auth_unauthorized_headers(set_cookie, authenticate),
        detail=detail,
    )


def slug_unavailable_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug is unavailable.")


def drop_list_unauthorized_exception() -> HTTPException:
    return api_auth_unauthorized_exception(
        detail="Authentication credentials were not provided or are invalid."
    )


def upload_too_large_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        detail="Uploaded file exceeds the configured maximum size.",
    )


def map_drop_read_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, (DropNotFoundError, DropAccessDeniedError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, DropPasswordInvalidError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if isinstance(exc, DropUploadTooLargeError):
        return upload_too_large_exception()
    raise exc


def map_drop_mutation_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, (DropNotFoundError, DropAccessDeniedError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, DropPasswordInvalidError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if isinstance(exc, DropUploadTooLargeError):
        return upload_too_large_exception()
    raise exc
