"""
Drop 목록 조회 Handler

Drop의 목록 조회, 페이지네이션, 정렬, 필터링 등의 비즈니스 로직을 처리합니다.
"""


from typing import Literal
from sqlmodel import Session
from fastapi import Depends

from app.models import Drop
from app.handlers.base import BaseHandler
from app.handlers.mixins import PaginationMixin
from app.infrastructure.storage.base import StorageInterface
from app.models.drop import DropSummary, DropList
from app.core.config import Settings
from app.core.dependencies import get_session, get_storage, get_settings
from app.models.auth import AuthData


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
        is_private: bool | None = None,
        is_favorite: bool | None = None,
        page: int = 1,
        page_size: int | None = None,
        sortby: Literal["created_time", "title", "file_size"] = "created_time",
        orderby: Literal["asc", "desc"] = "desc"
    ) -> DropList:
        """
        Drop 목록을 조회합니다.
        
        Args:
            auth_data: 인증 정보 (필수)
            is_private: private Drop 필터 (None: 전체, True: private만, False: public만)
            is_favorite: favorite Drop 필터 (None: 전체, True: favorite만, False: 일반만)
            page: 페이지 번호
            page_size: 페이지 크기 (None이면 설정값 사용)
            sortby: 정렬 기준 (created_time, title, file_size)
            orderby: 정렬 순서 (asc, desc)
            
        Returns:
            DropList: 페이지네이션된 Drop 목록
        """
        self.log_info("Fetching drop list", is_private=is_private, is_favorite=is_favorite, 
                     page=page, page_size=page_size, sortby=sortby, orderby=orderby)
        
        # 페이지네이션 검증 - Settings에서 기본값 가져오기
        page, page_size = self.validate_pagination(page, page_size)
        offset = self.calculate_offset(page, page_size)
        
        # Drop 목록과 전체 개수 동시 조회
        drops, total_count = await Drop.list_with_count(
            session=self.session,
            is_private=is_private,
            is_favorite=is_favorite,
            limit=page_size,
            offset=offset,
            sortby=sortby,
            orderby=orderby
        )
        
        # 응답 데이터 구성 - model_validate 사용
        drop_elements = [
            DropSummary.model_validate(drop)
            for drop in drops
        ]
        
        # DropList 스키마로 반환
        result = DropList(
            drops=drop_elements,
            total_count=total_count
        )
        
        self.log_info("Drop list fetched successfully", count=len(drops), total=total_count)
        return result 