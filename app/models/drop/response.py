"""
Drop API 응답 스키마들

클라이언트에게 반환되는 데이터 구조를 정의합니다.
각 스키마는 특정 API 엔드포인트의 응답 형태에 맞춰 설계되었습니다.
"""


from sqlmodel import SQLModel, Field
from pydantic import computed_field

from .base import DropCore, DropDetail, DropFileDetail

# ═══════════════════════════════════════════════════════════════
# 📤 응답 스키마들 - API 응답용 데이터 구조
# ═══════════════════════════════════════════════════════════════

class DropSummary(DropCore):
    """Drop 목록용 요약 스키마 - 핵심 정보 (메타데이터 + 파일 기본 정보)"""
    
    # password 필드를 포함하되 직렬화에서 제외 (보안)
    password: str | None = Field(default=None, exclude=True)
    
    @computed_field
    @property
    def has_password(self) -> bool:
        """password 필드를 기반으로 패스워드 설정 여부 계산"""
        return bool(self.password)


class DropRead(DropCore, DropDetail, DropFileDetail):
    """Drop 상세 조회 스키마 - 핵심 정보 + Drop 상세 정보 + 파일 상세 정보"""
    
    # password 필드를 포함하되 직렬화에서 제외 (보안)
    password: str | None = Field(default=None, exclude=True)
    
    @computed_field
    @property
    def has_password(self) -> bool:
        """password 필드를 기반으로 패스워드 설정 여부 계산"""
        return bool(self.password)


class DropList(SQLModel):
    """페이지네이션된 Drop 목록 컨테이너"""
    
    drops: list[DropSummary]
    total_count: int
    page: int | None = None
    page_size: int | None = None
    
    # Computed fields for pagination
    @property
    def total_pages(self) -> int | None:
        """전체 페이지 수"""
        if self.page_size and self.page_size > 0:
            return (self.total_count + self.page_size - 1) // self.page_size
        return None


class DropDeleteResult(SQLModel):
    """Drop 삭제 결과 스키마"""
    
    deleted_slug: str 


class DropExistsResult(SQLModel):
    """Drop 슬러그 존재 여부 스키마"""
    
    exists: bool    