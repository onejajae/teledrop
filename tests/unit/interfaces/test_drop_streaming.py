from datetime import datetime, timezone

from app.application.drop.models import DropDetailDTO
from app.domain.drop.value_objects import AccessScope
from app.interfaces.drop_streaming import build_drop_stream_response


def _detail(file_name: str) -> DropDetailDTO:
    now = datetime.now(timezone.utc)
    return DropDetailDTO(
        owner_user_id="user-1",
        slug="k1",
        title=None,
        description=None,
        file_name=file_name,
        mime_type="application/octet-stream",
        size_bytes=5,
        access_scope=AccessScope.PRIVATE,
        is_favorite=False,
        requires_password=False,
        created_at=now,
        updated_at=None,
        sha256="sha-k1",
    )


async def _iter_stream_range(_storage_key: str, start: int, end: int):
    yield b"hello"[start : end + 1]


def _stream_response(file_name: str):
    return build_drop_stream_response(
        detail=_detail(file_name),
        storage_key="storage-k1",
        iter_stream_range=_iter_stream_range,
        range_header=None,
        disposition="attachment",
    )


def test_content_disposition_strips_path_like_file_names():
    response = _stream_response("../secret\\report.pdf")

    assert response.headers["content-disposition"] == (
        "attachment; filename=\"report.pdf\"; filename*=UTF-8''report.pdf"
    )


def test_content_disposition_uses_ascii_fallback_and_utf8_filename_star():
    response = _stream_response("보고서 final.pdf")

    assert response.headers["content-disposition"] == (
        "attachment; filename=\"final.pdf\"; "
        "filename*=UTF-8''%EB%B3%B4%EA%B3%A0%EC%84%9C%20final.pdf"
    )


def test_content_disposition_removes_header_control_characters():
    response = _stream_response("evil\r\nx: y.txt")
    header = response.headers["content-disposition"]

    assert "\r" not in header
    assert "\n" not in header
    assert header == (
        "attachment; filename=\"evil x_ y.txt\"; "
        "filename*=UTF-8''evil%20x%3A%20y.txt"
    )


def test_stream_response_exposes_content_disposition_to_cors_clients():
    response = _stream_response("report.pdf")

    exposed = response.headers["access-control-expose-headers"]
    assert "content-disposition" in exposed
