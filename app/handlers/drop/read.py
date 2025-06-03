"""
Drop 조회 Handler들

Drop의 상세 조회, 목록 조회 등의 읽기 관련 비즈니스 로직을 처리합니다.
"""

from typing import Optional, Dict, Any
from sqlmodel import Session
from fastapi import Depends

from app.models import Drop
from app.handlers.base import BaseHandler, PaginationMixin
from app.infrastructure.storage.base import StorageInterface
from app.models.drop import DropListElement
from app.core.config import Settings
from app.core.exceptions import DropNotFoundError
from app.core.dependencies import get_session, get_storage, get_settings


class DropListHandler(BaseHandler, PaginationMixin):
    """Drop 목록 조회 Handler"""
    
    def __init__(
        self,
        session: Session = Depends(get_session),
        storage_service: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage_service = storage_service
        self.settings = settings
    
    async def execute(
        self,
        auth_data: Dict[str, Any],
        user_only: Optional[bool] = None,
        page: int = 1,
        page_size: Optional[int] = None,
        sortby: Optional[str] = "created_at",
        orderby: Optional[str] = "desc"
    ) -> Dict[str, Any]:
        """
        Drop 목록을 조회합니다.
        
        Args:
            auth_data: 인증 정보 (필수)
            user_only: 사용자 전용 Drop만 조회할지 여부
            page: 페이지 번호
            page_size: 페이지 크기 (None이면 설정값 사용)
            sortby: 정렬 기준 (created_at, title, file_size)
            orderby: 정렬 순서 (asc, desc)
            
        Returns:
            Dict[str, Any]: 페이지네이션된 Drop 목록
        """
        self.log_info("Fetching drop list", user_only=user_only, page=page, page_size=page_size, 
                     sortby=sortby, orderby=orderby)
        
        # 페이지네이션 검증 - Settings에서 기본값 가져오기
        page, page_size = self.validate_pagination(page, page_size)
        offset = self.calculate_offset(page, page_size)
        
        # Drop 목록과 전체 개수 동시 조회
        drops, total_count = await Drop.list_with_count(
            session=self.session,
            user_only=user_only,
            limit=page_size,
            offset=offset,
            sortby=sortby,
            orderby=orderby
        )
        
        # 응답 데이터 구성 - 리스트 컴프리헨션 사용
        drop_elements = [
            DropListElement(
                id=drop.id,
                key=drop.key,
                title=drop.title,
                favorite=drop.favorite,
                user_only=drop.user_only,
                created_at=drop.created_at,
                password=drop.password,  # @computed_field를 위해 포함
                has_file=True,  # 모든 Drop은 file을 가짐
                file_size=drop.file.file_size,
                file_type=drop.file.file_type,
                file_name=drop.file.original_filename,
            )
            for drop in drops
        ]
        
        result = {
            "drops": drop_elements,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size,
                "has_next": offset + page_size < total_count,
                "has_prev": page > 1
            }
        }
        
        self.log_info("Drop list fetched successfully", count=len(drops), total=total_count)
        return result


class DropDetailHandler(BaseHandler):
    """Drop 상세 조회 Handler"""

    def __init__(
        self,
        session: Session = Depends(get_session),
        storage_service: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage_service = storage_service
        self.settings = settings
    
    def execute(
        self,
        drop_key: str,
        password: Optional[str] = None,
        auth_data: Optional[Dict[str, Any]] = None
    ) -> Drop:
        """
        Drop 상세 정보를 조회합니다.
        
        Args:
            drop_key: Drop 키
            password: Drop 패스워드 (필요한 경우)
            auth_data: 인증 정보
            
        Returns:
            Drop: Drop 상세 정보
            
        Raises:
            DropNotFoundError: Drop을 찾을 수 없는 경우
            DropPasswordInvalidError: 패스워드가 틀린 경우
            DropAccessDeniedError: 접근 권한이 없는 경우
        """
        self.log_info("Fetching drop detail", drop_key=drop_key)
        
        # Drop 조회
        drop = Drop.get_by_key(self.session, drop_key)
        if not drop:
            raise DropNotFoundError(f"Drop not found: {drop_key}")
        
        # 접근 권한 검증
        self.validate_drop_access(drop, auth_data)
        
        # 패스워드 검증
        self.validate_drop_password(drop, password)
        
        self.log_info("Drop detail fetched successfully", drop_id=str(drop.id))
        return drop 