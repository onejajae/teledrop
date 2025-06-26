"""
Drop 업데이트 관련 API 엔드포인트

Drop의 상세정보, 권한, 패스워드, 즐겨찾기 등을 수정하는 기능을 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Form, Query

from app.handlers.drop.update import (
    DropDetailUpdateHandler,
    DropPermissionUpdateHandler,
    DropPasswordSetHandler,
    DropPasswordRemoveHandler,
    DropFavoriteUpdateHandler,
)
from app.models.drop.response import DropRead
from app.models.drop.request import (
    DropUpdateDetailForm, 
    DropUpdatePermissionForm, 
    DropSetPasswordForm, 
    DropUpdateFavoriteForm
)
from app.models.auth import AuthData
from app.core.dependencies import get_auth_data
from app.core.exceptions import DropNotFoundError, AuthenticationRequiredError, DropPasswordInvalidError


router = APIRouter()


@router.patch("/{slug}/detail", response_model=DropRead)
async def update_drop_detail(
    slug: str,
    password: str | None = Query(None, description="Drop 패스워드 (보호된 Drop인 경우)"),
    form_data: DropUpdateDetailForm = Form(..., description="상세정보 수정 데이터"),
    auth_data: AuthData | None = Depends(get_auth_data),
    drop_detail_update_handler: DropDetailUpdateHandler = Depends(DropDetailUpdateHandler)
):
    """
    Drop 상세정보를 수정합니다.
    
    @authenticate 데코레이터가 핸들러에서 인증을 자동으로 검증합니다.
    소유자 권한만으로 충분하여 Drop 패스워드 확인 불필요합니다.
    """
    try:
        # 핸들러의 @authenticate 데코레이터가 auth_data를 자동 검증
        result = await drop_detail_update_handler.execute(
            slug=slug,
            form_data=form_data,
            password=password,
            auth_data=auth_data
        )
        
        return result
        
    except AuthenticationRequiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update drop detail: {str(e)}"
        )


@router.patch("/{slug}/permission", response_model=DropRead)
async def update_drop_permission(
    slug: str,
    password: str | None = Query(None, description="Drop 패스워드 (보호된 Drop인 경우)"),
    form_data: DropUpdatePermissionForm = Form(..., description="권한 수정 데이터"),
    auth_data: AuthData | None = Depends(get_auth_data),
    drop_permission_update_handler: DropPermissionUpdateHandler = Depends(DropPermissionUpdateHandler)
):
    """
    Drop 권한을 수정합니다.
    
    @authenticate 데코레이터가 핸들러에서 인증을 자동으로 검증합니다.
    소유자 권한만으로 충분하여 Drop 패스워드 확인 불필요합니다.
    """
    try:
        # 핸들러의 @authenticate 데코레이터가 auth_data를 자동 검증
        result = await drop_permission_update_handler.execute(
            slug=slug,
            form_data=form_data,
            password=password,
            auth_data=auth_data
        )
        
        return result
    
    except DropPasswordInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
        
    except AuthenticationRequiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update drop permission: {str(e)}"
        )


@router.patch("/{slug}/password/set", response_model=DropRead)
async def set_drop_password(
    slug: str,
    form_data: DropSetPasswordForm = Form(..., description="패스워드 설정 데이터"),
    auth_data: AuthData | None = Depends(get_auth_data),
    drop_password_set_handler: DropPasswordSetHandler = Depends(DropPasswordSetHandler)
):
    """
    Drop 패스워드를 설정/변경합니다.
    
    @authenticate 데코레이터가 핸들러에서 인증을 자동으로 검증합니다.
    소유자 권한으로 현재 패스워드 없이도 설정 가능합니다.
    비밀번호를 잊어버렸을 때도 사용 가능합니다.
    """
    try:
        # 핸들러의 @authenticate 데코레이터가 auth_data를 자동 검증
        result = await drop_password_set_handler.execute(
            slug=slug,
            form_data=form_data,
            auth_data=auth_data
        )
        
        return result
        
    except AuthenticationRequiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set drop password: {str(e)}"
        )


@router.patch("/{slug}/password/remove", response_model=DropRead)
async def remove_drop_password(
    slug: str,
    password: str | None = Query(None, description="Drop 패스워드 (보호된 Drop인 경우)"),
    auth_data: AuthData | None = Depends(get_auth_data),
    drop_password_remove_handler: DropPasswordRemoveHandler = Depends(DropPasswordRemoveHandler)
):
    """
    Drop 패스워드를 제거합니다.
    
    @authenticate 데코레이터가 핸들러에서 인증을 자동으로 검증합니다.
    소유자 권한으로 현재 패스워드 확인 없이 바로 제거됩니다.
    Form 데이터가 필요없는 단순한 제거 작업입니다.
    """
    try:
        # 핸들러의 @authenticate 데코레이터가 auth_data를 자동 검증
        result = await drop_password_remove_handler.execute(
            slug=slug,
            password=password,
            auth_data=auth_data
        )
        
        return result
        
    except AuthenticationRequiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove drop password: {str(e)}"
        )


@router.patch("/{slug}/favorite", response_model=DropRead)
async def update_drop_favorite(
    slug: str,
    password: str | None = Query(None, description="Drop 패스워드 (보호된 Drop인 경우)"),
    form_data: DropUpdateFavoriteForm = Form(..., description="즐겨찾기 여부"),
    auth_data: AuthData | None = Depends(get_auth_data),
    drop_favorite_update_handler: DropFavoriteUpdateHandler = Depends(DropFavoriteUpdateHandler)
):
    """
    Drop 즐겨찾기를 토글합니다.
    
    @authenticate 데코레이터가 핸들러에서 인증을 자동으로 검증합니다.
    소유자 권한만으로 충분하여 Drop 패스워드 확인 불필요합니다.
    """
    try:
        # 핸들러의 @authenticate 데코레이터가 auth_data를 자동 검증
        result = await drop_favorite_update_handler.execute(
            slug=slug,
            form_data=form_data,
            password=password,
            auth_data=auth_data
        )
        
        return result
        
    except AuthenticationRequiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update drop favorite: {str(e)}"
        ) 