from fastapi import APIRouter, Depends, Form
from fastapi import Form, UploadFile, File, Header
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from typing import Literal
from urllib import parse

from api.services.post_service import PostService
from api.services.user_service import UserService
from api.schemas.post.service import (
    PostServiceCreate,
    PostServiceUpdate,
)
from api.schemas.post.router import (
    PostCreateResponse,
    PostPreviewResponse,
    PostUpdateRequest,
    PostListResponse,
    PostListElement,
    PostListUserInfo,
)
from api.routers.dependencies import (
    get_post_service,
    get_current_user_id,
    get_user_service,
)
from api.exceptions.post_exceptions import *

router = APIRouter()


@router.get("/list", response_model=PostListResponse)
async def list(
    page: int = 1,
    page_size: int = 10,
    sortby: Literal["created_at", "title", "filesize"] | None = "created_at",
    orderby: Literal["asc", "desc"] | None = "desc",
    user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    posts = post_service.list(
        user_id=user_id, page=page, page_size=page_size, sortby=sortby, orderby=orderby
    )

    posts = [PostListElement(**post.model_dump()) for post in posts]
    return PostListResponse(posts=posts)


@router.get("/preview/{key}", response_model=PostPreviewResponse)
async def preview(
    key: str,
    password: str | None = None,
    user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    try:
        post = post_service.get_by_key(key=key, user_id=user_id, password=password)
    except PostNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except PostNeedLogin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except UserNotHavePostPermission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    except PostPasswordInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return post


@router.get("/download/{key}")
async def download(
    key: str,
    preview: bool | None = False,
    password: str | None = None,
    access_token: str | None = None,
    range: str | None = Header(None),
    post_service: PostService = Depends(get_post_service),
    user_service: UserService = Depends(get_user_service),
):

    user_id = get_current_user_id(token=access_token, user_service=user_service)

    try:
        post = post_service.get_by_key(key=key, user_id=user_id, password=password)
    except PostNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except PostNeedLogin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except UserNotHavePostPermission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    except PostPasswordInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if preview:
        content_disposition_type = "inline"
    else:
        content_disposition_type = "attachment"

    # reference: filename in headers
    # https://httpwg.org/specs/rfc6266.html#examples
    headers = {
        "Content-Disposition": f"{content_disposition_type}; filename*=UTF-8''{parse.quote(post.filename)}",
        "content-type": post.filetype,
        "accept-ranges": "bytes",
        "content-encoding": "identity",
        "content-length": str(post.filesize),
        "access-control-expose-headers": (
            "content-type, accept-ranges, content-length, "
            "content-range, content-encoding"
        ),
    }

    start = 0
    end = post.filesize - 1
    status_code = status.HTTP_200_OK

    if range is not None:
        start, end = range.replace("bytes=", "").split("-")
        start = int(start)
        end = int(end) if end else post.filesize - 1
        size = end - start + 1
        headers["content-length"] = str(size)
        headers["content-range"] = f"bytes {start}-{end}/{post.filesize}"
        status_code = status.HTTP_206_PARTIAL_CONTENT

    return StreamingResponse(
        content=await post_service.get_file_range_by_key(
            user_id=user_id, key=key, start=start, end=end, password=password
        ),
        status_code=status_code,
        headers=headers,
        media_type=post.filetype,
    )


@router.post("/upload", response_model=PostCreateResponse)
async def upload(
    file: UploadFile = File(),
    key: str = Form(default=None),
    title: str = Form(default=None),
    description: str | None = Form(default=None),
    password: str | None = Form(default=None),
    is_user_only: bool = Form(default=False),
    user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if not key:
        key = post_service.generate_key()
    else:
        if not post_service.is_key_valid(key):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    new_post = await post_service.create(
        user_id=user_id,
        file=file.file,
        post_data=PostServiceCreate(
            key=key,
            is_user_only=is_user_only,
            filedata=file,
            filename=file.filename,
            filetype=file.content_type,
            filesize=file.size,
            title=title,
            description=description,
            password=password,
        ),
    )

    return PostCreateResponse(**new_post.model_dump())


@router.put("/update/{key}")
async def update(
    key: str,
    new_post: PostUpdateRequest = Form(),
    user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        post = post_service.update_by_key(
            key=key,
            user_id=user_id,
            post_data=PostServiceUpdate(**new_post.model_dump()),
            password=new_post.password,
        )
    except PostNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except PostNeedLogin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except UserNotHavePostPermission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    except PostPasswordInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return post


@router.delete("/delete/{key}")
async def delete(
    key: str,
    password: str = None,
    user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    post_service.delete_by_key(key=key, user_id=user_id, password=password)


@router.patch("/update/{key}/favorite")
async def update_favorite(
    key: str,
    password: str = Form(None),
    favorite: bool = Form(),
    user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        post = post_service.update_favorite_by_key(
            key=key, user_id=user_id, password=password, favorite=favorite
        )
    except PostNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except PostNeedLogin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except UserNotHavePostPermission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    except PostPasswordInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return post


@router.patch("/update/{key}/password")
async def update_password(
    key: str,
    new_password: str = Form(),
    user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        post = post_service.update_password_by_key(
            key=key, user_id=user_id, new_password=new_password
        )
    except PostNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except PostNeedLogin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except UserNotHavePostPermission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    except PostPasswordInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return post


@router.get("/keycheck")
async def get_key_exist(
    key: str,
    user_id: int = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return not post_service.is_key_valid(key)
