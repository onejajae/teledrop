"""
Drop API Router

Drop 관련 RESTful API 엔드포인트를 제공합니다.
기존 content API와 호환성을 유지하면서 새로운 Handler 패턴을 적용합니다.
"""

from typing import Optional, Dict, Any, Literal
from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, UploadFile, File, Header
from fastapi.responses import JSONResponse, StreamingResponse
from urllib import parse

from app.dependencies import (
    get_drop_list_handler,
    get_drop_detail_handler,
    get_drop_create_handler,
    get_drop_update_handler,
    get_drop_delete_handler,
    get_drop_access_handler,
    get_file_download_handler,
    get_file_range_handler,
    CurrentUserDep,
    CurrentUserOptionalDep
)
from app.handlers.drop import (
    DropListHandler,
    DropDetailHandler,
    DropCreateHandler,
    DropUpdateHandler,
    DropDeleteHandler,
    DropAccessHandler
)
from app.handlers.file import (
    FileDownloadHandler,
    FileRangeHandler
)
from app.models.drop import DropCreate, DropUpdate, DropListElement
from app.core.exceptions import (
    DropNotFoundError,
    DropPasswordInvalidError,
    DropAccessDeniedError,
    ValidationError,
    DropFileNotFoundError,
    DropKeyAlreadyExistsError
)

router = APIRouter(prefix="/content")


@router.get("", response_model=Dict[str, Any])
async def list_drops(
    current_user: CurrentUserDep,  # 기존 API는 인증 필수
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(10, ge=1, le=100, description="페이지 크기"),
    user_only: Optional[bool] = Query(None, description="사용자 전용 여부"),
    favorite: Optional[bool] = Query(None, description="즐겨찾기 여부"),
    sortby: Optional[Literal["created_at", "title", "file_size"]] = Query("created_at", description="정렬 기준"),
    orderby: Optional[Literal["asc", "desc"]] = Query("desc", description="정렬 순서"),
    handler: DropListHandler = Depends(get_drop_list_handler())
):
    """
    Drop 목록을 조회합니다. (기존 content API 호환)
    
    - **page**: 페이지 번호 (1부터 시작)
    - **page_size**: 페이지 크기 (1-100)
    - **sortby**: 정렬 기준 (created_at, title, file_size)
    - **orderby**: 정렬 순서 (asc, desc)
    
    인증이 필요합니다.
    """
    try:
        result = await handler.execute(
            user_only=user_only,  # 모든 Drop 조회 (공개 + 비공개)
            include_files=True,
            page=page,
            page_size=page_size,
            sortby=sortby,
            orderby=orderby,
            auth_data=current_user
        )
        
        # 기존 API 응답 형식에 맞게 변환
        return {
            "contents": result["drops"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch drops: {str(e)}"
        )


@router.get("/{key}/preview", response_model=Dict[str, Any])
async def get_drop_preview(
    key: str,
    password: Optional[str] = Query(None, description="Drop 패스워드"),
    current_user: CurrentUserOptionalDep = None,
    handler: DropDetailHandler = Depends(get_drop_detail_handler())
):
    """
    Drop 미리보기 정보를 조회합니다. (기존 content API 호환)
    
    - **key**: Drop 고유 키
    - **password**: Drop 패스워드 (필요한 경우)
    """
    try:
        drop = handler.execute(
            drop_key=key,
            password=password,
            auth_data=current_user
        )
        
        # 기존 ContentPublic API와 호환되는 응답 형식
        response = {
            "key": drop.key,
            "user_only": drop.user_only,
            "favorite": drop.favorite,
            "title": drop.title,
            "description": drop.description,
            "created_at": drop.created_at.isoformat(),
            "updated_at": drop.updated_at.isoformat() if drop.updated_at else None,
            "required_password": bool(drop.password)
        }
        
        # 파일 정보 추가 (모든 Drop은 file을 가짐)
        response.update({
            "file_name": drop.file.original_filename,
            "file_hash": drop.file.file_hash,
            "file_type": drop.file.file_type,
            "file_size": drop.file.file_size
        })
        
        return response
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except DropPasswordInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    except DropAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )


@router.get("/{key}")
async def download_or_stream_file(
    key: str,
    preview: Optional[bool] = Query(False, description="미리보기 모드"),
    password: Optional[str] = Query(None, description="Drop 패스워드"),
    range: Optional[str] = Header(None, alias="Range"),
    current_user: CurrentUserOptionalDep = None,
    download_handler: FileDownloadHandler = Depends(get_file_download_handler()),
    range_handler: FileRangeHandler = Depends(get_file_range_handler())
):
    """
    Drop의 파일을 다운로드하거나 스트리밍합니다. (기존 content API 호환)
    
    - **key**: Drop 고유 키
    - **preview**: 미리보기 모드 (inline vs attachment)
    - **password**: Drop 패스워드 (필요한 경우)
    - **Range**: HTTP Range 헤더 (부분 다운로드용)
    """
    try:
        # Range 요청이 있으면 Range Handler 사용
        if range:
            response, file_obj = await range_handler.execute(
                drop_key=key,
                range_header=range,
                password=password,
                auth_data=current_user
            )
        else:
            # 일반 다운로드
            as_attachment = not preview  # preview=True면 inline, False면 attachment
            response, file_obj = await download_handler.execute(
                drop_key=key,
                password=password,
                auth_data=current_user,
                as_attachment=as_attachment
            )
        
        # 기존 API와 동일한 추가 헤더 설정 (Content-Disposition은 Handler에서 설정됨)
        response.headers["accept-ranges"] = "bytes"
        response.headers["content-encoding"] = "identity"
        response.headers["access-control-expose-headers"] = (
            "content-type, accept-ranges, content-length, "
            "content-range, content-encoding"
        )
        
        return response
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except DropFileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    except DropPasswordInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    except DropAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_drop(
    current_user: CurrentUserDep,
    file: UploadFile = File(..., description="업로드할 파일 (필수)"),
    key: Optional[str] = Form(None, description="Drop 키 (없으면 자동 생성)"),
    title: Optional[str] = Form(None, description="Drop 제목"),
    description: Optional[str] = Form(None, description="Drop 설명"),
    password: Optional[str] = Form(None, description="Drop 패스워드"),
    user_only: bool = Form(False, description="사용자 전용 여부"),
    favorite: bool = Form(False, description="즐겨찾기 여부"),
    handler: DropCreateHandler = Depends(get_drop_create_handler())
):
    """
    파일과 함께 Drop을 생성합니다. (모든 Drop은 반드시 파일을 가져야 함)
    
    - **file**: 업로드할 파일 (필수)
    - **key**: Drop 키 (없으면 자동 생성)
    - **title**: Drop 제목
    - **description**: Drop 설명
    - **password**: Drop 패스워드
    - **user_only**: 사용자 전용 여부
    - **favorite**: 즐겨찾기 여부
    
    인증이 필요합니다.
    """
    try:
        # Drop 생성 데이터 구성
        drop_data = DropCreate(
            key=key,
            title=title,
            description=description,
            password=password,
            user_only=user_only,
            favorite=favorite
        )
        
        # Drop과 파일을 함께 생성
        drop = await handler.execute(
            drop_data=drop_data,
            upload_file=file,
            auth_data=current_user
        )
        
        # 성공 응답 반환 (기존 API 호환)
        return {
            "key": drop.key,
            "title": drop.title,
            "description": drop.description,
            "user_only": drop.user_only,
            "favorite": drop.favorite,
            "created_at": drop.created_at.isoformat(),
            "updated_at": drop.updated_at.isoformat() if drop.updated_at else None,
            "file": {
                "id": str(drop.file.id),
                "original_filename": drop.file.original_filename,
                "file_size": drop.file.file_size,
                "file_type": drop.file.file_type,
                "created_at": drop.file.created_at.isoformat()
            }
        }
        
    except DropKeyAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create drop: {str(e)}"
        )


@router.patch("/{key}/detail", response_model=Dict[str, Any])
async def update_drop_detail(
    key: str,
    current_user: CurrentUserDep,
    title: Optional[str] = Form(None, description="새 제목"),
    description: Optional[str] = Form(None, description="새 설명"),
    password: Optional[str] = Form(None, description="현재 패스워드"),
    handler: DropUpdateHandler = Depends(get_drop_update_handler()),
    access_handler: DropAccessHandler = Depends(get_drop_access_handler())
):
    """
    Drop 상세정보를 수정합니다. (기존 content API 호환)
    """
    try:
        # 통합 접근 권한 검증 (인증 + 패스워드 + 권한)
        access_handler.validate_access(
            drop_key=key,
            password=password,
            auth_data=current_user,
            require_auth=True
        )
        
        # 업데이트 데이터 구성
        update_data = DropUpdate()
        if title is not None:
            update_data.title = title
        if description is not None:
            update_data.description = description
        
        updated_drop = handler.execute(
            drop_key=key,
            update_data=update_data,
            auth_data=current_user
        )
        
        return updated_drop.model_dump()
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except DropPasswordInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    except DropAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )


@router.patch("/{key}/permission", response_model=Dict[str, Any])
async def update_drop_permission(
    key: str,
    current_user: CurrentUserDep,
    user_only: bool = Form(..., description="사용자 전용 여부"),
    password: Optional[str] = Form(None, description="현재 패스워드"),
    handler: DropUpdateHandler = Depends(get_drop_update_handler()),
    access_handler: DropAccessHandler = Depends(get_drop_access_handler())
):
    """
    Drop 권한을 수정합니다. (기존 content API 호환)
    """
    try:
        # 통합 접근 권한 검증 (인증 + 패스워드 + 권한)
        access_handler.validate_access(
            drop_key=key,
            password=password,
            auth_data=current_user,
            require_auth=True
        )
        
        update_data = DropUpdate(user_only=user_only)
        updated_drop = handler.execute(
            drop_key=key,
            update_data=update_data,
            auth_data=current_user
        )
        
        return updated_drop.model_dump()
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except DropPasswordInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    except DropAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )


@router.patch("/{key}/password", response_model=Dict[str, Any])
async def update_drop_password(
    key: str,
    current_user: CurrentUserDep,
    new_password: str = Form(..., description="새 패스워드"),
    handler: DropUpdateHandler = Depends(get_drop_update_handler())
):
    """
    Drop 패스워드를 설정/변경합니다. (기존 content API 호환)
    """
    try:
        update_data = DropUpdate(password=new_password)
        updated_drop = handler.execute(
            drop_key=key,
            update_data=update_data,
            auth_data=current_user
        )
        
        return updated_drop.model_dump()
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )


@router.patch("/{key}/reset", response_model=Dict[str, Any])
async def reset_drop_password(
    key: str,
    current_user: CurrentUserDep,
    password: str = Form(..., description="현재 패스워드"),
    handler: DropUpdateHandler = Depends(get_drop_update_handler()),
    access_handler: DropAccessHandler = Depends(get_drop_access_handler())
):
    """
    Drop 패스워드를 제거합니다. (기존 content API 호환)
    """
    try:
        # 통합 접근 권한 검증 (인증 + 패스워드 + 권한)
        access_handler.validate_access(
            drop_key=key,
            password=password,
            auth_data=current_user,
            require_auth=True
        )
        
        update_data = DropUpdate(password=None)  # 패스워드 제거
        updated_drop = handler.execute(
            drop_key=key,
            update_data=update_data,
            auth_data=current_user
        )
        
        return updated_drop.model_dump()
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except DropPasswordInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    except DropAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )


@router.patch("/{key}/favorite", response_model=Dict[str, Any])
async def update_drop_favorite(
    key: str,
    current_user: CurrentUserDep,
    favorite: bool = Form(..., description="즐겨찾기 여부"),
    password: Optional[str] = Form(None, description="현재 패스워드"),
    handler: DropUpdateHandler = Depends(get_drop_update_handler()),
    access_handler: DropAccessHandler = Depends(get_drop_access_handler())
):
    """
    Drop 즐겨찾기를 토글합니다. (기존 content API 호환)
    """
    try:
        # 통합 접근 권한 검증 (인증 + 패스워드 + 권한)
        access_handler.validate_access(
            drop_key=key,
            password=password,
            auth_data=current_user,
            require_auth=True
        )
        
        update_data = DropUpdate(favorite=favorite)
        updated_drop = handler.execute(
            drop_key=key,
            update_data=update_data,
            auth_data=current_user
        )
        
        return updated_drop.model_dump()
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except DropPasswordInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    except DropAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )


@router.delete("/{key}")
async def delete_drop(
    key: str,
    current_user: CurrentUserDep,
    password: Optional[str] = Query(None, description="Drop 패스워드"),
    handler: DropDeleteHandler = Depends(get_drop_delete_handler()),
    access_handler: DropAccessHandler = Depends(get_drop_access_handler())
):
    """
    Drop을 삭제합니다. (기존 content API 호환)
    
    연관된 파일도 함께 삭제됩니다.
    """
    try:
        # 통합 접근 권한 검증 (인증 + 패스워드 + 권한)
        access_handler.validate_access(
            drop_key=key,
            password=password,
            auth_data=current_user,
            require_auth=True
        )
        
        success = handler.execute(
            drop_key=key,
            auth_data=current_user
        )
        
        return {"message": "Drop deleted successfully"}
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except DropPasswordInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    except DropAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )


@router.get("/keycheck/{key}")
async def check_key_availability(
    key: str,
    current_user: CurrentUserDep
):
    """
    키 사용 가능 여부를 확인합니다. (기존 content API 호환)
    
    Returns:
        bool: 키가 사용 중이면 True, 사용 중이지 않으면 False
    """
    try:
        from app.models import Drop
        from app.dependencies import get_db_session
        
        # 예약어 체크
        if key in ["api", ""]:
            return False
        
        session = next(get_db_session())
        existing_drop = Drop.get_by_key(session, key, include_file=False)
        return existing_drop is not None 
            
    except Exception:
        return False 