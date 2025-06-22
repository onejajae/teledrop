"""
Drop API 요청 스키마들

클라이언트로부터 받는 Form 요청 데이터 구조를 정의합니다.
실제 API에서 사용되는 Form 스키마들만 포함합니다.
"""

from sqlmodel import SQLModel, Field


# ═══════════════════════════════════════════════════════════════
# 📝 Drop 생성용 스키마
# ═══════════════════════════════════════════════════════════════

class DropCreateForm(SQLModel):
    """Drop 생성 Form - 파일 업로드와 함께 사용 (완전한 Drop 엔티티 정보)"""
    
    # Drop 메타데이터 (선택적)
    slug: str | None = Field(None, description="Drop 슬러그 (없으면 자동 생성)")
    title: str | None = Field(None, max_length=200, description="Drop 제목 (최대 200자)")
    description: str | None = Field(None, max_length=1000, description="Drop 설명 (최대 1000자)")
    password: str | None = Field(None, max_length=100, description="Drop 패스워드 (최대 100자)")
    is_private: bool = Field(True, description="비공개 여부 (true: 로그인 필요, false: 공개)")
    is_favorite: bool = Field(False, description="즐겨찾기 여부")
    
    # 파일 정보 (UploadFile에서 추출하여 설정)
    filename: str | None = Field(None, description="업로드된 파일명")
    content_type: str | None = Field(None, description="파일 MIME 타입")
    file_size: int | None = Field(None, description="파일 크기 (bytes)")


# ═══════════════════════════════════════════════════════════════
# 📝 Drop 수정용 스키마
# ═══════════════════════════════════════════════════════════════

class DropUpdateDetailForm(SQLModel):
    """Drop 상세정보 수정 Form"""
    title: str | None = Field(
        None, 
        max_length=200, 
        description="Drop 제목 (최대 200자)"
    )
    description: str | None = Field(
        None, 
        max_length=1000, 
        description="Drop 설명 (최대 1000자)"
    )


class DropUpdatePermissionForm(SQLModel):
    """Drop 권한 수정 Form"""
    # 프론트엔드 호환성을 위해 user_only 필드명 사용 (is_private과 반대 의미)
    user_only: bool = Field(description="사용자 전용 여부 (true: 로그인 필요, false: 공개)")
    
    @property
    def is_private(self) -> bool:
        """내부적으로는 is_private로 변환"""
        return self.user_only


class DropSetPasswordForm(SQLModel):
    """Drop 패스워드 설정 Form"""
    new_password: str = Field(
        min_length=1, 
        max_length=100, 
        description="새로운 패스워드 (1-100자)"
    )


class DropUpdateFavoriteForm(SQLModel):
    """Drop 즐겨찾기 수정 Form"""
    favorite: bool = Field(description="즐겨찾기 여부")
    
    @property
    def is_favorite(self) -> bool:
        """내부적으로는 is_favorite로 변환"""
        return self.favorite 