from fastapi import APIRouter, Depends, Form
from fastapi import HTTPException, status
from fastapi.security import APIKeyHeader

from api.models import (
    APIKeyPublic,
    APIKeysPublic,
    APIKeyCreateRequest,
    APIKeyUpdatePermissions,
    APIKeyUpdateActive,
    APIKeyUpdateDescription,
)
from api.services import APIKeyService
from api.exceptions import APIKeyInvalid

from .dependencies import get_api_key_service, Authenticator


router = APIRouter()

api_key_header = APIKeyHeader(name="X-API-KEY")


@router.post(
    "",
    response_model=APIKeyPublic,
    dependencies=[Depends(Authenticator(web_only=True))],
)
async def create_api_key(
    new_api_key: APIKeyCreateRequest = Form(),
    api_key_service: APIKeyService = Depends(get_api_key_service),
):
    new_api_key = api_key_service.create(**new_api_key.model_dump())

    return new_api_key


@router.get(
    "",
    response_model=APIKeysPublic,
    dependencies=[Depends(Authenticator(web_only=True))],
)
async def get_api_key_list(
    api_key_service: APIKeyService = Depends(get_api_key_service),
):
    return APIKeysPublic(api_keys=api_key_service.list())


@router.patch("/permissions", dependencies=[Depends(Authenticator(web_only=True))])
async def update_api_key_permissions(
    new_permissions: APIKeyUpdatePermissions = Form(),
    api_key_service: APIKeyService = Depends(get_api_key_service),
):
    try:
        return api_key_service.update_permissions_by_key(
            key=new_permissions.key, permissions=new_permissions.permissions
        )
    except APIKeyInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@router.patch("/active", dependencies=[Depends(Authenticator(web_only=True))])
async def update_api_key_active(
    new_active: APIKeyUpdateActive = Form(),
    api_key_service: APIKeyService = Depends(get_api_key_service),
):
    try:
        return api_key_service.update_active_by_key(
            key=new_active.key, active=new_active.active
        )
    except APIKeyInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@router.patch("/description", dependencies=[Depends(Authenticator(web_only=True))])
async def update_api_key_description(
    new_description: APIKeyUpdateDescription = Form(),
    api_key_service: APIKeyService = Depends(get_api_key_service),
):
    try:
        return api_key_service.update_description_by_key(
            key=new_description.key, description=new_description.description
        )
    except APIKeyInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@router.delete("", dependencies=[Depends(Authenticator(web_only=True))])
async def delete_api_key(
    key: str = Form(),
    api_key_service: APIKeyService = Depends(get_api_key_service),
):
    try:
        api_key_service.delete_by_key(key)
    except APIKeyInvalid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
