from fastapi import HTTPException, Response, status

from app.domain.drop.errors import (
    DropAccessDeniedError,
    DropNotFoundError,
    DropPasswordInvalidError,
    DropUploadTooLargeError,
)


def _api_auth_unauthorized_headers(set_cookie: str | None = None) -> dict[str, str]:
    headers = {"WWW-Authenticate": "Session, ApiKey"}
    if set_cookie is not None:
        headers["set-cookie"] = set_cookie
    return headers


def response_set_cookie_header(response: Response) -> str | None:
    return response.headers.get("set-cookie")


def api_auth_unauthorized_exception(
    *,
    detail: str,
    set_cookie: str | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers=_api_auth_unauthorized_headers(set_cookie),
        detail=detail,
    )


def session_unauthorized_exception(
    *,
    detail: str,
    set_cookie: str | None = None,
) -> HTTPException:
    return api_auth_unauthorized_exception(detail=detail, set_cookie=set_cookie)


def login_invalid_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


def slug_unavailable_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug is unavailable.")


def drop_list_unauthorized_exception() -> HTTPException:
    return api_auth_unauthorized_exception(
        detail="Authentication credentials were not provided or are invalid."
    )


def invalid_range_header_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST)


def range_not_satisfiable_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE)


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
