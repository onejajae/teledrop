from datetime import datetime, timezone
from types import SimpleNamespace
from urllib.parse import quote

from fastapi import Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.drop.models import DropDetailDTO, DropListItemDTO
from app.bootstrap.runtime_paths import template_dir
from app.core.auth import get_session_id_from_request
from app.core.config import Settings
from app.interfaces.web.theme_config import web_theme


def configure_templates(templates: Jinja2Templates) -> Jinja2Templates:
    templates.env.globals["web_theme"] = web_theme()
    return templates


def templates(settings: Settings) -> Jinja2Templates:
    # Keep the settings parameter for call-site compatibility while template
    # ownership is normalized under app/interfaces/web.
    _ = settings
    return configure_templates(Jinja2Templates(directory=str(template_dir())))


def csrf_token_for_request(
    request: Request, settings: Settings, csrf_service: CsrfTokenService
) -> str | None:
    session_id = get_session_id_from_request(request, settings)
    if not session_id:
        return None
    return csrf_service.generate(session_id)


def csrf_is_valid(
    request: Request,
    settings: Settings,
    csrf_service: CsrfTokenService,
    csrf_token: str | None,
) -> bool:
    session_id = get_session_id_from_request(request, settings)
    if not session_id:
        return False
    return csrf_service.verify(session_id, csrf_token)


def unauthorized_ui_response(request: Request):
    if request.headers.get("HX-Request") == "true":
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        response.headers["HX-Redirect"] = "/"
        return response
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


def normalize_sort_value(sortby: str | None) -> str:
    if sortby == "file_size":
        return "size_bytes"
    return sortby or "created_at"


def drop_file_urls(slug: str, password: str | None) -> tuple[str, str]:
    encoded_slug = quote(slug, safe="")
    if password:
        encoded_password = quote(password, safe="")
        download_url = f"/api/drop/{encoded_slug}?drop_password={encoded_password}"
        preview_url = (
            f"/api/drop/{encoded_slug}?disposition=inline&drop_password={encoded_password}"
        )
    else:
        download_url = f"/api/drop/{encoded_slug}"
        preview_url = f"/api/drop/{encoded_slug}?disposition=inline"

    return download_url, preview_url


def drop_preview_page_url(slug: str, password: str | None) -> str:
    encoded_slug = quote(slug, safe="")
    if password:
        encoded_password = quote(password, safe="")
        return f"/{encoded_slug}?password={encoded_password}"
    return f"/{encoded_slug}"


def drop_manage_page_url(slug: str, password: str | None = None) -> str:
    encoded_slug = quote(slug, safe="")
    if password:
        encoded_password = quote(password, safe="")
        return f"/drops/{encoded_slug}?password={encoded_password}"
    return f"/drops/{encoded_slug}"


def _humanize_size_jedec(size_bytes: int | None) -> str | None:
    if size_bytes is None:
        return None
    if size_bytes < 0:
        return str(size_bytes)

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(size_bytes)
    unit_index = 0
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024.0
        unit_index += 1

    if unit_index == 0:
        return f"{int(value)} {units[unit_index]}"
    if value >= 100:
        return f"{value:.0f} {units[unit_index]}"
    if value >= 10:
        return f"{value:.1f} {units[unit_index]}"
    return f"{value:.2f} {units[unit_index]}"


def _as_local_datetime(value: datetime | None) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone()


def _format_datetime_label_ko(value: datetime | None) -> str | None:
    local_dt = _as_local_datetime(value)
    if local_dt is None:
        return None

    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    weekday = weekdays[local_dt.weekday()]
    return local_dt.strftime(f"%Y-%m-%d ({weekday}) %H:%M:%S")


def _format_relative_time_ko(value: datetime | None, now: datetime | None = None) -> str | None:
    local_dt = _as_local_datetime(value)
    if local_dt is None:
        return None

    if now is None:
        now = datetime.now().astimezone()
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc).astimezone()
    else:
        now = now.astimezone()

    seconds = int((now - local_dt).total_seconds())
    if seconds < 60:
        return "방금 전"
    if seconds < 60 * 60:
        return f"{seconds // 60}분 전"
    if seconds < 60 * 60 * 24:
        return f"{seconds // (60 * 60)}시간 전"
    if seconds < 60 * 60 * 24 * 30:
        return f"{seconds // (60 * 60 * 24)}일 전"
    if seconds < 60 * 60 * 24 * 365:
        return f"{seconds // (60 * 60 * 24 * 30)}개월 전"
    return f"{seconds // (60 * 60 * 24 * 365)}년 전"


def as_template_drop(item: DropListItemDTO | DropDetailDTO) -> SimpleNamespace:
    slug = item.slug
    size_human = _humanize_size_jedec(item.size_bytes)
    created_at_label = _format_datetime_label_ko(item.created_at)
    updated_at_label = _format_datetime_label_ko(item.updated_at)
    created_at_relative = _format_relative_time_ko(item.created_at)
    return SimpleNamespace(
        slug=slug,
        title=item.title,
        description=item.description,
        file_name=item.file_name,
        mime_type=item.mime_type,
        size_bytes=item.size_bytes,
        access_scope=item.access_scope.value,
        is_favorite=item.is_favorite,
        requires_password=item.requires_password,
        created_at=item.created_at,
        updated_at=item.updated_at,
        size_human=size_human,
        created_at_label=created_at_label,
        updated_at_label=updated_at_label,
        created_at_relative=created_at_relative,
    )
