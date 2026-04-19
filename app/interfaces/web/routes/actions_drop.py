from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile, status
from fastapi.responses import RedirectResponse

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.drop.models import (
    CreateDropCommand,
    DeleteDropCommand,
    DropMetaQuery,
    UpdateDropCommand,
)
from app.application.drop.use_cases import (
    CreateDropUseCase,
    DeleteDropUseCase,
    GetDropMetaUseCase,
    UpdateDropUseCase,
)
from app.bootstrap.container import get_app_settings, get_csrf_token_service
from app.bootstrap.providers.drop import (
    get_create_drop_use_case,
    get_delete_drop_use_case,
    get_drop_password_grant_service,
    get_get_drop_meta_use_case,
    get_update_drop_use_case,
)
from app.core.config import Settings
from app.core.drop_unlock_tokens import verify_drop_unlock_token
from app.core.drop_grants import (
    build_drop_password_credential,
    clear_drop_grant_cookie,
    request_drop_password_credential,
    set_drop_grant_cookie,
)
from app.domain.drop.errors import (
    DropAccessDeniedError,
    DropNotFoundError,
    DropPasswordInvalidError,
    DropSlugUnavailableError,
)
from app.domain.drop.grants import DropPasswordGrantService
from app.domain.drop.policies import normalize_drop_password
from app.domain.drop.value_objects import AccessScope
from app.interfaces.deps.auth import get_optional_session_auth
from app.interfaces.web.action_support import (
    is_hx_request,
    require_auth_and_csrf,
)
from app.interfaces.web.presenters.common import (
    drop_manage_page_url,
    drop_preview_page_url,
    finalize_ui_response,
    unauthorized_ui_response,
)
from app.interfaces.web.presenters.manage_page import render_manage_page
from app.interfaces.web.presenters.shared_page import render_shared_page
from app.interfaces.web.presenters.upload_panel import render_upload_panel


router = APIRouter(prefix="/actions/drop")


def _redirect_to(url: str, *, hx_request: bool) -> Response:
    if hx_request:
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        response.headers["HX-Redirect"] = url
        return response
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


def _request_credential(
    request: Request,
    settings: Settings,
    slug: str,
    *,
    password: str | None = None,
):
    return request_drop_password_credential(
        request,
        settings,
        slug,
        password=password,
    )


def _clear_grant_if_present(
    response: Response,
    request: Request,
    settings: Settings,
    slug: str,
):
    credential = _request_credential(request, settings, slug)
    if credential is not None and credential.grant_token:
        clear_drop_grant_cookie(response, settings, slug)


async def _render_drop_page(
    *,
    target_view: str,
    request: Request,
    slug: str,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    get_drop_meta_use_case: GetDropMetaUseCase,
    settings: Settings,
    status_code: int,
    detail_error_message: str | None = None,
    detail_status_message: str | None = None,
    credential=None,
    use_request_grant: bool = True,
) -> Response:
    if target_view == "manage":
        return await render_manage_page(
            request=request,
            auth_data=auth_data,
            csrf_service=csrf_service,
            get_drop_meta_use_case=get_drop_meta_use_case,
            settings=settings,
            slug=slug,
            credential=credential,
            use_request_grant=use_request_grant,
            status_code=status_code,
            detail_error_message=detail_error_message,
            detail_status_message=detail_status_message,
        )

    return await render_shared_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        slug=slug,
        credential=credential,
        use_request_grant=use_request_grant,
        status_code=status_code,
        detail_error_message=detail_error_message,
        detail_status_message=detail_status_message,
    )


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
    get_drop_meta_use_case: GetDropMetaUseCase,
    settings: Settings,
    csrf_token: str,
) -> Response | None:
    async def on_csrf_failure() -> Response:
        return await render_manage_page(
            request=request,
            auth_data=auth_data,
            csrf_service=csrf_service,
            get_drop_meta_use_case=get_drop_meta_use_case,
            settings=settings,
            slug=slug,
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
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    get_drop_meta_use_case: GetDropMetaUseCase,
    settings: Settings,
    exc: Exception,
) -> Response:
    if isinstance(exc, (DropNotFoundError, DropAccessDeniedError)):
        status_code = status.HTTP_404_NOT_FOUND
        error_message = "파일이 존재하지 않습니다."
    elif isinstance(exc, DropPasswordInvalidError):
        status_code = status.HTTP_401_UNAUTHORIZED
        error_message = "현재 비밀번호가 올바르지 않습니다."
    else:
        raise exc

    response = await render_manage_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        slug=slug,
        use_request_grant=False,
        status_code=status_code,
        detail_error_message=error_message,
    )
    _clear_grant_if_present(response, request, settings, slug)
    return response


async def _handle_drop_mutation(
    *,
    request: Request,
    slug: str,
    status_message: str,
    csrf_token: str,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    get_drop_meta_use_case: GetDropMetaUseCase,
    settings: Settings,
    mutation: Callable[[], Awaitable[object]],
    success_redirect_url: str | None = None,
    clear_grant_on_success: bool = False,
    expected_exceptions: tuple[type[Exception], ...] = (
        DropNotFoundError,
        DropAccessDeniedError,
        DropPasswordInvalidError,
    ),
) -> Response:
    guard_response = await _guard_manage_mutation(
        request=request,
        slug=slug,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        csrf_token=csrf_token,
    )
    if guard_response is not None:
        return guard_response

    try:
        await mutation()
    except expected_exceptions as exc:
        return await _render_manage_exception(
            request=request,
            slug=slug,
            auth_data=auth_data,
            csrf_service=csrf_service,
            get_drop_meta_use_case=get_drop_meta_use_case,
            settings=settings,
            exc=exc,
        )

    if success_redirect_url is not None:
        response = _redirect_to(success_redirect_url, hx_request=is_hx_request(request))
        if clear_grant_on_success:
            clear_drop_grant_cookie(response, settings, slug)
        return finalize_ui_response(request, response, settings)

    return await render_manage_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        slug=slug,
        detail_status_message=status_message,
    )


@router.post("/upload")
async def ui_upload(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    create_drop_use_case: CreateDropUseCase = Depends(get_create_drop_use_case),
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
        created = await create_drop_use_case.execute(
            CreateDropCommand(
                owner_user_id=auth_data.user_id or "",
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

    return finalize_ui_response(
        request,
        _redirect_to(drop_manage_page_url(created.slug), hx_request=is_hx_request(request)),
        settings,
    )


@router.post("/{slug}/unlock")
async def ui_unlock_drop(
    slug: str,
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    get_drop_meta_use_case: GetDropMetaUseCase = Depends(get_get_drop_meta_use_case),
    grant_service: DropPasswordGrantService = Depends(get_drop_password_grant_service),
    password: str | None = Form(default=None),
    target_view: str = Form(default="shared"),
    unlock_token: str = Form(default=""),
):
    normalized_target_view = "manage" if target_view == "manage" else "shared"
    if normalized_target_view == "manage" and not auth_data.is_authenticated:
        return unauthorized_ui_response(request, settings)

    if not verify_drop_unlock_token(
        settings,
        slug=slug,
        target_view=normalized_target_view,
        token=unlock_token,
    ):
        return await _render_drop_page(
            target_view=normalized_target_view,
            request=request,
            slug=slug,
            auth_data=auth_data,
            csrf_service=csrf_service,
            get_drop_meta_use_case=get_drop_meta_use_case,
            settings=settings,
            status_code=status.HTTP_403_FORBIDDEN,
            detail_error_message="페이지를 새로고침 후 다시 시도해 주세요.",
            use_request_grant=False,
        )

    normalized_password = normalize_drop_password(password)
    credential = build_drop_password_credential(password=normalized_password)

    try:
        await get_drop_meta_use_case.execute(
            DropMetaQuery(
                slug=slug,
                drop_password=credential,
                auth=auth_data,
            )
        )
    except DropNotFoundError:
        status_code = status.HTTP_404_NOT_FOUND
        error_message = "파일이 존재하지 않습니다."
    except DropAccessDeniedError:
        status_code = status.HTTP_404_NOT_FOUND
        error_message = "파일이 존재하지 않습니다."
    except DropPasswordInvalidError:
        status_code = status.HTTP_401_UNAUTHORIZED
        error_message = "비밀번호가 올바르지 않습니다."
    else:
        redirect_url = (
            drop_manage_page_url(slug)
            if normalized_target_view == "manage"
            else drop_preview_page_url(slug)
        )
        response = _redirect_to(redirect_url, hx_request=is_hx_request(request))
        issued_grant = grant_service.issue(slug, normalized_password)
        if issued_grant is not None:
            set_drop_grant_cookie(response, settings, slug, issued_grant)
        else:
            clear_drop_grant_cookie(response, settings, slug)
        return finalize_ui_response(request, response, settings)

    response = await _render_drop_page(
        target_view=normalized_target_view,
        request=request,
        slug=slug,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        status_code=status_code,
        detail_error_message=error_message,
        use_request_grant=False,
    )
    clear_drop_grant_cookie(response, settings, slug)
    return finalize_ui_response(request, response, settings)


@router.post("/{slug}/detail")
async def ui_update_drop_detail(
    slug: str,
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    get_drop_meta_use_case: GetDropMetaUseCase = Depends(get_get_drop_meta_use_case),
    update_drop_use_case: UpdateDropUseCase = Depends(get_update_drop_use_case),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    csrf_token: str = Form(default=""),
):
    return await _handle_drop_mutation(
        request=request,
        slug=slug,
        status_message="메타데이터가 수정되었습니다.",
        csrf_token=csrf_token,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        mutation=lambda: update_drop_use_case.execute(
            UpdateDropCommand(
                slug=slug,
                auth=auth_data,
                current_password=None,
                title=title,
                description=description,
            )
        ),
    )


@router.post("/{slug}/favorite")
async def ui_update_drop_favorite(
    slug: str,
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    get_drop_meta_use_case: GetDropMetaUseCase = Depends(get_get_drop_meta_use_case),
    update_drop_use_case: UpdateDropUseCase = Depends(get_update_drop_use_case),
    favorite: bool = Form(),
    csrf_token: str = Form(default=""),
):
    return await _handle_drop_mutation(
        request=request,
        slug=slug,
        status_message="즐겨찾기 설정이 변경되었습니다.",
        csrf_token=csrf_token,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        mutation=lambda: update_drop_use_case.execute(
            UpdateDropCommand(
                slug=slug,
                auth=auth_data,
                current_password=None,
                is_favorite=favorite,
            )
        ),
    )


@router.post("/{slug}/access")
async def ui_update_drop_access(
    slug: str,
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    get_drop_meta_use_case: GetDropMetaUseCase = Depends(get_get_drop_meta_use_case),
    update_drop_use_case: UpdateDropUseCase = Depends(get_update_drop_use_case),
    user_only: bool = Form(),
    csrf_token: str = Form(default=""),
):
    access_scope = AccessScope.PRIVATE if user_only else AccessScope.PUBLIC
    return await _handle_drop_mutation(
        request=request,
        slug=slug,
        status_message="공유가 중단되었습니다." if user_only else "공유가 시작되었습니다.",
        csrf_token=csrf_token,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        mutation=lambda: update_drop_use_case.execute(
            UpdateDropCommand(
                slug=slug,
                auth=auth_data,
                current_password=None,
                access_scope=access_scope,
            )
        ),
    )


@router.post("/{slug}/password")
async def ui_update_drop_password(
    slug: str,
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    get_drop_meta_use_case: GetDropMetaUseCase = Depends(get_get_drop_meta_use_case),
    update_drop_use_case: UpdateDropUseCase = Depends(get_update_drop_use_case),
    grant_service: DropPasswordGrantService = Depends(get_drop_password_grant_service),
    new_password: str | None = Form(default=None),
    confirm_password: str | None = Form(default=None),
    csrf_token: str = Form(default=""),
):
    guard_response = await _guard_manage_mutation(
        request=request,
        slug=slug,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        csrf_token=csrf_token,
    )
    if guard_response is not None:
        return guard_response

    normalized_new_password = normalize_drop_password(new_password)
    normalized_confirm_password = normalize_drop_password(confirm_password)

    if normalized_new_password != normalized_confirm_password:
        return await render_manage_page(
            request=request,
            auth_data=auth_data,
            csrf_service=csrf_service,
            get_drop_meta_use_case=get_drop_meta_use_case,
            settings=settings,
            slug=slug,
            detail_error_message="비밀번호 확인이 일치하지 않습니다.",
        )

    try:
        current_detail = await get_drop_meta_use_case.execute_for_display(slug, auth=auth_data)
        if current_detail.requires_password and normalized_new_password is not None:
            return await render_manage_page(
                request=request,
                auth_data=auth_data,
                csrf_service=csrf_service,
                get_drop_meta_use_case=get_drop_meta_use_case,
                settings=settings,
                slug=slug,
                detail_error_message="비밀번호를 변경하려면 먼저 해제한 뒤 다시 설정해 주세요.",
            )

        await update_drop_use_case.execute(
            UpdateDropCommand(
                slug=slug,
                auth=auth_data,
                current_password=None,
                new_password=normalized_new_password,
            )
        )
    except (DropAccessDeniedError, DropNotFoundError, DropPasswordInvalidError) as exc:
        return await _render_manage_exception(
            request=request,
            slug=slug,
            auth_data=auth_data,
            csrf_service=csrf_service,
            get_drop_meta_use_case=get_drop_meta_use_case,
            settings=settings,
            exc=exc,
        )

    response_credential = None
    issued_grant = grant_service.issue(slug, normalized_new_password)
    if issued_grant is not None:
        response_credential = build_drop_password_credential(grant_token=issued_grant)

    response = await render_manage_page(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        slug=slug,
        credential=response_credential,
        use_request_grant=False,
        detail_status_message=(
            "드롭 비밀번호가 해제되었습니다."
            if normalized_new_password is None
            else "드롭 비밀번호가 설정되었습니다."
        ),
    )
    if issued_grant is not None:
        set_drop_grant_cookie(response, settings, slug, issued_grant)
    else:
        clear_drop_grant_cookie(response, settings, slug)
    return finalize_ui_response(request, response, settings)


@router.post("/{slug}/delete")
async def ui_delete_drop(
    slug: str,
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_data: AuthIdentity = Depends(get_optional_session_auth),
    csrf_service: CsrfTokenService = Depends(get_csrf_token_service),
    get_drop_meta_use_case: GetDropMetaUseCase = Depends(get_get_drop_meta_use_case),
    delete_drop_use_case: DeleteDropUseCase = Depends(get_delete_drop_use_case),
    csrf_token: str = Form(default=""),
):
    return await _handle_drop_mutation(
        request=request,
        slug=slug,
        status_message="드롭이 삭제되었습니다.",
        csrf_token=csrf_token,
        auth_data=auth_data,
        csrf_service=csrf_service,
        get_drop_meta_use_case=get_drop_meta_use_case,
        settings=settings,
        success_redirect_url="/drops",
        clear_grant_on_success=True,
        expected_exceptions=(DropNotFoundError,),
        mutation=lambda: delete_drop_use_case.execute(
            DeleteDropCommand(
                slug=slug,
                auth=auth_data,
                current_password=None,
            )
        ),
    )
