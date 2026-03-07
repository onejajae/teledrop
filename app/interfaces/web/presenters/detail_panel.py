from fastapi import Request, status

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.drop.models import DropMetaQuery
from app.bootstrap.container import DropUseCaseCollection
from app.core.config import Settings
from app.domain.drop.errors import (
    DropAccessDeniedError,
    DropNotFoundError,
    DropPasswordInvalidError,
)
from app.domain.drop.policies import normalize_drop_password
from app.interfaces.web.presenters.common import (
    as_template_drop,
    drop_file_urls,
    drop_preview_page_url,
    csrf_token_for_request,
    templates,
)


async def detail_panel_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    drop_use_cases: DropUseCaseCollection,
    settings: Settings,
    selected_key: str | None = None,
    selected_password: str | None = None,
    detail_error_message: str | None = None,
    detail_status_message: str | None = None,
) -> dict:
    normalized_password = normalize_drop_password(selected_password)
    detail_error_code: str | None = None
    selected_drop = None
    selected_requires_password = False
    selected_download_url = None
    selected_preview_url = None
    selected_page_preview_url = (
        drop_preview_page_url(selected_key, None)
        if selected_key
        else None
    )

    if selected_key:
        try:
            drop_meta = await drop_use_cases.get_drop_meta_use_case.execute_for_display(
                slug=selected_key,
                auth=AuthIdentity(username=auth_data.username),
            )
        except DropAccessDeniedError:
            detail_error_message = detail_error_message or "이 파일을 보려면 로그인이 필요합니다."
            detail_error_code = detail_error_code or "forbidden"
        except DropNotFoundError:
            detail_error_message = detail_error_message or "파일이 존재하지 않습니다."
            detail_error_code = detail_error_code or "not_found"
        else:
            selected_requires_password = bool(drop_meta.requires_password)
            try:
                selected = await drop_use_cases.get_drop_meta_use_case.execute(
                    DropMetaQuery(
                        slug=selected_key,
                        drop_password=normalized_password,
                        auth=AuthIdentity(username=auth_data.username),
                    )
                )
            except DropPasswordInvalidError:
                if normalized_password:
                    detail_error_message = (
                        detail_error_message or "비밀번호가 올바르지 않습니다."
                    )
                    detail_error_code = detail_error_code or "password_invalid"
                else:
                    detail_error_code = detail_error_code or "password_required"
                selected_drop = as_template_drop(drop_meta)
            except DropAccessDeniedError:
                detail_error_message = detail_error_message or "파일을 불러올 수 없습니다."
                detail_error_code = detail_error_code or "forbidden"
            except DropNotFoundError:
                detail_error_message = detail_error_message or "파일을 불러올 수 없습니다."
                detail_error_code = detail_error_code or "not_found"
            else:
                selected_drop = as_template_drop(selected)
                selected_download_url, selected_preview_url = drop_file_urls(
                    selected_key,
                    normalized_password,
                )

    return {
        "request": request,
        "is_login": bool(auth_data.username),
        "selected_key": selected_key,
        "selected_password": normalized_password,
        "selected_drop": selected_drop,
        "selected_requires_password": selected_requires_password,
        "selected_download_url": selected_download_url,
        "selected_preview_url": selected_preview_url,
        "selected_page_preview_url": selected_page_preview_url,
        "csrf_token": csrf_token_for_request(request, settings, csrf_service),
        "detail_error_message": detail_error_message,
        "detail_error_code": detail_error_code,
        "detail_status_message": detail_status_message,
    }


async def render_detail_panel(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    drop_use_cases: DropUseCaseCollection,
    settings: Settings,
    status_code: int = status.HTTP_200_OK,
    selected_key: str | None = None,
    selected_password: str | None = None,
    detail_error_message: str | None = None,
    detail_status_message: str | None = None,
):
    context = await detail_panel_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        drop_use_cases=drop_use_cases,
        settings=settings,
        selected_key=selected_key,
        selected_password=selected_password,
        detail_error_message=detail_error_message,
        detail_status_message=detail_status_message,
    )
    return templates(settings).TemplateResponse(
        request=request,
        name="panels/drop_detail.html",
        context=context,
        status_code=status_code,
    )
