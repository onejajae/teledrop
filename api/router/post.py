import uuid
import os
import io
from urllib import parse
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter
from fastapi import Form, UploadFile, File, Header
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from typing import Literal
from sqlmodel import Session, select, col
from sqlalchemy.sql.functions import coalesce

from api.db.model import Post, User
from api.schema import (
    PostPublic,
    PostListElement,
    PostUpdate,
    PostMinimal,
    PostFavoriteUpdate,
    PostPasswordReset,
)
from api.deps import SessionDep, CurrentUser, SettingsDep, get_current_user
from api.utils import validate_key, send_bytes_range_requests
from api.config import Settings


router = APIRouter()


@router.get("/list", response_model=list[PostListElement])
async def list(
    sortby: Literal["created_at", "title", "filesize"] | None = "created_at",
    orderby: Literal["asc", "desc"] | None = "desc",
    user: User = CurrentUser,
    session: Session = SessionDep,
):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    sort_column = getattr(Post, sortby)
    if sortby == "title":
        sort_column = coalesce(Post.title, Post.filename)

    if orderby == "asc":
        sort_column = sort_column.asc()
    else:
        sort_column = sort_column.desc()

    statement = select(Post).where(Post.user_id == user.id).order_by(sort_column)
    posts = session.exec(statement).all()

    return posts


@router.get("/preview/{key}", response_model=PostPublic)
async def preview(
    key: str,
    password: str | None = None,
    user: User = CurrentUser,
    session: Session = SessionDep,
):
    statement = select(Post).where(Post.key == key)
    post = session.exec(statement).one_or_none()

    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if post.is_user_only and user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if post.is_user_only and user.id != post.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if post.password != password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return post


@router.get("/download/{key}")
async def download(
    key: str,
    preview: bool | None = False,
    password: str | None = None,
    access_token: str | None = None,
    range: str | None = Header(None),
    session: Session = SessionDep,
    settings: Settings = SettingsDep,
):
    user = await get_current_user(
        token=access_token, session=session, settings=settings
    )

    statement = select(Post).where(Post.key == key)
    post = session.exec(statement).one_or_none()

    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if post.is_user_only and user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if post.is_user_only and user.id != post.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if post.password != password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    file_path = Path(settings.SHARE_DIRECTORY) / post.location

    # reference: reusable streaming response for any filetypes
    # https://github.com/fastapi/fastapi/issues/1240#issuecomment-1055396884

    # reference: filename in headers
    # https://httpwg.org/specs/rfc6266.html#examples

    if preview:
        content_disposition_type = "inline"
    else:
        content_disposition_type = "attachment"

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
        send_bytes_range_requests(open(file_path, "rb"), start, end),
        headers=headers,
        status_code=status_code,
    )


@router.post("/upload", response_model=PostMinimal)
async def upload(
    file: UploadFile = File(),
    key: str = Form(default=None),
    title: str = Form(default=None),
    description: str | None = Form(default=None),
    password: str | None = Form(default=None),
    is_user_only: bool = Form(default=False),
    user: User = CurrentUser,
    session: Session = SessionDep,
    settings: Settings = SettingsDep,
):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    file_uuid = str(uuid.uuid4())
    if not key:
        key = file_uuid
    else:
        if not await validate_key(key, session):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    data = await file.read()
    write_path = Path(settings.SHARE_DIRECTORY) / file_uuid

    with open(write_path, "wb") as f:
        f.write(data)

    new_post = Post(
        key=key,
        is_user_only=is_user_only,
        title=title,
        description=description,
        created_at=datetime.now(),
        password=password,
        filename=file.filename,
        filetype=file.content_type,
        filesize=file.size,
        location=file_uuid,
        user_id=user.id,
    )
    session.add(new_post)
    session.commit()
    session.refresh(new_post)

    return new_post


@router.put("/update/{key}", response_model=PostPublic)
async def update(
    key: str,
    new_post: PostUpdate = Form(),
    user: User = CurrentUser,
    session: Session = SessionDep,
):
    statement = select(Post).where(Post.key == key)
    post = session.exec(statement).one_or_none()

    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user is None or post.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if post.password != new_post.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if new_post.new_password:
        new_post.password = new_post.new_password
    else:
        if new_post.delete_password:
            new_post.password = None

    new_post = new_post.model_dump(exclude_unset=True)
    post.sqlmodel_update(new_post)
    post.updated_at = datetime.now()

    session.add(post)
    session.commit()
    session.refresh(post)

    return post


@router.patch("/update/{key}/favorite")
async def update_favorite(
    key: str,
    new_favorite: PostFavoriteUpdate = Form(),
    user: User = CurrentUser,
    session: Session = SessionDep,
):
    statement = select(Post).where(Post.key == key)
    post = session.exec(statement).one_or_none()

    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user is None or post.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if post.password != new_favorite.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    post.favorite = new_favorite.favorite
    session.add(post)
    session.commit()


@router.patch("/update/{key}/password")
async def update_password(
    key: str,
    new_password: PostPasswordReset = Form(),
    user: User = CurrentUser,
    session: Session = SessionDep,
):
    statement = select(Post).where(Post.key == key)
    post = session.exec(statement).one_or_none()

    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user is None or post.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    post.password = new_password.new_password
    session.add(post)
    session.commit()


@router.delete("/delete/{key}")
async def delete(
    key: str,
    password: str = None,
    user: User = CurrentUser,
    session: Session = SessionDep,
    settings: Settings = SettingsDep,
):
    statement = select(Post).where(Post.key == key)
    post = session.exec(statement).one_or_none()

    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user is None or post.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if post.password != password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    delete_path = Path(settings.SHARE_DIRECTORY) / post.location
    os.remove(delete_path)

    session.delete(post)
    session.commit()


@router.get("/keycheck")
async def get_key_exist(
    key: str,
    user: User = CurrentUser,
    session: Session = SessionDep,
):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return not await validate_key(key=key, session=session)
