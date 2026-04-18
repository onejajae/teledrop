from fastapi import Request

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.drop.models import DropMetaQuery
from app.application.drop.use_cases import GetDropMetaUseCase
from app.core.config import Settings
from app.core.drop_unlock_tokens import issue_drop_unlock_token
from app.core.drop_grants import (
    build_drop_password_credential,
    request_drop_password_credential,
)
from app.domain.drop.grants import DropPasswordCredential
from app.domain.drop.errors import (
    DropAccessDeniedError,
    DropNotFoundError,
    DropPasswordInvalidError,
)
from app.interfaces.web.presenters.common import (
    as_drop_vm,
    base_template_context,
    drop_file_urls,
    drop_preview_page_url,
    drop_unlock_action_url,
)
from app.interfaces.web.presenters.view_models import (
    DetailErrorVM,
    DetailFormsVM,
    DetailUrlsVM,
    DetailVM,
)


async def detail_panel_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    get_drop_meta_use_case: GetDropMetaUseCase,
    settings: Settings,
    selected_key: str | None = None,
    selected_password: str | None = None,
    credential: DropPasswordCredential | None = None,
    use_request_grant: bool = True,
    detail_error_message: str | None = None,
    detail_status_message: str | None = None,
) -> dict:
    detail_error_code: str | None = None
    selected_drop = None
    selected_requires_password = False
    selected_download_url = None
    selected_preview_url = None
    access_granted = False
    invalid_grant = False
    selected_page_preview_url = (
        drop_preview_page_url(selected_key)
        if selected_key
        else None
    )
    selected_prompt_action = (
        drop_unlock_action_url(selected_key)
        if selected_key
        else None
    )

    if selected_key:
        effective_credential = credential
        if effective_credential is None and selected_password is not None:
            effective_credential = build_drop_password_credential(password=selected_password)
        if effective_credential is None and use_request_grant:
            effective_credential = request_drop_password_credential(
                request,
                settings,
                selected_key,
            )

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
                        drop_password=effective_credential,
                        auth=AuthIdentity(username=auth_data.username),
                    )
                )
            except DropPasswordInvalidError:
                has_raw_password = bool(effective_credential and effective_credential.password)
                has_grant_token = bool(effective_credential and effective_credential.grant_token)
                if has_raw_password:
                    detail_error_message = (
                        detail_error_message or "비밀번호가 올바르지 않습니다."
                    )
                    detail_error_code = detail_error_code or "password_invalid"
                else:
                    detail_error_code = detail_error_code or "password_required"
                invalid_grant = has_grant_token and not has_raw_password
                selected_drop = as_drop_vm(drop_meta)
            except DropAccessDeniedError:
                detail_error_message = detail_error_message or "파일을 불러올 수 없습니다."
                detail_error_code = detail_error_code or "forbidden"
            except DropNotFoundError:
                detail_error_message = detail_error_message or "파일을 불러올 수 없습니다."
                detail_error_code = detail_error_code or "not_found"
            else:
                selected_drop = as_drop_vm(selected)
                selected_download_url, selected_preview_url = drop_file_urls(selected_key)
                access_granted = True

    detail = DetailVM(
        key=selected_key,
        drop=selected_drop,
        requires_password=selected_requires_password,
        access_granted=access_granted,
        invalid_grant=invalid_grant,
        status_message=detail_status_message,
        error=DetailErrorVM(
            message=detail_error_message,
            code=detail_error_code,
        ),
        urls=DetailUrlsVM(
            download=selected_download_url,
            preview=selected_preview_url,
            page=selected_page_preview_url,
        ),
        forms=DetailFormsVM(
            locked_prompt_action=selected_prompt_action,
            unlock_token=(
                issue_drop_unlock_token(settings, selected_key, "shared")
                if selected_key
                else None
            ),
        ),
    )
    return base_template_context(
        request=request,
        auth_data=auth_data,
        settings=settings,
        csrf_service=csrf_service,
        detail=detail,
    )
