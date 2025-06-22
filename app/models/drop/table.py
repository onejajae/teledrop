"""
Drop 테이블 모델

Drop SQLModel 테이블 정의와 모든 쿼리 메서드들을 제공합니다.
"""

from datetime import datetime
from typing import Optional, Literal

from sqlmodel import Session, select, func

from .base import DropInternal, DropCore, DropDetail, DropFileDetail


# ═══════════════════════════════════════════════════════════════
# 🗄️ Drop 테이블 모델
# ═══════════════════════════════════════════════════════════════

class Drop(DropInternal, DropCore, DropDetail, DropFileDetail, table=True):
    """
    Drop SQLModel 테이블
    
    모든 필드 그룹을 조합하여 완전한 Drop 정보를 포함합니다.
    테이블 관련 쿼리 메서드들과 비즈니스 로직을 제공합니다.
    """
    
    # Computed properties
    @property
    def has_password(self) -> bool:
        """패스워드 설정 여부"""
        return bool(self.password)
    
    # ===== 클래스 메서드들 (쿼리) =====
    
    @classmethod
    def get_by_slug(
        cls, 
        session: Session, 
        slug: str, 
    ) -> Optional["Drop"]:
        """slug로 Drop 조회"""
        statement = select(cls).where(cls.slug == slug)
        result = session.exec(statement)
        return result.first()
    
    @classmethod
    def get_by_id(
        cls, 
        session: Session, 
        drop_id: int, 
    ) -> Optional["Drop"]:
        """ID로 Drop 조회"""
        statement = select(cls).where(cls.id == drop_id)
        result = session.exec(statement)
        return result.first()
    
    @classmethod
    async def list_all(
        cls,
        session: Session,
        is_private: bool | None = None,
        is_favorite: bool | None = None,
        limit: int | None = None,
        offset: int | None = 0,
        sortby: Literal["created_time", "title", "file_size"] | None = "created_time",
        orderby: Literal["asc", "desc"] | None = "desc"
    ) -> list["Drop"]:
        """
        Drop 목록 조회 (비동기)
        """
        # 1단계: 필터 조건들 준비 (간단한 직접 방식)
        filters = []
        if is_private is not None:
            filters.append(cls.is_private == is_private)
        if is_favorite is not None:
            filters.append(cls.is_favorite == is_favorite)
        
        # 2단계: 정렬 컬럼 준비 (기본값 → 특별 케이스)
        sort_column = getattr(cls, sortby)
        if sortby == "title":
            # title이 None이면 file_name으로 대체 (스마트 정렬)
            sort_column = func.coalesce(cls.title, cls.file_name)
        
        if orderby.lower() == "desc":
            sort_column = sort_column.desc()
        else:
            sort_column = sort_column.asc()  # 명시적 asc 처리
        
        # 3단계: 기본 쿼리 구성 (템플릿 패턴)
        statement = select(cls).where(*filters).order_by(sort_column)
        
        # 4단계: 페이지네이션 적용 (조건부)
        if offset:
            statement = statement.offset(offset)
        if limit:
            statement = statement.limit(limit)
        
        result = session.exec(statement)
        return list(result)
    
    @classmethod
    async def count_all(
        cls,
        session: Session,
        is_private: bool | None = None,
        is_favorite: bool | None = None
    ) -> int:
        """
        Drop 전체 개수 조회 (비동기)
        """
        # 필터 조건들 준비 (list_all과 동일한 조건)
        filters = []
        if is_private is not None:
            filters.append(cls.is_private == is_private)
        if is_favorite is not None:
            filters.append(cls.is_favorite == is_favorite)
        
        # 카운트 쿼리 구성 (템플릿 패턴)
        statement = select(func.count(cls.id)).where(*filters)
        
        result = session.exec(statement)
        return result.one()

    @classmethod
    async def list_with_count(
        cls,
        session: Session,
        is_private: bool | None = None,
        is_favorite: bool | None = None,
        limit: int | None = None,
        offset: int | None = 0,
        sortby: Literal["created_time", "title", "file_size"] | None = "created_time",
        orderby: Literal["asc", "desc"] | None = "desc"
    ) -> tuple[list["Drop"], int]:
        """
        Drop 목록과 전체 개수를 동시에 반환
        """
        drops = await cls.list_all(
            session=session,
            is_private=is_private,
            is_favorite=is_favorite,
            limit=limit,
            offset=offset,
            sortby=sortby,
            orderby=orderby
        )
        
        total_count = await cls.count_all(
            session=session,
            is_private=is_private,
            is_favorite=is_favorite
        )

        return drops, total_count
    
    # ===== 인스턴스 메서드들 =====
    
    def update_fields(self, **kwargs) -> None:
        """필드 업데이트 헬퍼"""
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        self.updated_time = datetime.now()
    

    def check_password(self, password: str | None) -> bool:
        """패스워드 확인 (향후 해시 검증으로 개선 예정)"""
        if not self.password:
            return True  # 패스워드가 설정되지 않은 경우
        return self.password == password


    # ===== 생성/저장 헬퍼 메서드들 =====
    
    @classmethod
    def create(
        cls,
        session: Session,
        drop_data: dict,
        slug: str,
        created_time: datetime
    ) -> "Drop":
        """Drop을 생성하고 데이터베이스에 저장"""
        drop = cls(**drop_data)
        drop.slug = slug
        drop.created_time = created_time
        
        session.add(drop)
        session.commit()
        session.refresh(drop)
        return drop

    def delete(self, session: Session) -> None:
        """
        Drop을 데이터베이스에서 삭제
        (파일 정보가 통합되어 있으므로 단일 삭제)
        """
        session.delete(self)
        session.commit()
    
    def update(self, session: Session, **kwargs) -> None:
        """
        Drop의 필드들을 업데이트
        """
        # 유효한 필드만 업데이트
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        
        # 업데이트 시간 갱신
        self.updated_time = datetime.now()
        
        session.commit()
        session.refresh(self)
    
    @classmethod
    def delete_by_slug(cls, session: Session, slug: str) -> bool:
        """
        slug로 Drop을 찾아서 삭제
        
        Args:
            session: 데이터베이스 세션
            slug: Drop slug
            
        Returns:
            bool: 삭제 성공 여부
        """
        drop = cls.get_by_slug(session, slug)
        if drop:
            drop.delete(session)
            return True
        return False
    
    
    @classmethod
    def get_by_file_hash(cls, session: Session, file_hash: str) -> Optional["Drop"]:
        """파일 해시로 Drop 조회 (중복 체크용)"""
        statement = select(cls).where(cls.file_hash == file_hash)
        result = session.exec(statement)
        return result.first() 