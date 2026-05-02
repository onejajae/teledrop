from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile

from app.application.auth.types import AuthIdentity
from app.application.drop.models import (
    CreateDropCommand,
    DropListQuery,
    DropMetaQuery,
    DropStreamQuery,
)
from app.application.drop.use_cases import (
    CreateDropUseCase,
    GetDropMetaUseCase,
    GetDropStreamSourceUseCase,
    ListDropsUseCase,
)
from app.bootstrap.container import get_app_settings
from app.bootstrap.providers.drop import (
    get_create_drop_use_case,
    get_get_drop_meta_use_case,
    get_get_drop_stream_source_use_case,
    get_list_drops_use_case,
)
from app.core.config import Settings
from app.core.drop_grants import build_drop_password_credential
from app.domain.drop.errors import DropAccessDeniedError, DropSlugUnavailableError
from app.domain.drop.value_objects import AccessScope, DropSortField
from app.interfaces.api.deps.auth import get_required_api_key_auth
from app.interfaces.api.errors import (
    drop_list_unauthorized_exception,
    map_drop_mutation_exception,
    map_drop_read_exception,
    slug_unavailable_exception,
    upload_too_large_exception,
)
from app.interfaces.api.schemas.drop import (
    DropDetailResponse,
    DropListResponse,
)
from app.interfaces.drop_streaming import build_drop_stream_response


router = APIRouter(prefix="/drop", tags=["Drop"])


@router.get("", response_model=DropListResponse)
async def list_drops(
    auth_data: AuthIdentity = Depends(get_required_api_key_auth),
    list_drops_use_case: ListDropsUseCase = Depends(get_list_drops_use_case),
    page: int = Query(default=1),
    page_size: int = Query(default=50),
    sort: DropSortField = Query(default=DropSortField.CREATED_AT),
    order: str = Query(default="desc"),
):
    try:
        result = await list_drops_use_case.execute(
            DropListQuery(
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
                auth=auth_data,
            )
        )
    except DropAccessDeniedError:
        raise drop_list_unauthorized_exception()

    return DropListResponse.from_dto(result)


@router.post("", response_model=DropDetailResponse)
async def upload_drop(
    auth_data: AuthIdentity = Depends(get_required_api_key_auth),
    settings: Settings = Depends(get_app_settings),
    create_drop_use_case: CreateDropUseCase = Depends(get_create_drop_use_case),
    file: UploadFile = File(),
    slug: str | None = Form(default=None),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    access_scope: AccessScope = Form(default=AccessScope.PRIVATE),
    drop_password: str | None = Form(default=None),
):
    size_bytes = file.size
    if size_bytes is None:
        current_pos = file.file.tell()
        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(current_pos)

    if size_bytes > settings.MAX_UPLOAD_BYTES:
        raise upload_too_large_exception()

    command = CreateDropCommand(
        owner_user_id=auth_data.user_id or "",
        file_stream=file.file,
        file_name=file.filename,
        mime_type=file.content_type,
        size_bytes=size_bytes,
        slug=slug,
        access_scope=access_scope,
        drop_password=drop_password,
        title=title,
        description=description,
    )

    try:
        created = await create_drop_use_case.execute(command)
    except DropSlugUnavailableError:
        raise slug_unavailable_exception()
    except Exception as exc:
        raise map_drop_mutation_exception(exc)

    return DropDetailResponse.from_dto(created)


@router.get("/{slug}/meta", response_model=DropDetailResponse)
async def drop_meta(
    slug: str,
    auth_data: AuthIdentity = Depends(get_required_api_key_auth),
    get_drop_meta_use_case: GetDropMetaUseCase = Depends(get_get_drop_meta_use_case),
    drop_password: str | None = Header(default=None, alias="X-Drop-Password"),
):
    try:
        result = await get_drop_meta_use_case.execute(
            DropMetaQuery(
                slug=slug,
                drop_password=build_drop_password_credential(password=drop_password),
                auth=auth_data,
            )
        )
    except Exception as exc:
        raise map_drop_read_exception(exc)

    return DropDetailResponse.from_dto(result)


@router.get("/{slug}")
async def drop_stream(
    slug: str,
    auth_data: AuthIdentity = Depends(get_required_api_key_auth),
    get_drop_stream_source_use_case: GetDropStreamSourceUseCase = Depends(
        get_get_drop_stream_source_use_case
    ),
    drop_password: str | None = Header(default=None, alias="X-Drop-Password"),
    range_header: str | None = Header(None, alias="Range"),
    disposition: str = Query(default="attachment"),
):
    try:
        detail, storage_key = await get_drop_stream_source_use_case.execute(
            DropStreamQuery(
                slug=slug,
                drop_password=build_drop_password_credential(password=drop_password),
                auth=auth_data,
            )
        )
    except Exception as exc:
        raise map_drop_read_exception(exc)

    return build_drop_stream_response(
        detail=detail,
        storage_key=storage_key,
        iter_stream_range=get_drop_stream_source_use_case.iter_stream_range,
        range_header=range_header,
        disposition=disposition,
    )
