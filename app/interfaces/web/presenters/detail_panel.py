from fastapi import Request

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.application.drop.models import DropMetaQuery
from app.application.drop.use_cases import GetDropMetaUseCase
from app.core.config import Settings
from app.core.drop_unlock_tokens import issue_drop_unlock_token
from app.core.drop_grants import request_drop_password_credential
from app.domain.drop.grants import DropPasswordCredential
from app.domain.drop.errors import (
    DropAccessDeniedError,
    DropNotFoundError,
    DropPasswordInvalidError,
)
from app.interfaces.web.presenters.common import (
    as_drop_vm,
    base_template_context,
    drop_file_url,
    drop_page_url,
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
    selected_slug: str | None = None,
    credential: DropPasswordCredential | None = None,
    use_request_grant: bool = True,
    detail_error_message: str | None = None,
    detail_status_message: str | None = None,
) -> dict:
    detail_error_code: str | None = None
    selected_drop = None
    selected_requires_password = False
    selected_download_url = None
    access_granted = False
    invalid_grant = False
    selected_page_url = (
        drop_page_url(selected_slug)
        if selected_slug
        else None
    )
    selected_prompt_action = (
        drop_unlock_action_url(selected_slug)
        if selected_slug
        else None
    )

    if selected_slug:
        effective_credential = credential
        if effective_credential is None and use_request_grant:
            effective_credential = request_drop_password_credential(
                request,
                settings,
                selected_slug,
            )

        try:
            drop_meta = await get_drop_meta_use_case.execute_for_display(
                slug=selected_slug,
                auth=auth_data,
            )
        except DropAccessDeniedError:
            detail_error_message = detail_error_message or "파일이 존재하지 않습니다."
            detail_error_code = detail_error_code or "not_found"
        except DropNotFoundError:
            detail_error_message = detail_error_message or "파일이 존재하지 않습니다."
            detail_error_code = detail_error_code or "not_found"
        else:
            selected_requires_password = bool(drop_meta.requires_password)
            try:
                selected = await get_drop_meta_use_case.execute(
                    DropMetaQuery(
                        slug=selected_slug,
                        drop_password=effective_credential,
                        auth=auth_data,
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
                detail_error_message = detail_error_message or "파일이 존재하지 않습니다."
                detail_error_code = detail_error_code or "not_found"
            except DropNotFoundError:
                detail_error_message = detail_error_message or "파일을 불러올 수 없습니다."
                detail_error_code = detail_error_code or "not_found"
            else:
                selected_drop = as_drop_vm(selected)
                selected_download_url = drop_file_url(selected_slug)
                access_granted = True

    detail = DetailVM(
        slug=selected_slug,
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
            page=selected_page_url,
        ),
        forms=DetailFormsVM(
            locked_prompt_action=selected_prompt_action,
            unlock_token=(
                issue_drop_unlock_token(settings, selected_slug, "shared")
                if selected_slug
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
