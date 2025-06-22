"""
페이지네이션 기능을 제공하는 믹스인

Handler에서 사용하는 페이지네이션 관련 공통 기능을 제공합니다.
"""

from typing import Optional

from app.core.config import Settings


class PaginationMixin:
    """페이지네이션 기능을 제공하는 믹스인"""
    
    settings: Settings  # Settings 주입 필요
    
    def calculate_offset(self, page: int, page_size: int) -> int:
        """페이지와 페이지 크기를 기반으로 오프셋을 계산합니다."""
        return (page - 1) * page_size
    
    def validate_pagination(self, page: Optional[int] = None, page_size: Optional[int] = None) -> tuple[int, int]:
        """페이지네이션 파라미터를 검증하고 기본값을 적용합니다.
        
        Args:
            page: 페이지 번호 (1부터 시작)
            page_size: 페이지당 항목 수
            
        Returns:
            tuple[int, int]: (검증된 페이지, 검증된 페이지 크기)
        """
        # 기본값 적용
        page = page or 1
        page_size = page_size or self.settings.DEFAULT_PAGE_SIZE
        
        # 최솟값 검증
        page = max(1, page)
        page_size = max(1, min(page_size, self.settings.MAX_PAGE_SIZE))
        
        return page, page_size 