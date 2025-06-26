"""
Drop 수정 Handler들

Drop의 메타데이터 수정 관련 비즈니스 로직을 처리합니다.
각 핸들러는 완전히 독립적으로 동작하며 특정 업데이트 기능만 담당합니다.
"""

from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Depends

from app.models import Drop
from app.handlers.base import BaseHandler
from app.handlers.mixins import DropAccessMixin
from app.handlers.decorators import authenticate
from app.infrastructure.storage.base import StorageInterface
from app.models.drop.request import (
    DropUpdateDetailForm, 
    DropUpdatePermissionForm, 
    DropSetPasswordForm, 
    DropUpdateFavoriteForm
)
from app.models.drop.response import DropRead
from app.core.config import Settings
from app.core.exceptions import DropNotFoundError, ValidationError
from app.core.dependencies import get_session, get_storage, get_settings
from app.models.auth import AuthData


class DropDetailUpdateHandler(BaseHandler, DropAccessMixin):
    """Drop 상세 정보 업데이트 전담 핸들러"""
    
    def __init__(
        self,
        session: AsyncSession = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage = storage
        self.settings = settings
    
    @authenticate  # 인증 필수
    async def execute(
        self,
        slug: str,
        form_data: DropUpdateDetailForm,
        password: str | None = None,
        auth_data: AuthData | None = None,
    ) -> DropRead:
        """Drop 상세 정보를 업데이트합니다."""
        self.log_info("Updating drop details", slug=slug, user=auth_data.username)
        
        try:
            # Drop 조회
            drop = await Drop.get_by_slug(self.session, slug)
            if not drop:
                raise DropNotFoundError(f"Drop not found: {slug}")
            
            self.validate_drop_access(drop, auth_data, password)
            
            # 업데이트 (None 값 제외)
            update_fields = {}
            if form_data.title is not None:
                update_fields['title'] = form_data.title
            if form_data.description is not None:
                update_fields['description'] = form_data.description
            
            if update_fields:
                await drop.update(self.session, **update_fields)
            
            result = DropRead.model_validate(drop)
            self.log_info("Drop detail updated successfully", drop_id=str(drop.id))
            return result
            
        except Exception as e:
            # 의존성에서 자동 롤백 처리됨
            self.log_error("Failed to update drop detail", error=str(e))
            raise


class DropPermissionUpdateHandler(BaseHandler, DropAccessMixin):
    """Drop 권한 수정 전담 핸들러"""
    
    def __init__(
        self,
        session: AsyncSession = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage = storage
        self.settings = settings
    
    @authenticate  # 인증 필수
    async def execute(
        self,
        slug: str,
        form_data: DropUpdatePermissionForm,
        password: str | None = None,
        auth_data: AuthData | None = None,
    ) -> DropRead:
        """Drop 권한을 수정합니다."""
        self.log_info("Updating drop permission", slug=slug, is_private=form_data.is_private, user=auth_data.username)
        
        try:
            drop = await Drop.get_by_slug(self.session, slug)
            if not drop:
                raise DropNotFoundError(f"Drop not found: {slug}")
            
            self.validate_drop_access(drop, auth_data, password)
            
            # 권한 변경
            await drop.update(self.session, is_private=form_data.is_private)
            
            result = DropRead.model_validate(drop)
            self.log_info("Drop permission updated successfully", drop_id=str(drop.id))
            return result
        
        
        except Exception as e:
            # 의존성에서 자동 롤백 처리됨
            self.log_error("Failed to update drop permission", error=str(e))
            raise


class DropPasswordSetHandler(BaseHandler, DropAccessMixin):
    """Drop 패스워드 설정 전담 핸들러"""
    
    def __init__(
        self,
        session: AsyncSession = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage = storage
        self.settings = settings
    
    @authenticate  # 인증 필수
    async def execute(
        self,
        slug: str,
        form_data: DropSetPasswordForm,
        auth_data: AuthData | None = None,
    ) -> DropRead:
        """Drop 패스워드를 설정합니다."""
        self.log_info("Setting drop password", slug=slug, user=auth_data.username)
        
        try:
            drop = await Drop.get_by_slug(self.session, slug)
            if not drop:
                raise DropNotFoundError(f"Drop not found: {slug}")
            
            
            # 패스워드 특화 검증 (길이는 이미 Form에서 검증됨)
            password = form_data.new_password.strip()
            if not password:
                raise ValidationError("Password cannot be empty")
            
            # 패스워드 설정
            await drop.update(self.session, password=password)
            
            result = DropRead.model_validate(drop)
            self.log_info("Drop password set successfully", drop_id=str(drop.id))
            return result
            
        except Exception as e:
            # 의존성에서 자동 롤백 처리됨
            self.log_error("Failed to set drop password", error=str(e))
            raise


class DropPasswordRemoveHandler(BaseHandler, DropAccessMixin):
    """Drop 패스워드 제거 전담 핸들러"""
    
    def __init__(
        self,
        session: AsyncSession = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage = storage
        self.settings = settings
    
    @authenticate  # 인증 필수
    async def execute(
        self,
        slug: str,
        auth_data: AuthData | None = None,
        password: str | None = None,
    ) -> DropRead:
        """Drop 패스워드를 제거합니다."""
        self.log_info("Removing drop password", slug=slug, user=auth_data.username)
        
        try:
            drop = await Drop.get_by_slug(self.session, slug)
            if not drop:
                raise DropNotFoundError(f"Drop not found: {slug}")
            
            self.validate_drop_access(drop, auth_data, password)
            
            # 패스워드 제거
            await drop.update(self.session, password=None)
            
            result = DropRead.model_validate(drop)
            self.log_info("Drop password removed successfully", drop_id=str(drop.id))
            return result
            
        except Exception as e:
            # 의존성에서 자동 롤백 처리됨
            self.log_error("Failed to remove drop password", error=str(e))
            raise


class DropFavoriteUpdateHandler(BaseHandler, DropAccessMixin):
    """Drop 즐겨찾기 수정 전담 핸들러"""
    
    def __init__(
        self,
        session: AsyncSession = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage = storage
        self.settings = settings
    
    @authenticate  # 인증 필수
    async def execute(
        self,
        slug: str,
        form_data: DropUpdateFavoriteForm,
        auth_data: AuthData | None = None,
        password: str | None = None,
    ) -> DropRead:
        """Drop 즐겨찾기를 수정합니다."""
        self.log_info("Updating drop favorite", slug=slug, is_favorite=form_data.is_favorite, user=auth_data.username)
        
        try:
            drop = await Drop.get_by_slug(self.session, slug)
            if not drop:
                raise DropNotFoundError(f"Drop not found: {slug}")
            
            self.validate_drop_access(drop, auth_data, password)
            
            # 즐겨찾기 변경
            await drop.update(self.session, is_favorite=form_data.is_favorite)
            
            result = DropRead.model_validate(drop)
            self.log_info("Drop favorite updated successfully", drop_id=str(drop.id))
            return result
            
        except Exception as e:
            # 의존성에서 자동 롤백 처리됨
            self.log_error("Failed to update drop favorite", error=str(e))
            raise
