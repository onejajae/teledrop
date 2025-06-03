import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlmodel import SQLModel, Field, Relationship, Session, select
from pydantic import computed_field
import asyncio

if TYPE_CHECKING:
    from .file import File


# Drop Models - 개선된 구조
class DropBase(SQLModel):
    """Drop 기본 모델 - 메타데이터만 관리"""
    key: str = Field(index=True, unique=True)
    title: str | None = None
    description: str | None = None
    password: str | None = None
    user_only: bool = True
    favorite: bool = False
    created_at: datetime
    updated_at: datetime | None = None


class DropCreate(SQLModel):
    """Drop 생성 요청용 - key는 핸들러에서 생성"""
    key: str | None = None
    title: str | None = None
    description: str | None = None
    password: str | None = None
    user_only: bool = True
    favorite: bool = False


class DropRead(DropBase):
    """Drop 읽기 응답용 (ID 포함)"""
    id: uuid.UUID
    file: "File"  # 1:1 관계 - 필수


class DropPublic(DropRead):
    """공개 응답용 (민감정보 제외)"""
    password: str | None = Field(exclude=True)
    
    @computed_field
    @property
    def required_password(self) -> bool:
        return bool(self.password)
    
    @computed_field
    @property
    def has_file(self) -> bool:
        return True  # 모든 Drop은 file을 가짐


class DropListElement(SQLModel):
    """목록용 간소화된 정보 - 성능 최적화"""
    id: uuid.UUID
    key: str
    title: str | None
    favorite: bool
    user_only: bool
    created_at: datetime
    
    # 보안상 제외하되 required_password 계산을 위해 필요
    password: str | None = Field(exclude=True)
    
    # 파일 정보 요약 (조인 없이 가져올 수 있도록)
    has_file: bool = True  # 모든 Drop은 file을 가짐
    file_size: int
    file_type: str
    file_name: str  # 기존 API 호환성을 위한 original_filename
    
    @computed_field
    @property
    def required_password(self) -> bool:
        """비밀번호 필요 여부를 동적으로 계산"""
        return bool(self.password)


class DropsPublic(SQLModel):
    """Drop 목록 응답 래퍼"""
    drops: list[DropListElement]
    total_count: int


class DropUpdate(SQLModel):
    """Drop 업데이트용 - 선택적 필드들"""
    title: str | None = None
    description: str | None = None
    favorite: bool | None = None
    user_only: bool | None = None
    password: str | None = None


class DropPasswordCheck(SQLModel):
    """패스워드 확인용"""
    password: str | None = None


class Drop(DropBase, table=True):
    """Drop 데이터베이스 테이블"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # 1:1 관계: Drop은 반드시 하나의 File을 가져야 함
    file: "File" = Relationship(back_populates="drop", sa_relationship_kwargs={"uselist": False})
    
    # ===== 쿼리 메서드들 (중복 제거용) =====
    
    @classmethod
    def get_by_key(
        cls, 
        session: Session, 
        key: str, 
    ) -> Optional["Drop"]:
        """키로 Drop 조회 - 가장 자주 사용되는 패턴"""
        statement = select(cls).where(cls.key == key)
        result = session.exec(statement)
        return result.first()
    
    @classmethod
    def get_by_id(
        cls, 
        session: Session, 
        drop_id: uuid.UUID, 
    ) -> Optional["Drop"]:
        """ID로 Drop 조회"""
        statement = select(cls).where(cls.id == drop_id)
        
        result = session.exec(statement)
        return result.first()
    
    @classmethod
    async def list_all(
        cls,
        session: Session,
        user_only: Optional[bool] = None,
        favorites_only: bool = False,
        limit: Optional[int] = None,
        offset: int = 0,
        sortby: Optional[str] = "created_at",
        orderby: Optional[str] = "desc"
    ) -> list["Drop"]:
        """Drop 목록 조회 - 명시적 join으로 정렬 지원"""
        from sqlmodel import func
        from .file import File
        
        statement = select(cls)
        
        # 필터링 조건들
        if user_only is not None:
            statement = statement.where(cls.user_only == user_only)
        if favorites_only:
            statement = statement.where(cls.favorite == True)
        
        # 정렬을 위한 명시적 join
        if sortby in ["title", "file_size"]:
            statement = statement.outerjoin(File)
        
        # 동적 정렬
        if sortby == "title":
            sort_column = func.coalesce(cls.title, File.original_filename).collate("NOCASE")
        elif sortby == "file_size":
            sort_column = func.coalesce(File.file_size, 0)
        else:
            sort_column = cls.created_at
        
        # 정렬 순서 적용
        if orderby == "asc":
            statement = statement.order_by(sort_column.asc())
        else:
            statement = statement.order_by(sort_column.desc())
        
        # 페이징
        if limit:
            statement = statement.limit(limit)
        if offset:
            statement = statement.offset(offset)
        
        
        result = session.exec(statement)
        return result.all()
    
    @classmethod
    async def count_all(
        cls,
        session: Session,
        user_only: Optional[bool] = None,
        favorites_only: bool = False
    ) -> int:
        """조건에 맞는 Drop 개수 조회"""
        from sqlmodel import func
        
        statement = select(func.count(cls.id))
        
        if user_only is not None:
            statement = statement.where(cls.user_only == user_only)
        if favorites_only:
            statement = statement.where(cls.favorite == True)
        
        result = session.exec(statement)
        return result.first() or 0
    
    @classmethod
    def search_by_title(
        cls,
        session: Session,
        query: str,
    ) -> list["Drop"]:
        """제목으로 Drop 검색"""
        statement = select(cls).where(
            cls.title.ilike(f"%{query}%")
        ).order_by(cls.created_at.desc())
        
        
        result = session.exec(statement)
        return result.all()
    
    @classmethod
    def get_favorites(
        cls,
        session: Session,
    ) -> list["Drop"]:
        """즐겨찾기 Drop 목록 조회"""
        statement = select(cls).where(cls.favorite == True)
        
        statement = statement.order_by(cls.created_at.desc())
        
        result = session.exec(statement)
        return result.all()
    
    @classmethod
    async def list_with_count(
        cls,
        session: Session,
        user_only: Optional[bool] = None,
        favorites_only: bool = False,
        limit: Optional[int] = None,
        offset: int = 0,
        sortby: Optional[str] = "created_at",
        orderby: Optional[str] = "desc"
    ) -> tuple[list["Drop"], int]:
        """
        Drop 목록과 전체 개수를 동시에 반환 (비동기 병렬 실행)
        """
        drops_task = cls.list_all(
            session=session,
            user_only=user_only,
            favorites_only=favorites_only,
            limit=limit,
            offset=offset,
            sortby=sortby,
            orderby=orderby
        )
        count_task = cls.count_all(
            session=session,
            user_only=user_only,
            favorites_only=favorites_only
        )
        drops, total_count = await asyncio.gather(drops_task, count_task)
        return drops, total_count
    
    # ===== 인스턴스 메서드들 =====
    
    def update_fields(self, **kwargs) -> None:
        """필드 업데이트 헬퍼"""
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        self.updated_at = datetime.now()
    
    def toggle_favorite(self) -> None:
        """즐겨찾기 토글"""
        self.favorite = not self.favorite
        self.updated_at = datetime.now()
    
    def check_password(self, password: str | None) -> bool:
        """패스워드 확인"""
        if not self.password:
            return True  # 패스워드가 설정되지 않은 경우
        return self.password == password
    
    @property
    def is_public(self) -> bool:
        """공개 Drop인지 확인"""
        return not self.user_only and not self.password
