from collections.abc import Awaitable, Callable

from fastapi import APIRouter, File, Form, Request, Response, UploadFile, status
from fastapi.responses import RedirectResponse

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.drop.models import (
    CreateDropCommand,
    DeleteDropCommand,
    UpdateDropCommand,
)
from app.bootstrap.container import AppContainer, AppContainerDep, SettingsDep
from app.core.config import Settings
from app.domain.drop.errors import (
    DropNotFoundError,
    DropPasswordInvalidError,
    DropSlugUnavailableError,
)
from app.domain.drop.policies import normalize_drop_password
from app.domain.drop.value_objects import AccessScope
from app.interfaces.deps.auth import OptionalSessionAuthDep
from app.interfaces.deps.common import CsrfTokenServiceDep
from app.interfaces.web.action_support import (
    is_hx_request,
    require_auth_and_csrf,
)
from app.interfaces.web.presenters.common import drop_manage_page_url
from app.interfaces.web.presenters.detail_panel import render_detail_panel
from app.interfaces.web.presenters.manage_page import render_manage_page
from app.interfaces.web.presenters.upload_panel import render_upload_panel


router = APIRouter(prefix="/actions/drop")


def _redirect_to(url: str, *, hx_request: bool) -> Response:
    if hx_request:
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        response.headers["HX-Redirect"] = url
        return response
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


async def _guard_upload_mutation(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    csrf_token: str,
) -> Response | None:
    async def on_csrf_failure() -> Response:
        return render_upload_panel(
            request=request,
            auth_data=auth_data,
            csrf_service=csrf_service,
            settings=settings,
            status_code=status.HTTP_403_FORBIDDEN,
            upload_error_message="유효하지 않은 CSRF 토큰입니다.",
        )

    return await require_auth_and_csrf(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        csrf_token=csrf_token,
        on_csrf_failure=on_csrf_failure,
    )


async def _guard_manage_mutation(
    request: Request,
    slug: str,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    drop_use_cases: AppContainer,
    settings: Settings,
    csrf_token: str,
    password: str | None,
) -> Response | None:
    normalized_password = normalize_drop_password(password)

    async def on_csrf_failure() -> Response:
        return await render_manage_page(
            request=request,
            auth_data=auth_data,
            csrf_service=csrf_service,
            get_drop_meta_use_case=drop_use_cases.get_drop_meta_use_case,
            settings=settings,
            slug=slug,
            password=normalized_password,
            status_code=status.HTTP_403_FORBIDDEN,
            detail_error_message="유효하지 않은 CSRF 토큰입니다.",
        )

    return await require_auth_and_csrf(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        csrf_token=csrf_token,
        on_csrf_failure=on_csrf_failure,
    )


async def _render_manage_exception(
    *,
    request: Request,
    slug: str,
    password: str | None,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    drop_use_cases: AppContainer,
    settings: Settings,
    exc: Exception,
) -> Response:
    if isinstance(exc, DropNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
        error_message = "파일이 존재하지 않습니다."
    elif isinstance(exc, DropPasswordInvalidError):
        status_code = status.HTTP_401_UNAUTHORIZED
        error_message = "현재 비밀번호가 올바르지 않습니다."
    else:
        raise exc

    return await render_manage_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=drop_use_cases.get_drop_meta_use_case,
        settings=settings,
        slug=slug,
        password=normalize_drop_password(password),
        status_code=status_code,
        detail_error_message=error_message,
    )


async def _handle_drop_mutation(
    *,
    request: Request,
    slug: str,
    status_message: str,
    csrf_token: str,
    password: str | None,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    drop_use_cases: AppContainer,
    settings: Settings,
    mutation: Callable[[], Awaitable[object]],
    success_redirect_url: str | None = None,
    expected_exceptions: tuple[type[Exception], ...] = (
        DropNotFoundError,
        DropPasswordInvalidError,
    ),
) -> Response:
    normalized_password = normalize_drop_password(password)
    guard_response = await _guard_manage_mutation(
        request=request,
        slug=slug,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        csrf_token=csrf_token,
        password=normalized_password,
    )
    if guard_response is not None:
        return guard_response

    try:
        await mutation()
    except expected_exceptions as exc:
        return await _render_manage_exception(
            request=request,
            slug=slug,
            password=normalized_password,
            auth_data=auth_data,
            csrf_service=csrf_service,
            drop_use_cases=drop_use_cases,
            settings=settings,
            exc=exc,
        )

    if success_redirect_url is not None:
        return _redirect_to(success_redirect_url, hx_request=is_hx_request(request))

    return await render_manage_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=drop_use_cases.get_drop_meta_use_case,
        settings=settings,
        slug=slug,
        password=normalized_password,
        detail_status_message=status_message,
    )


@router.post("/{slug}/open")
async def ui_open_drop_detail(
    slug: str,
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalSessionAuthDep,
    csrf_service: CsrfTokenServiceDep,
    drop_use_cases: AppContainerDep,
    password: str | None = Form(default=None),
    csrf_token: str = Form(default=""),
):
    normalized_password = normalize_drop_password(password)

    async def on_csrf_failure() -> Response:
        return await render_detail_panel(
            request=request,
            auth_data=auth_data,
            csrf_service=csrf_service,
            get_drop_meta_use_case=drop_use_cases.get_drop_meta_use_case,
            settings=settings,
            status_code=status.HTTP_403_FORBIDDEN,
            selected_key=slug,
            selected_password=normalized_password,
            detail_error_message="유효하지 않은 CSRF 토큰입니다.",
        )

    guard_response = await require_auth_and_csrf(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        csrf_token=csrf_token,
        on_csrf_failure=on_csrf_failure,
    )
    if guard_response is not None:
        return guard_response

    return await render_detail_panel(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=drop_use_cases.get_drop_meta_use_case,
        settings=settings,
        selected_key=slug,
        selected_password=normalized_password,
    )


@router.post("/upload")
async def ui_upload(
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalSessionAuthDep,
    csrf_service: CsrfTokenServiceDep,
    drop_use_cases: AppContainerDep,
    file: UploadFile = File(),
    slug: str | None = Form(default=None),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    password: str | None = Form(default=None),
    user_only: bool = Form(default=True),
    csrf_token: str = Form(default=""),
):
    guard_response = await _guard_upload_mutation(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
        csrf_token=csrf_token,
    )
    if guard_response is not None:
        return guard_response

    size_bytes = file.size
    if size_bytes is None:
        current_pos = file.file.tell()
        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(current_pos)

    access_scope = AccessScope.PRIVATE if user_only else AccessScope.PUBLIC

    try:
        created = await drop_use_cases.create_drop_use_case.execute(
            CreateDropCommand(
                file_stream=file.file,
                file_name=file.filename,
                mime_type=file.content_type,
                size_bytes=size_bytes,
                slug=slug,
                access_scope=access_scope,
                drop_password=normalize_drop_password(password),
                title=title,
                description=description,
            )
        )
    except DropSlugUnavailableError:
        return render_upload_panel(
            request=request,
            auth_data=auth_data,
            csrf_service=csrf_service,
            settings=settings,
            status_code=status.HTTP_409_CONFLICT,
            upload_error_message="이미 사용 중이거나 사용할 수 없는 URL 입니다.",
        )

    return _redirect_to(drop_manage_page_url(created.slug), hx_request=is_hx_request(request))


@router.post("/{slug}/detail")
async def ui_update_drop_detail(
    slug: str,
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalSessionAuthDep,
    csrf_service: CsrfTokenServiceDep,
    drop_use_cases: AppContainerDep,
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    password: str | None = Form(default=None),
    csrf_token: str = Form(default=""),
):
    return await _handle_drop_mutation(
        request=request,
        slug=slug,
        status_message="메타데이터가 수정되었습니다.",
        csrf_token=csrf_token,
        password=password,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        mutation=lambda: drop_use_cases.update_drop_use_case.execute(
            UpdateDropCommand(
                slug=slug,
                current_password=normalize_drop_password(password),
                title=title,
                description=description,
            )
        ),
    )


@router.post("/{slug}/favorite")
async def ui_update_drop_favorite(
    slug: str,
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalSessionAuthDep,
    csrf_service: CsrfTokenServiceDep,
    drop_use_cases: AppContainerDep,
    favorite: bool = Form(),
    password: str | None = Form(default=None),
    csrf_token: str = Form(default=""),
):
    return await _handle_drop_mutation(
        request=request,
        slug=slug,
        status_message="즐겨찾기 설정이 변경되었습니다.",
        csrf_token=csrf_token,
        password=password,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        mutation=lambda: drop_use_cases.update_drop_use_case.execute(
            UpdateDropCommand(
                slug=slug,
                current_password=normalize_drop_password(password),
                is_favorite=favorite,
            )
        ),
    )


@router.post("/{slug}/access")
async def ui_update_drop_access(
    slug: str,
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalSessionAuthDep,
    csrf_service: CsrfTokenServiceDep,
    drop_use_cases: AppContainerDep,
    user_only: bool = Form(),
    password: str | None = Form(default=None),
    csrf_token: str = Form(default=""),
):
    access_scope = AccessScope.PRIVATE if user_only else AccessScope.PUBLIC
    return await _handle_drop_mutation(
        request=request,
        slug=slug,
        status_message="공유가 중단되었습니다." if user_only else "공유가 시작되었습니다.",
        csrf_token=csrf_token,
        password=password,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        mutation=lambda: drop_use_cases.update_drop_use_case.execute(
            UpdateDropCommand(
                slug=slug,
                current_password=normalize_drop_password(password),
                access_scope=access_scope,
            )
        ),
    )


@router.post("/{slug}/password")
async def ui_update_drop_password(
    slug: str,
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalSessionAuthDep,
    csrf_service: CsrfTokenServiceDep,
    drop_use_cases: AppContainerDep,
    new_password: str | None = Form(default=None),
    current_password: str | None = Form(default=None),
    csrf_token: str = Form(default=""),
):
    return await _handle_drop_mutation(
        request=request,
        slug=slug,
        status_message="드롭 비밀번호가 변경되었습니다.",
        csrf_token=csrf_token,
        password=current_password,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        mutation=lambda: drop_use_cases.update_drop_use_case.execute(
            UpdateDropCommand(
                slug=slug,
                current_password=normalize_drop_password(current_password),
                new_password=normalize_drop_password(new_password),
            )
        ),
        expected_exceptions=(DropNotFoundError, DropPasswordInvalidError),
    )


@router.post("/{slug}/delete")
async def ui_delete_drop(
    slug: str,
    request: Request,
    settings: SettingsDep,
    auth_data: OptionalSessionAuthDep,
    csrf_service: CsrfTokenServiceDep,
    drop_use_cases: AppContainerDep,
    password: str | None = Form(default=None),
    csrf_token: str = Form(default=""),
):
    return await _handle_drop_mutation(
        request=request,
        slug=slug,
        status_message="드롭이 삭제되었습니다.",
        csrf_token=csrf_token,
        password=password,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        success_redirect_url="/drops",
        mutation=lambda: drop_use_cases.delete_drop_use_case.execute(
            DeleteDropCommand(
                slug=slug,
                current_password=normalize_drop_password(password),
            )
        ),
    )
