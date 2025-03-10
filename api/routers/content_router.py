from fastapi import APIRouter, Depends
from fastapi import Form, UploadFile, File, Header
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from typing import Literal
from urllib import parse

from api.models import *
from api.exceptions import *
from api.services import ContentService

from .dependencies import get_content_service, Authenticator

router = APIRouter()


@router.get(
    path="",
    response_model=ContentsPublic,
    dependencies=[Depends(Authenticator(auto_error=True))],
)
async def list(
    page: int = 1,
    page_size: int = 10,
    sortby: Literal["created_at", "title", "file_size"] | None = "created_at",
    orderby: Literal["asc", "desc"] | None = "desc",
    content_service: ContentService = Depends(get_content_service),
):
    contents = content_service.list(
        page=page, page_size=page_size, sortby=sortby, orderby=orderby
    )

    return ContentsPublic(contents=contents)


@router.get("/{key}/preview", response_model=ContentPublic)
async def preview(
    key: str,
    password: str | None = None,
    auth_data: AuthData | None = Depends(Authenticator(auto_error=False)),
    content_service: ContentService = Depends(get_content_service),
):
    try:
        content = content_service.check_access_permission_by_key(
            key=key, auth_data=auth_data
        )
    except (ContentNotExist, ContentNeedLogin):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        content = content_service.get_by_key(key=key, password=password)
    except ContentNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except ContentPasswordInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return content


@router.get("/{key}")
async def download(
    key: str,
    preview: bool | None = False,
    password: str | None = None,
    auth_data: AuthData | None = Depends(Authenticator(auto_error=False)),
    range: str | None = Header(None),
    content_service: ContentService = Depends(get_content_service),
):
    try:
        content = content_service.check_access_permission_by_key(
            key=key, auth_data=auth_data
        )
    except (ContentNotExist, ContentNeedLogin):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        content = content_service.get_by_key(key=key, password=password)
    except ContentNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except ContentPasswordInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if preview:
        content_disposition_type = "inline"
    else:
        content_disposition_type = "attachment"

    # reference: filename in headers
    # https://httpwg.org/specs/rfc6266.html#examples
    headers = {
        "Content-Disposition": f"{content_disposition_type}; filename*=UTF-8''{parse.quote(content.file_name)}",
        "content-type": content.file_type,
        "accept-ranges": "bytes",
        "content-encoding": "identity",
        "content-length": str(content.file_size),
        "access-control-expose-headers": (
            "content-type, accept-ranges, content-length, "
            "content-range, content-encoding"
        ),
    }

    # reference: reusable streaming response for any filetypes
    # https://github.com/fastapi/fastapi/issues/1240#issuecomment-1055396884
    start = 0
    end = content.file_size - 1
    status_code = status.HTTP_200_OK

    if range is not None:
        start, end = range.replace("bytes=", "").split("-")
        start = int(start)
        end = int(end) if end else content.file_size - 1
        size = end - start + 1
        headers["content-length"] = str(size)
        headers["content-range"] = f"bytes {start}-{end}/{content.file_size}"
        status_code = status.HTTP_206_PARTIAL_CONTENT

    return StreamingResponse(
        content=await content_service.get_file_range_by_key(
            key=key, start=start, end=end, password=password
        ),
        status_code=status_code,
        headers=headers,
        media_type=content.file_type,
    )


@router.post("", response_model=ContentPublic, dependencies=[Depends(Authenticator())])
async def upload(
    file: UploadFile = File(),
    key: str = Form(default=None),
    title: str = Form(default=None),
    description: str | None = Form(default=None),
    password: str | None = Form(default=None),
    user_only: bool = Form(default=False),
    content_service: ContentService = Depends(get_content_service),
):

    if not key:
        key = content_service.generate_key()
    else:
        if not content_service.is_key_valid(key):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    new_content = await content_service.create(
        file_stream=file.file,
        file_name=file.filename,
        file_type=file.content_type,
        file_size=file.size,
        key=key,
        password=password,
        title=title,
        description=description,
        user_only=user_only,
    )

    return new_content


@router.patch(
    "/{key}/detail",
    response_model=ContentPublic,
    dependencies=[Depends(Authenticator())],
)
async def update_detail(
    key: str,
    new_detail: ContentUpdateDetail = Form(),
    content_service: ContentService = Depends(get_content_service),
):
    try:
        updated_content = content_service.update_detail(
            key=key,
            password=new_detail.password,
            title=new_detail.title,
            description=new_detail.description,
        )
    except ContentNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except ContentPasswordInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return updated_content


@router.patch(
    "/{key}/permission",
    response_model=ContentPublic,
    dependencies=[Depends(Authenticator())],
)
async def update_permission(
    key: str,
    new_permission: ContentUpdatePermission = Form(),
    content_service: ContentService = Depends(get_content_service),
):
    try:
        updated_content = content_service.update_permission(
            key=key,
            password=new_permission.password,
            user_only=new_permission.user_only,
        )
    except ContentNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except ContentPasswordInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return updated_content


@router.patch(
    "/{key}/password",
    response_model=ContentPublic,
    dependencies=[Depends(Authenticator())],
)
async def update_password(
    key: str,
    new_password: ContentUpdatePassword = Form(),
    content_service: ContentService = Depends(get_content_service),
):
    try:
        updated_content = content_service.update_password(
            key=key,
            new_password=new_password.new_password,
        )
    except ContentNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return updated_content


@router.patch(
    "/{key}/reset",
    response_model=ContentPublic,
    dependencies=[Depends(Authenticator())],
)
async def delete_password(
    key: str,
    password: str = Form(),
    content_service: ContentService = Depends(get_content_service),
):
    try:
        updated_content = content_service.update_password(key=key, new_password=None)
    except ContentNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return updated_content


@router.patch(
    "/{key}/favorite",
    response_model=ContentPublic,
    dependencies=[Depends(Authenticator())],
)
async def update_favorite(
    key: str,
    new_favorite: ContentUpdateFavorite = Form(),
    content_service: ContentService = Depends(get_content_service),
):
    try:
        updated_content = content_service.update_favorite_by_key(
            key=key, password=new_favorite.password, favorite=new_favorite.favorite
        )
    except ContentNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except ContentPasswordInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return updated_content


@router.delete("/{key}", dependencies=[Depends(Authenticator())])
async def delete(
    key: str,
    password: str = None,
    content_service: ContentService = Depends(get_content_service),
):

    try:
        content_service.delete_by_key(key=key, password=password)
    except ContentNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except ContentPasswordInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@router.get("/keycheck/{key}", dependencies=[Depends(Authenticator())])
async def get_key_exist(
    key: str,
    content_service: ContentService = Depends(get_content_service),
):

    return not content_service.is_key_valid(key)
