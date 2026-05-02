from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from app.application.auth.types import AuthIdentity
from app.application.drop.models import DropStreamQuery
from app.application.drop.use_cases import GetDropStreamSourceUseCase
from app.bootstrap.container import get_app_settings
from app.bootstrap.providers.drop import get_get_drop_stream_source_use_case
from app.core.config import Settings
from app.core.drop_grants import request_drop_password_credential
from app.domain.drop.errors import (
    DropAccessDeniedError,
    DropNotFoundError,
    DropPasswordInvalidError,
    DropUploadTooLargeError,
)
from app.interfaces.deps.auth import get_optional_session_auth
from app.interfaces.drop_streaming import build_drop_stream_response


router = APIRouter(prefix="/files")

TRUSTED_FETCH_SITES = frozenset({"same-origin", "none"})
EMBED_FETCH_DESTS = frozenset({"audio", "embed", "iframe", "image", "object", "video"})
WEB_FILE_RESPONSE_HEADERS = {
    "Cache-Control": "no-store, private, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
    "Vary": "Cookie, Sec-Fetch-Site, Sec-Fetch-Mode, Sec-Fetch-Dest",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Content-Security-Policy": "frame-ancestors 'self'",
    "X-Frame-Options": "SAMEORIGIN",
}


def _map_web_file_read_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, (DropNotFoundError, DropAccessDeniedError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, DropPasswordInvalidError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if isinstance(exc, DropUploadTooLargeError):
        return HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE)
    raise exc


def _reject_cross_site_embed(request: Request) -> None:
    fetch_site = request.headers.get("Sec-Fetch-Site", "").lower()
    fetch_dest = request.headers.get("Sec-Fetch-Dest", "").lower()
    if (
        fetch_site
        and fetch_site not in TRUSTED_FETCH_SITES
        and fetch_dest in EMBED_FETCH_DESTS
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


@router.get("/{slug}")
async def web_drop_file(
    slug: str,
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    get_drop_stream_source_use_case: GetDropStreamSourceUseCase = Depends(
        get_get_drop_stream_source_use_case
    ),
    range_header: str | None = Header(default=None, alias="Range"),
    disposition: str = Query(default="attachment"),
):
    _reject_cross_site_embed(request)

    try:
        detail, storage_key = await get_drop_stream_source_use_case.execute(
            DropStreamQuery(
                slug=slug,
                drop_password=request_drop_password_credential(request, settings, slug),
                auth=auth_data,
            )
        )
    except Exception as exc:
        raise _map_web_file_read_exception(exc)

    return build_drop_stream_response(
        detail=detail,
        storage_key=storage_key,
        iter_stream_range=get_drop_stream_source_use_case.iter_stream_range,
        range_header=range_header,
        disposition=disposition,
        extra_headers=WEB_FILE_RESPONSE_HEADERS,
    )
