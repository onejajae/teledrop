"""
Drop 업데이트 관련 API 엔드포인트

Drop의 상세정보, 권한, 패스워드, 즐겨찾기 등을 수정하는 기능을 제공합니다.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Form

from app.handlers.drop import (
    DropDetailUpdateHandler,
    DropPermissionUpdateHandler,
    DropPasswordSetHandler,
    DropPasswordRemoveHandler,
    DropFavoriteUpdateHandler,
)
from app.handlers.auth.user import CurrentUserHandler
from app.models.drop import DropRead
from app.models.drop import (
    DropUpdateDetailForm, 
    DropUpdatePermissionForm, 
    DropSetPasswordForm, 
    DropUpdateFavoriteForm
)
from app.core.exceptions import DropNotFoundError


router = APIRouter()


@router.patch("/{slug}/detail", response_model=DropRead)
async def update_drop_detail(
    slug: str,
    form_data: DropUpdateDetailForm = Form(..., description="상세정보 수정 데이터"),
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
    handler: DropDetailUpdateHandler = Depends(DropDetailUpdateHandler)
):
    """
    Drop 상세정보를 수정합니다.
    
    소유자 권한만으로 충분하여 Drop 패스워드 확인 불필요합니다.
    """
    current_user = user_handler.execute()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # 인증 확인 후 핸들러 호출 (auth_data 불필요)
        result = handler.execute(
            slug=slug,
            form_data=form_data
        )
        
        return result
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )


@router.patch("/{slug}/permission", response_model=DropRead)
async def update_drop_permission(
    slug: str,
    form_data: DropUpdatePermissionForm = Form(..., description="권한 수정 데이터"),
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
    handler: DropPermissionUpdateHandler = Depends(DropPermissionUpdateHandler)
):
    """
    Drop 권한을 수정합니다.
    
    소유자 권한만으로 충분하여 Drop 패스워드 확인 불필요합니다.
    """
    current_user = user_handler.execute()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # 인증 확인 후 핸들러 호출 (auth_data 불필요)
        result = handler.execute(
            slug=slug,
            form_data=form_data
        )
        
        return result
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )


@router.patch("/{slug}/password/set", response_model=DropRead)
async def set_drop_password(
    slug: str,
    form_data: DropSetPasswordForm = Form(..., description="패스워드 설정 데이터"),
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
    handler: DropPasswordSetHandler = Depends(DropPasswordSetHandler)
):
    """
    Drop 패스워드를 설정/변경합니다.
    
    소유자 권한으로 현재 패스워드 없이도 설정 가능합니다.
    비밀번호를 잊어버렸을 때도 사용 가능합니다.
    """
    current_user = user_handler.execute()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # 인증 확인 후 핸들러 호출 (auth_data 불필요)
        result = handler.execute(
            slug=slug,
            form_data=form_data
        )
        
        return result
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )


@router.patch("/{slug}/password/remove", response_model=DropRead)
async def remove_drop_password(
    slug: str,
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
    handler: DropPasswordRemoveHandler = Depends(DropPasswordRemoveHandler)
):
    """
    Drop 패스워드를 제거합니다.
    
    소유자 권한으로 현재 패스워드 확인 없이 바로 제거됩니다.
    Form 데이터가 필요없는 단순한 제거 작업입니다.
    """
    current_user = user_handler.execute()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # 인증 확인 후 핸들러 호출 (auth_data 불필요)
        result = handler.execute(
            slug=slug
        )
        
        return result
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )


@router.patch("/{slug}/favorite", response_model=DropRead)
async def update_drop_favorite(
    slug: str,
    form_data: DropUpdateFavoriteForm = Form(..., description="즐겨찾기 여부"),
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
    handler: DropFavoriteUpdateHandler = Depends(DropFavoriteUpdateHandler)
):
    """
    Drop 즐겨찾기를 토글합니다.
    
    소유자 권한만으로 충분하여 Drop 패스워드 확인 불필요합니다.
    """
    current_user = user_handler.execute()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # 인증 확인 후 핸들러 호출 (auth_data 불필요)
        result = handler.execute(
            slug=slug,
            form_data=form_data
        )
        
        return result
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        ) 