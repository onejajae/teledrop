"""
Drop 목록 조회 API 엔드포인트

Drop 목록을 조회하는 기능을 제공합니다.
"""

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.handlers.drop.list import DropListHandler
from app.models.drop.response import DropList
from app.models.auth import AuthData
from app.core.dependencies import get_auth_data
from app.core.exceptions import AuthenticationRequiredError


router = APIRouter()


@router.get("/", response_model=DropList)
async def list_drops(
    auth_data: AuthData | None = Depends(get_auth_data),
    is_private: bool | None = Query(None, description="비공개 여부"),
    is_favorite: bool | None = Query(None, description="즐겨찾기 여부"),
    has_password: bool | None = Query(None, description="비밀번호 여부"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int | None = Query(None, ge=1, le=100, description="페이지 크기"),
    sortby: Literal["created_time", "title", "file_size"] = Query("created_time", description="정렬 기준"),
    orderby: Literal["asc", "desc"] = Query("desc", description="정렬 순서"),
    drop_list_handler: DropListHandler = Depends(DropListHandler)
):
    """
    Drop 목록을 조회합니다.
    
    @authenticate 데코레이터가 핸들러에서 인증을 자동으로 검증합니다.
    
    - **is_private**: 비공개 Drop만 조회 (true), 공개 Drop만 조회 (false), 전체 조회 (null)
    - **is_favorite**: 즐겨찾기 Drop만 조회 (true), 일반 Drop만 조회 (false), 전체 조회 (null)
    - **page**: 페이지 번호 (1부터 시작)
    - **page_size**: 페이지 크기 (기본값은 설정값)
    - **sortby**: 정렬 기준 (created_time, title, file_size)
    - **orderby**: 정렬 순서 (asc, desc)
    
    인증이 필요합니다.
    """
    try:
        # 핸들러의 @authenticate 데코레이터가 auth_data를 자동 검증
        result = await drop_list_handler.execute(
            is_private=is_private,
            is_favorite=is_favorite,
            has_password=has_password,
            page=page,
            page_size=page_size,
            sortby=sortby,
            orderby=orderby,
            auth_data=auth_data  # 명시적으로 전달
        )
        
        return result
        
    except AuthenticationRequiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list drops: {str(e)}"
        ) 