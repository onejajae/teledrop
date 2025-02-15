import uuid
import secrets
from datetime import datetime, timezone

from api.config import Settings

from api.models import APIKeyCreate, APIKeyUpdate
from api.exceptions import APIKeyInvalid, APIKeyNotActive, APIKeyNotExist
from api.repositories import APIKeyRepositoryInterface


class APIKeyService:
    def __init__(
        self, api_key_repository: APIKeyRepositoryInterface, settings: Settings
    ):
        self.api_key_repository = api_key_repository
        self.settings = settings

    def create(
        self, description: str | None, read_permission: bool, write_permission: bool
    ):
        key = secrets.token_hex(16)

        new_api_key = self.api_key_repository.create(
            APIKeyCreate(
                key=key,
                description=description,
                read_permission=read_permission,
                write_permission=write_permission,
                active=True,
                created_at=datetime.now(timezone.utc),
            )
        )

        return new_api_key

    def list(self):
        api_keys = self.api_key_repository.list()

        return api_keys

    def get_by_id(self, id: uuid.UUID):
        api_key = self.api_key_repository.get_by_id(id)

        if api_key is None:
            raise APIKeyInvalid

        return api_key

    def get_by_key(self, key: str):
        api_key = self.api_key_repository.get_by_key(key)

        if api_key is None:
            raise APIKeyInvalid

        return api_key

    def delete_by_key(self, key: str):
        api_key = self.api_key_repository.get_by_key(key)

        if api_key is None:
            raise APIKeyInvalid

        self.api_key_repository.delete_by_key(key)

    def update_description_by_key(self, key: str, description: str):
        updated_api_key = self.api_key_repository.update_by_key(
            key=key,
            new_api_key=APIKeyUpdate(
                description=description, updated_at=datetime.now(timezone.utc)
            ),
        )

        if updated_api_key is None:
            raise APIKeyInvalid

        return updated_api_key

    def update_permissions_by_key(
        self, key: str, read_permission: bool, write_permission: bool
    ):
        updated_api_key = self.api_key_repository.update_by_key(
            key=key,
            new_api_key=APIKeyUpdate(
                read_permission=read_permission,
                write_permission=write_permission,
                updated_at=datetime.now(timezone.utc),
            ),
        )

        if updated_api_key is None:
            raise APIKeyInvalid

        return updated_api_key

    def update_active_by_key(self, key: str, active: bool):
        updated_api_key = self.api_key_repository.update_by_key(
            key=key,
            new_api_key=APIKeyUpdate(
                active=active,
                updated_at=datetime.now(timezone.utc),
            ),
        )

        if updated_api_key is None:
            raise APIKeyInvalid

        return updated_api_key
