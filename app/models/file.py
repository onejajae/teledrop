import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlmodel import SQLModel, Field, Relationship, Session, select
from sqlalchemy.orm import selectinload

if TYPE_CHECKING:
    from .drop import Drop


# File Models - 개선된 구조
class FileBase(SQLModel):
    """File 기본 모델 - 해시 저장 지원"""
    original_filename: str  # 원본 파일명
    file_size: int  # 파일 크기 (bytes)
    file_type: str  # MIME 타입
    file_hash: str = Field(index=True)  # 파일 해시 (중복 체크 + 무결성 검증용)
    storage_type: str = "local"  # "local", "s3", etc.
    storage_path: str  # 실제 저장 경로
    created_at: datetime


class FileCreate(SQLModel):
    """File 생성 요청용"""
    original_filename: str
    file_size: int
    file_type: str
    file_hash: str
    storage_type: str = "local"
    storage_path: str


class FileRead(FileBase):
    """File 읽기 응답용 (ID 포함)"""
    id: uuid.UUID
    drop_id: uuid.UUID


class FilePublic(FileRead):
    """공개 응답용 (스토리지 경로와 해시 숨김)"""
    storage_path: str = Field(exclude=True)
    file_hash: str = Field(exclude=True)
    
    @property
    def size_formatted(self) -> str:
        """사람이 읽기 쉬운 파일 크기"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"


class FileUpdate(SQLModel):
    """File 업데이트용 (제한적)"""
    original_filename: str | None = None  # 파일명만 변경 가능


class File(FileBase, table=True):
    """File 데이터베이스 테이블"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    drop_id: uuid.UUID = Field(foreign_key="drop.id", index=True, unique=True, nullable=False)  # 1:1 관계를 위한 unique 제약, NOT NULL
    
    # 1:1 관계: File은 반드시 하나의 Drop에 속함
    drop: "Drop" = Relationship(back_populates="file")
    
    # ===== 쿼리 메서드들 (중복 제거용) =====
    
    @classmethod
    def get_by_drop_key(
        cls,
        session: Session,
        drop_key: str,
        include_drop: bool = False
    ) -> Optional["File"]:
        """Drop 키로 파일 조회 - 가장 자주 사용되는 패턴"""
        from .drop import Drop
        
        statement = select(cls).join(Drop).where(Drop.key == drop_key)
        if include_drop:
            statement = statement.options(selectinload(cls.drop))
        
        result = session.exec(statement)
        return result.first()
    
    @classmethod
    def get_by_drop_id(
        cls,
        session: Session,
        drop_id: uuid.UUID,
        include_drop: bool = False
    ) -> Optional["File"]:
        """Drop ID로 파일 조회"""
        statement = select(cls).where(cls.drop_id == drop_id)
        if include_drop:
            statement = statement.options(selectinload(cls.drop))
        
        result = session.exec(statement)
        return result.first()
    
    @classmethod
    def get_by_hash(
        cls,
        session: Session,
        file_hash: str,
        include_drop: bool = False
    ) -> Optional["File"]:
        """파일 해시로 조회 - 중복 체크용"""
        statement = select(cls).where(cls.file_hash == file_hash)
        if include_drop:
            statement = statement.options(selectinload(cls.drop))
        
        result = session.exec(statement)
        return result.first()
    
    @classmethod
    def list_by_type(
        cls,
        session: Session,
        file_type: str,
        include_drops: bool = False
    ) -> list["File"]:
        """파일 타입별 조회"""
        statement = select(cls).where(cls.file_type == file_type)
        if include_drops:
            statement = statement.options(selectinload(cls.drop))
        
        statement = statement.order_by(cls.created_at.desc())
        
        result = session.exec(statement)
        return result.all()
    
    @classmethod
    def list_by_storage_type(
        cls,
        session: Session,
        storage_type: str,
        include_drops: bool = False
    ) -> list["File"]:
        """스토리지 타입별 조회"""
        statement = select(cls).where(cls.storage_type == storage_type)
        if include_drops:
            statement = statement.options(selectinload(cls.drop))
        
        statement = statement.order_by(cls.created_at.desc())
        
        result = session.exec(statement)
        return result.all()
    
    @classmethod
    def get_storage_stats(
        cls,
        session: Session
    ) -> dict:
        """스토리지 통계 조회"""
        from sqlmodel import func
        
        # 총 파일 수와 크기
        total_result = session.exec(
            select(
                func.count(cls.id).label('total_files'),
                func.sum(cls.file_size).label('total_size')
            )
        )
        total_stats = total_result.first()
        
        # 스토리지 타입별 통계
        storage_result = session.exec(
            select(
                cls.storage_type,
                func.count(cls.id).label('file_count'),
                func.sum(cls.file_size).label('storage_size')
            ).group_by(cls.storage_type)
        )
        storage_stats = storage_result.all()
        
        return {
            "total_files": total_stats.total_files or 0,
            "total_size": total_stats.total_size or 0,
            "by_storage": [
                {
                    "storage_type": stat.storage_type,
                    "file_count": stat.file_count,
                    "storage_size": stat.storage_size
                }
                for stat in storage_stats
            ]
        }
    
    # ===== 인스턴스 메서드들 =====
    
    def get_file_extension(self) -> str:
        """파일 확장자 추출"""
        if '.' in self.original_filename:
            return self.original_filename.split('.')[-1].lower()
        return ""
    
    def is_image(self) -> bool:
        """이미지 파일인지 확인"""
        return self.file_type.startswith('image/')
    
    def is_video(self) -> bool:
        """비디오 파일인지 확인"""
        return self.file_type.startswith('video/')
    
    def is_audio(self) -> bool:
        """오디오 파일인지 확인"""
        return self.file_type.startswith('audio/')
    
    def is_text(self) -> bool:
        """텍스트 파일인지 확인"""
        return self.file_type.startswith('text/')
    
    def get_category(self) -> str:
        """파일 카테고리 반환"""
        if self.is_image():
            return "image"
        elif self.is_video():
            return "video"
        elif self.is_audio():
            return "audio"
        elif self.is_text():
            return "text"
        else:
            return "other"
