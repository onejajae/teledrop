from __future__ import annotations

from fastapi import HTTPException, Response, status

from app.domain.drop.errors import (
    DropAccessDeniedError,
    DropNotFoundError,
    DropPasswordInvalidError,
)


def _session_unauthorized_headers(set_cookie: str | None = None) -> dict[str, str]:
    headers = {"WWW-Authenticate": "Session"}
    if set_cookie is not None:
        headers["set-cookie"] = set_cookie
    return headers


def response_set_cookie_header(response: Response) -> str | None:
    return response.headers.get("set-cookie")


def session_unauthorized_exception(
    *,
    detail: str,
    set_cookie: str | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers=_session_unauthorized_headers(set_cookie),
        detail=detail,
    )


def login_invalid_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


def slug_unavailable_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug is unavailable.")


def drop_list_unauthorized_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


def invalid_range_header_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST)


def range_not_satisfiable_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE)


def map_drop_read_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, (DropNotFoundError, DropAccessDeniedError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, DropPasswordInvalidError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    raise exc


def map_drop_mutation_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, DropNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, DropPasswordInvalidError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    raise exc
