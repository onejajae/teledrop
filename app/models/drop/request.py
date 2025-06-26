"""
Drop API 요청 스키마들

클라이언트로부터 받는 Form 요청 데이터 구조를 정의합니다.
실제 API에서 사용되는 Form 스키마들만 포함합니다.
"""

from sqlmodel import SQLModel, Field


# ═══════════════════════════════════════════════════════════════
# �� Drop 생성용 스키마
# ═══════════════════════════════════════════════════════════════

class DropCreateForm(SQLModel):
    """Drop 생성 Form - 순수 Drop 메타데이터만 포함 (파일 정보는 UploadFile에서 추출)"""
    
    # Drop 메타데이터 (선택적)
    slug: str | None = Field(None, description="Drop 슬러그 (없으면 자동 생성)")
    title: str | None = Field(None, max_length=200, description="Drop 제목 (최대 200자)")
    description: str | None = Field(None, max_length=1000, description="Drop 설명 (최대 1000자)")
    password: str | None = Field(None, max_length=100, description="Drop 패스워드 (최대 100자)")
    is_private: bool = Field(True, description="비공개 여부 (true: 로그인 필요, false: 공개)")
    is_favorite: bool = Field(False, description="즐겨찾기 여부")
    
    # 파일 정보 제거 - UploadFile에서 직접 추출
    # filename, content_type, file_size 필드 제거됨


# ═══════════════════════════════════════════════════════════════
# 📝 Drop 수정용 스키마
# ═══════════════════════════════════════════════════════════════

class DropUpdateDetailForm(SQLModel):
    """Drop 상세정보 수정 Form"""
    title: str | None = None
    description: str | None = None


class DropUpdatePermissionForm(SQLModel):
    """Drop 권한 수정 Form"""
    is_private: bool = Field(description="사용자 전용 여부 (true: 로그인 필요, false: 공개)")
    


class DropSetPasswordForm(SQLModel):
    """Drop 패스워드 설정 Form"""
    new_password: str = Field(
        min_length=1, 
        max_length=100, 
        description="새로운 패스워드 (1-100자)"
    )


class DropUpdateFavoriteForm(SQLModel):
    """Drop 즐겨찾기 수정 Form"""
    is_favorite: bool = Field(description="즐겨찾기 여부")
