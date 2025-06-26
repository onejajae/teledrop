"""
Drop 목록 조회 Handler

Drop의 목록 조회, 페이지네이션, 정렬, 필터링 등의 비즈니스 로직을 처리합니다.
"""


from typing import Literal
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Depends

from app.models import Drop
from app.handlers.base import BaseHandler
from app.handlers.mixins import PaginationMixin, LoggingMixin
from app.handlers.decorators import authenticate
from app.infrastructure.storage.base import StorageInterface
from app.models.drop.response import DropSummary, DropList
from app.core.config import Settings
from app.core.dependencies import get_session, get_storage, get_settings
from app.models.auth import AuthData


class DropListHandler(BaseHandler, PaginationMixin, LoggingMixin):
    """Drop 목록 조회 Handler"""
    
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
        is_private: bool | None = None,
        is_favorite: bool | None = None,
        has_password: bool | None = None,
        page: int = 1,
        page_size: int | None = None,
        sortby: Literal["created_time", "title", "file_size"] = "created_time",
        orderby: Literal["asc", "desc"] = "desc",
        auth_data: AuthData | None = None
    ) -> DropList:
        """
        Drop 목록을 조회합니다.
        
        @authenticate 데코레이터로 인증이 자동 검증됩니다.
        
        Args:
            is_private: private Drop 필터 (None: 전체, True: private만, False: public만)
            is_favorite: favorite Drop 필터 (None: 전체, True: favorite만, False: 일반만)
            has_password: password 필터 (None: 전체, True: password만, False: 일반만)
            page: 페이지 번호
            page_size: 페이지 크기 (None이면 설정값 사용)
            sortby: 정렬 기준 (created_time, title, file_size)
            orderby: 정렬 순서 (asc, desc)
            auth_data: 인증 데이터 (데코레이터에 의해 보장됨)
            
        Returns:
            DropList: 페이지네이션된 Drop 목록
        """
        self.log_info("Fetching drop list", is_private=is_private, is_favorite=is_favorite, 
                     page=page, page_size=page_size, sortby=sortby, orderby=orderby, user=auth_data.username)
        
        # 페이지네이션 검증 - Settings에서 기본값 가져오기
        page, page_size = self.validate_pagination(page, page_size)
        offset = self.calculate_offset(page, page_size)
        
        # Drop 목록과 전체 개수 동시 조회
        drops, total_count = await Drop.list_with_count(
            session=self.session,
            is_private=is_private,
            is_favorite=is_favorite,
            has_password=has_password,
            limit=page_size,
            offset=offset,
            sortby=sortby,
            orderby=orderby
        )
        
        
        # DropList 스키마로 반환
        result = DropList(
            drops=[
                DropSummary.model_validate(drop)
                for drop in drops
            ],
            total_count=total_count,
            page=page,
            page_size=page_size
        )
        
        self.log_info("Drop list fetched successfully", count=len(drops), total=total_count)
        return result 