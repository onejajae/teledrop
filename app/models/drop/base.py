"""
Drop 모델의 기본 필드 그룹들

책임별로 분리된 필드 정의를 통해 명확한 구조를 제공합니다.
각 필드 그룹은 특정 목적과 책임을 가지며, 필요에 따라 조합하여 사용됩니다.
"""

from datetime import datetime
from sqlmodel import SQLModel, Field


# ═══════════════════════════════════════════════════════════════
# 🧩 필드 그룹들 - 책임별로 분리된 필드 정의
# ═══════════════════════════════════════════════════════════════

class DropCore(SQLModel):
    """Drop의 핵심 정보 필드들 (메타데이터 + 기본 파일 정보)"""
    
    # 공개 식별자 (URL에서 사용)
    slug: str = Field(index=True, unique=True)
    
    # Drop 기본 메타데이터
    title: str | None = None
    is_private: bool = True
    is_favorite: bool = False
    created_time: datetime
    
    # 파일 기본 정보
    file_name: str
    file_size: int
    file_type: str


class DropDetail(SQLModel):
    """Drop의 상세 정보 필드들 (상세 조회에 필요한 정보)"""
    
    description: str | None = None
    updated_time: datetime | None = None


class DropFileDetail(SQLModel):
    """Drop 파일의 상세 정보 필드들 (상세 조회에 필요한 정보)"""
    
    file_hash: str = Field(index=True)
    storage_type: str = Field(default="local")


class DropInternal(SQLModel):
    """Drop DB 내부 정보 필드들 (외부 비공개, 내부에서만 사용)"""
    
    # Integer Primary Key - SQLite에서 자동 증가 (DB 내부 식별자)
    id: int = Field(primary_key=True, default=None)
    
    # 민감 정보 및 내부 저장소 정보
    password: str | None = None  # 실제 패스워드 (민감정보)
    storage_path: str  # 물리적 저장 경로 (내부정보) 