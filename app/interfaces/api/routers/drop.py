from urllib import parse

from fastapi import APIRouter, File, Form, Header, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.application.drop.models import (
    UNSET as COMMAND_UNSET,
    CreateDropCommand,
    DropDetailDTO,
    DropListItemDTO,
    DropListQuery,
    DropMetaQuery,
    DropStreamQuery,
    DeleteDropCommand,
    UpdateDropCommand,
)
from app.core.exceptions import InvalidRangeHeader, RangeNotSatisfiable
from app.core.utils import parse_range_header
from app.domain.drop.errors import DropAccessDeniedError, DropSlugUnavailableError
from app.domain.drop.policies import normalize_drop_password
from app.domain.drop.value_objects import AccessScope, DropSortField
from app.interfaces.api.deps import (
    DropUseCasesDep,
    OptionalApiAuthDep,
    RequiredApiAuthDep,
)
from app.interfaces.api.errors import (
    drop_list_unauthorized_exception,
    invalid_range_header_exception,
    map_drop_mutation_exception,
    map_drop_read_exception,
    range_not_satisfiable_exception,
    slug_unavailable_exception,
)
from app.interfaces.api.schemas.drop import (
    DropDetailResponse,
    DropListItemResponse,
    DropListResponse,
    DropPatchRequest,
    SlugAvailabilityResponse,
)


router = APIRouter(prefix="/drop", tags=["Drop"])


def _to_list_item_response(item: DropListItemDTO) -> DropListItemResponse:
    return DropListItemResponse(
        slug=item.slug,
        title=item.title,
        description=item.description,
        file_name=item.file_name,
        mime_type=item.mime_type,
        size_bytes=item.size_bytes,
        access_scope=item.access_scope,
        is_favorite=item.is_favorite,
        requires_password=item.requires_password,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _to_detail_response(item: DropDetailDTO) -> DropDetailResponse:
    list_item = _to_list_item_response(item)
    return DropDetailResponse(
        slug=list_item.slug,
        title=list_item.title,
        description=list_item.description,
        file_name=list_item.file_name,
        mime_type=list_item.mime_type,
        size_bytes=list_item.size_bytes,
        access_scope=list_item.access_scope,
        is_favorite=list_item.is_favorite,
        requires_password=list_item.requires_password,
        created_at=list_item.created_at,
        updated_at=list_item.updated_at,
        sha256=item.sha256,
    )


@router.get("/availability/{slug}", response_model=SlugAvailabilityResponse)
async def slug_availability(
    slug: str,
    _auth_data: RequiredApiAuthDep,
    use_cases: DropUseCasesDep,
):
    return SlugAvailabilityResponse(
        available=await use_cases.check_slug_availability_use_case.execute(slug)
    )


@router.get("", response_model=DropListResponse)
async def list_drops(
    auth_data: RequiredApiAuthDep,
    use_cases: DropUseCasesDep,
    page: int = Query(default=1),
    page_size: int = Query(default=50),
    sort: DropSortField = Query(default=DropSortField.CREATED_AT),
    order: str = Query(default="desc"),
):
    try:
        result = await use_cases.list_drops_use_case.execute(
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

    return DropListResponse(
        items=[_to_list_item_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


@router.post("", response_model=DropDetailResponse)
async def upload_drop(
    _auth_data: RequiredApiAuthDep,
    use_cases: DropUseCasesDep,
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

    command = CreateDropCommand(
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
        created = await use_cases.create_drop_use_case.execute(command)
    except DropSlugUnavailableError:
        raise slug_unavailable_exception()

    return _to_detail_response(created)


@router.get("/{slug}/meta", response_model=DropDetailResponse)
async def drop_meta(
    slug: str,
    auth_data: OptionalApiAuthDep,
    use_cases: DropUseCasesDep,
    drop_password: str | None = Query(default=None),
):
    try:
        result = await use_cases.get_drop_meta_use_case.execute(
            DropMetaQuery(
                slug=slug,
                drop_password=normalize_drop_password(drop_password),
                auth=auth_data,
            )
        )
    except Exception as exc:
        raise map_drop_read_exception(exc)

    return _to_detail_response(result)


@router.get("/{slug}")
async def drop_stream(
    slug: str,
    auth_data: OptionalApiAuthDep,
    use_cases: DropUseCasesDep,
    disposition: str = Query(default="attachment"),
    drop_password: str | None = Query(default=None),
    range_header: str | None = Header(None, alias="Range"),
):
    try:
        detail, storage_key = await use_cases.get_drop_stream_source_use_case.execute(
            DropStreamQuery(
                slug=slug,
                drop_password=normalize_drop_password(drop_password),
                auth=auth_data,
            )
        )
    except Exception as exc:
        raise map_drop_read_exception(exc)

    if disposition not in {"attachment", "inline"}:
        disposition = "attachment"

    headers = {
        "Content-Disposition": f"{disposition}; filename*=UTF-8''{parse.quote(detail.file_name)}",
        "content-type": detail.mime_type,
        "accept-ranges": "bytes",
        "content-encoding": "identity",
        "content-length": str(detail.size_bytes),
        "access-control-expose-headers": (
            "content-type, accept-ranges, content-length, content-range, content-encoding"
        ),
    }

    start = 0
    end = detail.size_bytes - 1
    status_code = status.HTTP_200_OK

    if range_header is not None:
        try:
            start, end = parse_range_header(range_header, detail.size_bytes)
        except InvalidRangeHeader:
            raise invalid_range_header_exception()
        except RangeNotSatisfiable:
            raise range_not_satisfiable_exception()

        headers["content-length"] = str(end - start + 1)
        headers["content-range"] = f"bytes {start}-{end}/{detail.size_bytes}"
        status_code = status.HTTP_206_PARTIAL_CONTENT

    return StreamingResponse(
        content=use_cases.get_drop_stream_source_use_case.iter_stream_range(
            storage_key, start, end
        ),
        status_code=status_code,
        headers=headers,
        media_type=detail.mime_type,
    )


@router.patch("/{slug}", response_model=DropDetailResponse)
async def patch_drop(
    slug: str,
    payload: DropPatchRequest,
    _auth_data: RequiredApiAuthDep,
    use_cases: DropUseCasesDep,
):
    title = payload.title if "title" in payload.model_fields_set else COMMAND_UNSET
    description = (
        payload.description if "description" in payload.model_fields_set else COMMAND_UNSET
    )
    access_scope = (
        payload.access_scope if "access_scope" in payload.model_fields_set else COMMAND_UNSET
    )
    is_favorite = (
        payload.is_favorite if "is_favorite" in payload.model_fields_set else COMMAND_UNSET
    )
    new_password = (
        payload.new_password if "new_password" in payload.model_fields_set else COMMAND_UNSET
    )

    try:
        result = await use_cases.update_drop_use_case.execute(
            UpdateDropCommand(
                slug=slug,
                current_password=normalize_drop_password(payload.current_password),
                title=title,
                description=description,
                access_scope=access_scope,
                is_favorite=is_favorite,
                new_password=new_password,
            )
        )
    except Exception as exc:
        raise map_drop_mutation_exception(exc)

    return _to_detail_response(result)


@router.delete("/{slug}")
async def delete_drop(
    slug: str,
    _auth_data: RequiredApiAuthDep,
    use_cases: DropUseCasesDep,
    current_password: str | None = Query(default=None),
):
    try:
        await use_cases.delete_drop_use_case.execute(
            DeleteDropCommand(
                slug=slug,
                current_password=normalize_drop_password(current_password),
            )
        )
    except Exception as exc:
        raise map_drop_mutation_exception(exc)
