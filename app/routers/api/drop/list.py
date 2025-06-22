"""
Drop 목록 조회 API 엔드포인트

Drop 목록을 조회하는 기능을 제공합니다.
"""

from typing import Optional, Dict, Any, Literal
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.handlers.drop import DropListHandler
from app.handlers.auth.user import CurrentUserHandler
from app.models.drop import DropList


router = APIRouter()


@router.get("/", response_model=DropList)
async def list_drops(
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
    is_private: Optional[bool] = Query(None, description="비공개 여부"),
    is_favorite: Optional[bool] = Query(None, description="즐겨찾기 여부"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="페이지 크기"),
    sortby: Literal["created_time", "title", "file_size"] = Query("created_time", description="정렬 기준"),
    orderby: Literal["asc", "desc"] = Query("desc", description="정렬 순서"),
    handler: DropListHandler = Depends(DropListHandler)
):
    """
    Drop 목록을 조회합니다.
    
    - **is_private**: 비공개 Drop만 조회 (true), 공개 Drop만 조회 (false), 전체 조회 (null)
    - **is_favorite**: 즐겨찾기 Drop만 조회 (true), 일반 Drop만 조회 (false), 전체 조회 (null)
    - **page**: 페이지 번호 (1부터 시작)
    - **page_size**: 페이지 크기 (기본값은 설정값)
    - **sortby**: 정렬 기준 (created_time, title, file_size)
    - **orderby**: 정렬 순서 (asc, desc)
    
    인증이 필요합니다.
    """
    current_user = user_handler.execute()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        result = await handler.execute(
            is_private=is_private,
            is_favorite=is_favorite,
            page=page,
            page_size=page_size,
            sortby=sortby,
            orderby=orderby
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list drops: {str(e)}"
        ) 