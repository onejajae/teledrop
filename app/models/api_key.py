import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import SQLModel, Field, Session, select, func
from pydantic import computed_field


# API Key Models
class ApiKeyBase(SQLModel):
    """API Key 기본 모델"""
    name: str  # API 키 이름/설명 (예: "Mobile App", "CLI Tool")
    key_prefix: str = Field(index=True)  # 키 접두사 (공개적으로 표시 가능, 예: "tk_live_abc123...")
    
    # 권한 (단순화)
    can_read: bool = True    # 읽기 권한 (조회, 다운로드)
    can_write: bool = False  # 쓰기 권한 (생성, 수정, 삭제, 업로드)
    
    is_active: bool = True
    expires_at: datetime | None = None  # 만료일 (None이면 무제한)
    last_used_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class ApiKeyCreate(SQLModel):
    """API Key 생성 요청용"""
    name: str
    can_read: bool = True    # 기본값: 읽기 권한 있음
    can_write: bool = False  # 기본값: 쓰기 권한 없음
    expires_in_days: int | None = None  # 만료일까지 일수 (None이면 무제한)


class ApiKeyRead(ApiKeyBase):
    """API Key 읽기 응답용 (ID 포함)"""
    id: uuid.UUID
    user_id: str | None = None  # 사용자 식별자 (현재는 단순 문자열)


class ApiKeyPublic(ApiKeyRead):
    """공개 응답용 (민감정보 제외)"""
    key_hash: str = Field(exclude=True)  # 해시는 숨김
    
    @computed_field
    @property
    def is_expired(self) -> bool:
        """만료 여부 확인"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    @computed_field 
    @property
    def days_until_expiry(self) -> int | None:
        """만료까지 남은 일수"""
        if self.expires_at is None:
            return None
        delta = self.expires_at - datetime.now()
        return max(0, delta.days)
    
    @computed_field
    @property
    def status(self) -> str:
        """API 키 상태"""
        if not self.is_active:
            return "inactive"
        elif self.is_expired:
            return "expired"
        else:
            return "active"
    
    @computed_field
    @property
    def permission_level(self) -> str:
        """권한 레벨"""
        if self.can_read and self.can_write:
            return "읽기/쓰기"
        elif self.can_write:
            return "쓰기 전용"
        elif self.can_read:
            return "읽기 전용"
        else:
            return "권한 없음"
    
    @computed_field
    @property
    def permission_description(self) -> str:
        """권한 설명"""
        if self.can_read and self.can_write:
            return "모든 작업 가능 (조회, 생성, 수정, 삭제, 파일 업로드/다운로드)"
        elif self.can_write:
            return "쓰기 작업만 가능 (생성, 수정, 삭제, 파일 업로드)"
        elif self.can_read:
            return "읽기 작업만 가능 (조회, 파일 다운로드)"
        else:
            return "권한 없음"


class ApiKeyListElement(SQLModel):
    """목록용 간소화된 정보"""
    id: uuid.UUID
    name: str
    key_prefix: str
    can_read: bool
    can_write: bool
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    
    @computed_field
    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    @computed_field
    @property
    def status(self) -> str:
        if not self.is_active:
            return "inactive"
        elif self.is_expired:
            return "expired"
        else:
            return "active"
    
    @computed_field
    @property
    def permission_level(self) -> str:
        """권한 레벨"""
        if self.can_read and self.can_write:
            return "읽기/쓰기"
        elif self.can_write:
            return "쓰기 전용"
        elif self.can_read:
            return "읽기 전용"
        else:
            return "권한 없음"


class ApiKeysPublic(SQLModel):
    """API Key 목록 응답 래퍼"""
    api_keys: list[ApiKeyListElement]
    total_count: int


class ApiKeyUpdate(SQLModel):
    """API Key 업데이트용"""
    name: str | None = None
    can_read: bool | None = None
    can_write: bool | None = None
    is_active: bool | None = None
    expires_at: datetime | None = None


class ApiKeyCreateResponse(SQLModel):
    """API Key 생성 응답용 (실제 키 포함)"""
    api_key: ApiKeyPublic
    secret_key: str  # 실제 API 키 (한 번만 표시)


# Permission Preset Helper
class ApiKeyPresets:
    """API Key 권한 프리셋"""
    
    @staticmethod
    def read_only() -> dict:
        """읽기 전용 권한"""
        return {
            "can_read": True,
            "can_write": False,
        }
    
    @staticmethod
    def read_write() -> dict:
        """읽기/쓰기 권한"""
        return {
            "can_read": True,
            "can_write": True,
        }
    
    @staticmethod
    def write_only() -> dict:
        """쓰기 전용 권한"""
        return {
            "can_read": False,
            "can_write": True,
        }
    
    @staticmethod
    def no_access() -> dict:
        """권한 없음"""
        return {
            "can_read": False,
            "can_write": False,
        }


class ApiKey(ApiKeyBase, table=True):
    """API Key 데이터베이스 테이블"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    key_hash: str = Field(index=True, unique=True)  # 해시된 API 키 (검증용)
    user_id: str | None = None  # 향후 사용자 모델과 연결 가능
    
    # ===== 쿼리 메서드들 =====
    
    @classmethod
    def get_by_hash(
        cls,
        session: Session,
        key_hash: str
    ) -> Optional["ApiKey"]:
        """해시로 API Key 조회 - 인증용"""
        statement = select(cls).where(cls.key_hash == key_hash)
        result = session.exec(statement)
        return result.first()
    
    @classmethod
    def get_by_prefix(
        cls,
        session: Session,
        key_prefix: str
    ) -> Optional["ApiKey"]:
        """접두사로 API Key 조회"""
        statement = select(cls).where(cls.key_prefix == key_prefix)
        result = session.exec(statement)
        return result.first()
    
    @classmethod
    def list_active(
        cls,
        session: Session,
        include_expired: bool = False
    ) -> list["ApiKey"]:
        """활성 API Key 목록 조회"""
        statement = select(cls).where(cls.is_active == True)
        
        if not include_expired:
            # 만료되지 않은 키만 조회
            statement = statement.where(
                (cls.expires_at.is_(None)) | 
                (cls.expires_at > datetime.now())
            )
        
        statement = statement.order_by(cls.created_at.desc())
        result = session.exec(statement)
        return result.all()
    
    @classmethod
    def list_by_user(
        cls,
        session: Session,
        user_id: str
    ) -> list["ApiKey"]:
        """사용자별 API Key 목록 조회"""
        statement = select(cls).where(cls.user_id == user_id)
        statement = statement.order_by(cls.created_at.desc())
        result = session.exec(statement)
        return result.all()
    
    @classmethod
    def cleanup_expired(
        cls,
        session: Session,
        delete_expired: bool = False
    ) -> int:
        """만료된 API Key 정리"""
        now = datetime.now()
        
        if delete_expired:
            # 만료된 키 삭제
            statement = select(cls).where(
                (cls.expires_at.is_not(None)) & 
                (cls.expires_at < now)
            )
            expired_keys = session.exec(statement).all()
            
            for key in expired_keys:
                session.delete(key)
            
            session.commit()
            return len(expired_keys)
        else:
            # 만료된 키 비활성화
            statement = select(cls).where(
                (cls.expires_at.is_not(None)) & 
                (cls.expires_at < now) &
                (cls.is_active == True)
            )
            expired_keys = session.exec(statement).all()
            
            for key in expired_keys:
                key.is_active = False
                key.updated_at = now
                session.add(key)
            
            session.commit()
            return len(expired_keys)
    
    @classmethod
    def get_usage_stats(
        cls,
        session: Session,
        days: int = 30
    ) -> dict:
        """API Key 사용 통계"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 총 키 수
        total_keys = session.exec(select(func.count(cls.id))).first()
        
        # 활성 키 수
        active_keys = session.exec(
            select(func.count(cls.id)).where(cls.is_active == True)
        ).first()
        
        # 최근 사용된 키 수
        recently_used = session.exec(
            select(func.count(cls.id)).where(
                (cls.last_used_at.is_not(None)) &
                (cls.last_used_at > cutoff_date)
            )
        ).first()
        
        # 만료된 키 수
        expired_keys = session.exec(
            select(func.count(cls.id)).where(
                (cls.expires_at.is_not(None)) &
                (cls.expires_at < datetime.now())
            )
        ).first()
        
        return {
            "total_keys": total_keys or 0,
            "active_keys": active_keys or 0,
            "recently_used": recently_used or 0,
            "expired_keys": expired_keys or 0,
            "usage_period_days": days
        }
    
    # ===== 인스턴스 메서드들 =====
    
    def has_permission(self, action: str) -> bool:
        """권한 확인"""
        if not self.is_active:
            return False
        
        if self.is_expired:
            return False
        
        if action in ["read", "download", "view"]:
            return self.can_read
        elif action in ["write", "upload", "create", "update", "delete"]:
            return self.can_write
        else:
            return False
    
    def get_permissions_dict(self) -> dict:
        """권한 딕셔너리 반환"""
        return {
            "can_read": self.can_read,
            "can_write": self.can_write
        }
    
    def apply_preset(self, preset_name: str) -> None:
        """권한 프리셋 적용"""
        presets = {
            "read_only": ApiKeyPresets.read_only(),
            "read_write": ApiKeyPresets.read_write(),
            "write_only": ApiKeyPresets.write_only(),
            "no_access": ApiKeyPresets.no_access()
        }
        
        if preset_name in presets:
            preset = presets[preset_name]
            self.can_read = preset["can_read"]
            self.can_write = preset["can_write"]
            self.updated_at = datetime.now()
    
    def update_last_used(self) -> None:
        """마지막 사용 시간 업데이트"""
        self.last_used_at = datetime.now()
    
    def deactivate(self) -> None:
        """API Key 비활성화"""
        self.is_active = False
        self.updated_at = datetime.now()
    
    def extend_expiry(self, days: int) -> None:
        """만료일 연장"""
        if self.expires_at:
            self.expires_at += timedelta(days=days)
        else:
            self.expires_at = datetime.now() + timedelta(days=days)
        self.updated_at = datetime.now() 