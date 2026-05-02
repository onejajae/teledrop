from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.application.auth.models import ApiKeyDTO, CreatedApiKeyDTO
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.auth.types import AuthIdentity
from app.application.drop.models import DropDetailDTO, DropListItemDTO
from app.bootstrap.runtime_paths import template_dir
from app.core.auth import clear_session_cookie, get_session_id_from_request
from app.core.config import Settings
from app.interfaces.web.theme_config import web_theme
from app.interfaces.web.presenters.view_models import (
    ApiKeyVM,
    CreatedApiKeyVM,
    DropVM,
)

_CLEAR_SESSION_COOKIE_ATTR = "clear_session_cookie_pending"


def configure_templates(templates: Jinja2Templates) -> Jinja2Templates:
    templates.env.globals["web_theme"] = web_theme()
    return templates


def templates() -> Jinja2Templates:
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


def mark_session_cookie_for_clear(request: Request):
    setattr(request.state, _CLEAR_SESSION_COOKIE_ATTR, True)


def finalize_ui_response(request: Request, response: Response, settings: Settings) -> Response:
    if getattr(request.state, _CLEAR_SESSION_COOKIE_ATTR, False):
        clear_session_cookie(response, settings)
        setattr(request.state, _CLEAR_SESSION_COOKIE_ATTR, False)
    return response


def build_query_url(url: str, **params: str | None) -> str:
    serialized = [
        f"{key}={quote(value, safe='')}"
        for key, value in params.items()
        if value is not None
    ]
    if not serialized:
        return url
    return f"{url}?{'&'.join(serialized)}"


def unauthorized_ui_response(request: Request, settings: Settings):
    if request.headers.get("HX-Request") == "true":
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        response.headers["HX-Redirect"] = "/"
        return finalize_ui_response(request, response, settings)
    return finalize_ui_response(
        request,
        RedirectResponse(url="/", status_code=status.HTTP_302_FOUND),
        settings,
    )


def base_template_context(
    request: Request,
    auth_data: AuthIdentity,
    settings: Settings,
    csrf_service: CsrfTokenService,
    **extra: object,
) -> dict[str, object]:
    is_authenticated = bool(
        getattr(auth_data, "is_authenticated", getattr(auth_data, "user_id", None))
        or getattr(auth_data, "username", None)
    )
    context: dict[str, object] = {
        "request": request,
        "is_login": is_authenticated,
        "csrf_token": csrf_token_for_request(request, settings, csrf_service),
    }
    context.update(extra)
    return context


def drop_file_url(slug: str) -> str:
    encoded_slug = quote(slug, safe="")
    return f"/api/drop/{encoded_slug}"


def drop_page_url(slug: str) -> str:
    encoded_slug = quote(slug, safe="")
    return f"/{encoded_slug}"


def drop_unlock_action_url(slug: str) -> str:
    encoded_slug = quote(slug, safe="")
    return f"/actions/drop/{encoded_slug}/unlock"


def drop_manage_page_url(slug: str) -> str:
    encoded_slug = quote(slug, safe="")
    return f"/drops/{encoded_slug}"


def drop_access_status_badge(
    selected_drop: DropVM | None,
) -> tuple[str | None, str | None, str | None]:
    if selected_drop is None:
        return None, None, None
    if selected_drop.access_scope == "private":
        return "비공개", "warning", "soft"
    return "공유 중", "success", "soft"


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


def as_drop_vm(item: DropListItemDTO | DropDetailDTO) -> DropVM:
    slug = item.slug
    size_human = _humanize_size_jedec(item.size_bytes)
    created_at_label = _format_datetime_label_ko(item.created_at)
    updated_at_label = _format_datetime_label_ko(item.updated_at)
    created_at_relative = _format_relative_time_ko(item.created_at)
    return DropVM(
        owner_user_id=getattr(item, "owner_user_id", ""),
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


def as_api_key_vm(item: ApiKeyDTO) -> ApiKeyVM:
    now = datetime.now(tz=timezone.utc)
    expires_at = item.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    return ApiKeyVM(
        public_id=item.public_id,
        name=item.name,
        created_at=item.created_at,
        expires_at=expires_at,
        last_used_at=item.last_used_at,
        revoked_at=item.revoked_at,
        is_active=item.revoked_at is None and (expires_at is None or expires_at > now),
    )


def as_created_api_key_vm(item: CreatedApiKeyDTO) -> CreatedApiKeyVM:
    return CreatedApiKeyVM(key=item.key)
