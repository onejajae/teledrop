import re
import unicodedata
from collections.abc import AsyncIterator, Callable, Mapping
from urllib import parse

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from app.application.drop.models import DropDetailDTO
from app.core.exceptions import InvalidRangeHeader, RangeNotSatisfiable
from app.core.utils import parse_range_header


INLINE_PREVIEW_MIME_TYPES = frozenset(
    {
        "image/avif",
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    }
)
INLINE_PREVIEW_MIME_PREFIXES = ("video/",)
RFC5987_SAFE_CHARS = "!#$&+-.^_`|~"
CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]+")
ASCII_FALLBACK_UNSAFE_RE = re.compile(r"[^A-Za-z0-9._ -]+")
WHITESPACE_RE = re.compile(r"\s+")
MAX_DOWNLOAD_FILENAME_LENGTH = 180

StreamRangeIterator = Callable[[str, int, int], AsyncIterator[bytes]]


def _is_inline_preview_mime_type(mime_type: str) -> bool:
    return mime_type in INLINE_PREVIEW_MIME_TYPES or any(
        mime_type.startswith(prefix) for prefix in INLINE_PREVIEW_MIME_PREFIXES
    )


def _safe_download_filename(file_name: str | None) -> str:
    raw_name = unicodedata.normalize("NFC", file_name or "")
    leaf_name = raw_name.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = CONTROL_CHARS_RE.sub(" ", leaf_name)
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()
    if cleaned in {"", ".", ".."}:
        cleaned = "download"
    cleaned = cleaned.replace("/", "_").replace("\\", "_")
    cleaned = cleaned[:MAX_DOWNLOAD_FILENAME_LENGTH].strip(" .")
    return cleaned or "download"


def _ascii_filename_fallback(file_name: str) -> str:
    fallback = unicodedata.normalize("NFKD", file_name)
    fallback = fallback.encode("ascii", "ignore").decode("ascii")
    fallback = CONTROL_CHARS_RE.sub(" ", fallback)
    fallback = ASCII_FALLBACK_UNSAFE_RE.sub("_", fallback)
    fallback = WHITESPACE_RE.sub(" ", fallback).strip(" .")
    fallback = fallback.replace('"', "_").replace("\\", "_").replace(";", "_")
    fallback = fallback[:MAX_DOWNLOAD_FILENAME_LENGTH].strip(" .")
    return fallback or "download"


def _content_disposition_header(disposition_type: str, file_name: str | None) -> str:
    safe_name = _safe_download_filename(file_name)
    fallback = _ascii_filename_fallback(safe_name)
    encoded_name = parse.quote(safe_name, safe=RFC5987_SAFE_CHARS)
    return (
        f'{disposition_type}; filename="{fallback}"; '
        f"filename*=UTF-8''{encoded_name}"
    )


def _invalid_range_header_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST)


def _range_not_satisfiable_exception(file_size: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
        headers={"Content-Range": f"bytes */{file_size}"},
    )


def build_drop_stream_response(
    *,
    detail: DropDetailDTO,
    storage_key: str,
    iter_stream_range: StreamRangeIterator,
    range_header: str | None,
    disposition: str,
    extra_headers: Mapping[str, str] | None = None,
) -> StreamingResponse:
    disposition_type = (
        "inline"
        if disposition == "inline" and _is_inline_preview_mime_type(detail.mime_type)
        else "attachment"
    )

    headers = {
        "Content-Disposition": _content_disposition_header(
            disposition_type,
            detail.file_name,
        ),
        "content-type": detail.mime_type,
        "x-content-type-options": "nosniff",
        "accept-ranges": "bytes",
        "content-encoding": "identity",
        "content-length": str(detail.size_bytes),
        "access-control-expose-headers": (
            "content-type, content-disposition, accept-ranges, content-length, "
            "content-range, content-encoding"
        ),
    }
    if extra_headers:
        headers.update(extra_headers)

    start = 0
    end = detail.size_bytes - 1
    status_code = status.HTTP_200_OK

    if range_header is not None:
        try:
            start, end = parse_range_header(range_header, detail.size_bytes)
        except InvalidRangeHeader:
            raise _invalid_range_header_exception()
        except RangeNotSatisfiable:
            raise _range_not_satisfiable_exception(detail.size_bytes)

        headers["content-length"] = str(end - start + 1)
        headers["content-range"] = f"bytes {start}-{end}/{detail.size_bytes}"
        status_code = status.HTTP_206_PARTIAL_CONTENT

    return StreamingResponse(
        content=iter_stream_range(storage_key, start, end),
        status_code=status_code,
        headers=headers,
        media_type=detail.mime_type,
    )
