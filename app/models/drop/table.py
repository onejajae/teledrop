"""
Drop 테이블 모델

Drop SQLModel 테이블 정의와 모든 쿼리 메서드들을 제공합니다.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Literal

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func

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
    async def get_by_slug(
        cls, 
        session: AsyncSession, 
        slug: str, 
    ) -> Optional["Drop"]:
        """slug로 Drop 조회"""
        statement = select(cls).where(cls.slug == slug)
        result = await session.exec(statement)
        return result.first()
    
    @classmethod
    async def get_by_id(
        cls, 
        session: AsyncSession, 
        drop_id: int, 
    ) -> Optional["Drop"]:
        """ID로 Drop 조회"""
        statement = select(cls).where(cls.id == drop_id)
        result = await session.exec(statement)
        return result.first()
    
    @classmethod
    async def list_all(
        cls,
        session: AsyncSession,
        is_private: bool | None = None,
        is_favorite: bool | None = None,
        has_password: bool | None = None,
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
        if has_password is not None:
            filters.append(cls.password.isnot(None) == has_password)
        
        # 2단계: 정렬 컬럼 준비 (기본값 → 특별 케이스)
        sort_column = getattr(cls, sortby)
        if sortby == "title":
            # title이 None이면 file_name으로 대체
            sort_column = func.coalesce(cls.title, cls.file_name).collate("NOCASE")
        
        if orderby == "asc":
            sort_column = sort_column.asc()
        else:
            sort_column = sort_column.desc()
        
        # 3단계: 기본 쿼리 구성 (템플릿 패턴)
        statement = select(cls).where(*filters).order_by(sort_column)
        
        # 4단계: 페이지네이션 적용 (조건부)
        if offset is not None:
            statement = statement.offset(offset)
        if limit:
            statement = statement.limit(limit)
        
        result = await session.exec(statement)
        return list(result)
    
    @classmethod
    async def count_all(
        cls,
        session: AsyncSession,
        is_private: bool | None = None,
        is_favorite: bool | None = None,
        has_password: bool | None = None
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
        if has_password is not None:
            filters.append(cls.password.isnot(None) == has_password)
        
        # 카운트 쿼리 구성 (템플릿 패턴)
        statement = select(func.count(cls.id)).where(*filters)
        
        result = await session.exec(statement)
        return result.one()

    @classmethod
    async def list_with_count(
        cls,
        session: AsyncSession,
        is_private: bool | None = None,
        is_favorite: bool | None = None,
        has_password: bool | None = None,
        limit: int | None = None,
        offset: int | None = 0,
        sortby: Literal["created_time", "title", "file_size"] | None = "created_time",
        orderby: Literal["asc", "desc"] | None = "desc"
    ) -> tuple[list["Drop"], int]:
        """
        Drop 목록과 전체 개수를 동시에 반환
        """
        drops = cls.list_all(
            session=session,
            is_private=is_private,
            is_favorite=is_favorite,
            has_password=has_password,
            limit=limit,
            offset=offset,
            sortby=sortby,
            orderby=orderby
        )
        
        count = cls.count_all(
            session=session,
            is_private=is_private,
            is_favorite=is_favorite,
            has_password=has_password
        )

        return await asyncio.gather(drops, count)
    
    # ===== 인스턴스 메서드들 =====
    
    def check_password(self, password: str | None) -> bool:
        """패스워드 확인 (향후 해시 검증으로 개선 예정)"""
        if not self.password:
            return True  # 패스워드가 설정되지 않은 경우
        
        return self.password == password


    # ===== 생성/저장 헬퍼 메서드들 =====
    
    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        drop_data: dict,
        slug: str,
    ) -> "Drop":
        """Drop을 생성하고 데이터베이스에 저장"""
        drop = cls(**drop_data)
        drop.slug = slug
        drop.created_time = datetime.now(timezone.utc)
        
        session.add(drop)
        await session.commit()
        await session.refresh(drop)
        return drop

    async def delete(self, session: AsyncSession) -> None:
        """
        Drop을 데이터베이스에서 삭제
        (파일 정보가 통합되어 있으므로 단일 삭제)
        """
        await session.delete(self)
        await session.commit()
    
    async def update(self, session: AsyncSession, **kwargs) -> None:
        """
        Drop의 필드들을 업데이트
        """
        # 유효한 필드만 업데이트
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # 업데이트 시간 갱신
        self.updated_time = datetime.now(timezone.utc)
        
        await session.commit()
        await session.refresh(self)
    
    @classmethod
    async def delete_by_slug(cls, session: AsyncSession, slug: str) -> bool:
        """
        slug로 Drop을 찾아서 삭제
        
        Args:
            session: 데이터베이스 세션
            slug: Drop slug
            
        Returns:
            bool: 삭제 성공 여부
        """
        drop = await cls.get_by_slug(session, slug)
        if drop:
            await drop.delete(session)
            return True
        return False
    
    
    @classmethod
    async def get_by_file_hash(cls, session: AsyncSession, file_hash: str) -> Optional["Drop"]:
        """파일 해시로 Drop 조회 (중복 체크용)"""
        statement = select(cls).where(cls.file_hash == file_hash)
        result = await session.exec(statement)
        return result.first() 