from fastapi import Request

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.drop.models import DropMetaQuery
from app.application.drop.use_cases import GetDropMetaUseCase
from app.core.config import Settings
from app.domain.drop.errors import (
    DropAccessDeniedError,
    DropNotFoundError,
    DropPasswordInvalidError,
)
from app.domain.drop.policies import normalize_drop_password
from app.interfaces.web.presenters.common import (
    as_template_drop,
    base_template_context,
    drop_file_urls,
    drop_preview_page_url,
)


async def detail_panel_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    get_drop_meta_use_case: GetDropMetaUseCase,
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
            drop_meta = await get_drop_meta_use_case.execute_for_display(
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
                selected = await get_drop_meta_use_case.execute(
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

    return base_template_context(
        request=request,
        auth_data=auth_data,
        settings=settings,
        csrf_service=csrf_service,
        selected_key=selected_key,
        selected_password=normalized_password,
        selected_drop=selected_drop,
        selected_requires_password=selected_requires_password,
        selected_download_url=selected_download_url,
        selected_preview_url=selected_preview_url,
        selected_page_preview_url=selected_page_preview_url,
        detail_error_message=detail_error_message,
        detail_error_code=detail_error_code,
        detail_status_message=detail_status_message,
    )
