"""
API Key Router

API Key 관리를 위한 RESTful API 엔드포인트를 제공합니다.
API Key 생성, 조회, 수정, 삭제, 검증 등의 기능을 포함합니다.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Form
from fastapi.responses import JSONResponse

from app.dependencies import (
    get_api_key_create_handler,
    get_api_key_list_handler,
    get_api_key_update_handler,
    get_api_key_delete_handler,
    get_api_key_validate_handler,
    CurrentUserDep
)
from app.handlers.api_key import (
    ApiKeyCreateHandler,
    ApiKeyListHandler,
    ApiKeyUpdateHandler,
    ApiKeyDeleteHandler,
    ApiKeyValidateHandler
)
from app.models.api_key import ApiKeyCreate, ApiKeyUpdate
from app.core.exceptions import (
    ApiKeyNotFoundError,
    ApiKeyInvalidError,
    ValidationError
)

router = APIRouter(prefix="/api-key")


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_api_key(
    current_user: CurrentUserDep,
    name: str = Form(..., description="API Key 이름"),
    description: Optional[str] = Form(None, description="API Key 설명"),
    expires_in_days: Optional[int] = Form(None, ge=1, le=365, description="만료일 (일 단위, 최대 365일)"),
    handler: ApiKeyCreateHandler = Depends(get_api_key_create_handler())
):
    """
    새로운 API Key를 생성합니다.
    
    - **name**: API Key 이름 (필수)
    - **description**: API Key 설명 (선택)
    - **expires_in_days**: 만료일 (일 단위, 1-365일, 선택)
    
    인증이 필요합니다.
    
    ⚠️ **중요**: 생성된 API Key는 한 번만 표시됩니다. 안전한 곳에 저장하세요.
    """
    try:
        api_key_data = ApiKeyCreate(
            name=name,
            description=description,
            expires_in_days=expires_in_days
        )
        
        result = await handler.execute(
            api_key_data=api_key_data,
            auth_data=current_user
        )
        
        return result
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=Dict[str, Any])
async def list_api_keys(
    current_user: CurrentUserDep,
    active_only: bool = Query(True, description="활성 키만 조회"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    handler: ApiKeyListHandler = Depends(get_api_key_list_handler())
):
    """
    API Key 목록을 조회합니다.
    
    - **active_only**: 활성 키만 조회할지 여부
    - **page**: 페이지 번호 (1부터 시작)
    - **page_size**: 페이지 크기 (1-100)
    
    인증이 필요합니다.
    """
    try:
        result = await handler.execute(
            active_only=active_only,
            page=page,
            page_size=page_size,
            auth_data=current_user
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch API keys: {str(e)}"
        )


@router.get("/{api_key_id}", response_model=Dict[str, Any])
async def get_api_key(
    api_key_id: str,
    current_user: CurrentUserDep
):
    """
    특정 API Key 정보를 조회합니다.
    
    - **api_key_id**: API Key ID
    
    인증이 필요합니다.
    """
    try:
        from app.models import ApiKey
        from app.dependencies import get_db_session
        
        async with get_db_session() as session:
            api_key = await ApiKey.get_by_id(session, api_key_id)
            if not api_key:
                raise ApiKeyNotFoundError(f"API key not found: {api_key_id}")
            
            return {
                "api_key": {
                    "id": str(api_key.id),
                    "name": api_key.name,
                    "description": api_key.description,
                    "key_prefix": api_key.key_prefix,
                    "is_active": api_key.is_active,
                    "expires_at": api_key.expires_at,
                    "last_used_at": api_key.last_used_at,
                    "created_at": api_key.created_at,
                    "updated_at": api_key.updated_at,
                    "status": api_key.status,
                    "is_expired": api_key.is_expired
                }
            }
            
    except ApiKeyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )


@router.patch("/{api_key_id}", response_model=Dict[str, Any])
async def update_api_key(
    api_key_id: str,
    current_user: CurrentUserDep,
    name: Optional[str] = Form(None, description="새 이름"),
    description: Optional[str] = Form(None, description="새 설명"),
    is_active: Optional[bool] = Form(None, description="활성 상태"),
    expires_in_days: Optional[int] = Form(None, ge=1, le=365, description="새 만료일 (일 단위)"),
    handler: ApiKeyUpdateHandler = Depends(get_api_key_update_handler())
):
    """
    API Key 정보를 수정합니다.
    
    - **name**: 새 이름 (선택)
    - **description**: 새 설명 (선택)
    - **is_active**: 활성 상태 (선택)
    - **expires_in_days**: 새 만료일 (일 단위, 1-365일, 선택)
    
    인증이 필요합니다.
    """
    try:
        update_data = ApiKeyUpdate()
        if name is not None:
            update_data.name = name
        if description is not None:
            update_data.description = description
        if is_active is not None:
            update_data.is_active = is_active
        if expires_in_days is not None:
            update_data.expires_in_days = expires_in_days
        
        updated_api_key = await handler.execute(
            api_key_id=api_key_id,
            update_data=update_data,
            auth_data=current_user
        )
        
        return {
            "api_key": updated_api_key.model_dump(),
            "message": "API key updated successfully"
        }
        
    except ApiKeyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{api_key_id}", response_model=Dict[str, Any])
async def delete_api_key(
    api_key_id: str,
    current_user: CurrentUserDep,
    handler: ApiKeyDeleteHandler = Depends(get_api_key_delete_handler())
):
    """
    API Key를 삭제합니다.
    
    - **api_key_id**: API Key ID
    
    인증이 필요합니다.
    
    ⚠️ **주의**: 삭제된 API Key는 복구할 수 없습니다.
    """
    try:
        success = await handler.execute(
            api_key_id=api_key_id,
            auth_data=current_user
        )
        
        return {
            "success": success,
            "message": "API key deleted successfully"
        }
        
    except ApiKeyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )


@router.post("/validate", response_model=Dict[str, Any])
async def validate_api_key(
    api_key: str = Form(..., description="검증할 API Key"),
    handler: ApiKeyValidateHandler = Depends(get_api_key_validate_handler())
):
    """
    API Key를 검증합니다.
    
    - **api_key**: 검증할 API Key
    
    이 엔드포인트는 인증이 필요하지 않습니다. (API Key 자체가 인증 수단)
    """
    try:
        result = await handler.execute(
            api_key=api_key,
            update_last_used=True
        )
        
        return result
        
    except ApiKeyInvalidError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/{api_key_id}/deactivate", response_model=Dict[str, Any])
async def deactivate_api_key(
    api_key_id: str,
    current_user: CurrentUserDep,
    handler: ApiKeyUpdateHandler = Depends(get_api_key_update_handler())
):
    """
    API Key를 비활성화합니다.
    
    - **api_key_id**: API Key ID
    
    인증이 필요합니다.
    """
    try:
        update_data = ApiKeyUpdate(is_active=False)
        updated_api_key = await handler.execute(
            api_key_id=api_key_id,
            update_data=update_data,
            auth_data=current_user
        )
        
        return {
            "api_key": updated_api_key.model_dump(),
            "message": "API key deactivated successfully"
        }
        
    except ApiKeyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )


@router.post("/{api_key_id}/activate", response_model=Dict[str, Any])
async def activate_api_key(
    api_key_id: str,
    current_user: CurrentUserDep,
    handler: ApiKeyUpdateHandler = Depends(get_api_key_update_handler())
):
    """
    API Key를 활성화합니다.
    
    - **api_key_id**: API Key ID
    
    인증이 필요합니다.
    """
    try:
        update_data = ApiKeyUpdate(is_active=True)
        updated_api_key = await handler.execute(
            api_key_id=api_key_id,
            update_data=update_data,
            auth_data=current_user
        )
        
        return {
            "api_key": updated_api_key.model_dump(),
            "message": "API key activated successfully"
        }
        
    except ApiKeyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        ) 