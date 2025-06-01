# 데이터 모델

Teledrop은 **SQLModel**을 활용하여 데이터 모델을 정의합니다. SQLModel은 SQLAlchemy와 Pydantic을 통합하여 **타입 안전성**과 **ORM 기능**을 모두 제공합니다.

## 모델 구조

```
app/models/
├── __init__.py          # 모델 통합 export
├── drop.py              # Drop 도메인 모델 (272줄)
│   ├── DropBase         # 기본 필드
│   ├── DropCreate       # 생성 요청
│   ├── DropRead         # 읽기 응답
│   ├── DropPublic       # 공개 응답
│   ├── DropListElement  # 목록 항목
│   ├── DropsPublic      # 목록 컨테이너
│   ├── DropUpdate       # 업데이트 요청
│   └── Drop             # DB 테이블 (쿼리 메서드 포함)
├── file.py              # File 도메인 모델 (227줄)
│   ├── FileBase         # 기본 필드
│   ├── FileCreate       # 생성 요청
│   ├── FileRead         # 읽기 응답
│   ├── FilePublic       # 공개 응답
│   ├── FileUpdate       # 업데이트 요청
│   └── File             # DB 테이블
├── api_key.py           # API Key 도메인 모델 (395줄)
│   ├── ApiKeyBase       # 기본 필드
│   ├── ApiKeyCreate     # 생성 요청
│   ├── ApiKeyRead       # 읽기 응답
│   ├── ApiKeyPublic     # 공개 응답
│   ├── ApiKeyListElement # 목록 항목
│   ├── ApiKeysPublic    # 목록 컨테이너
│   ├── ApiKeyUpdate     # 업데이트 요청
│   ├── ApiKeyCreateResponse # 생성 응답 (해시 전 원본 키 포함)
│   ├── ApiKeyPresets    # 사전 정의된 권한 세트
│   └── ApiKey           # DB 테이블
└── auth.py              # 인증 관련 모델 (27줄)
    ├── AccessToken      # 토큰 응답
    ├── TokenPayload     # 토큰 페이로드
    └── AuthData         # 인증 요청 데이터
```

## 계층적 모델 설계

SQLModel을 활용한 계층적 모델 설계는 Teledrop의 핵심 아키텍처 패턴 중 하나입니다. 다음과 같은 구조로 설계되었습니다:

1. **기본 모델(Base Model)**: 공통 필드 정의
2. **테이블 모델(Table Model)**: 데이터베이스 테이블 매핑
3. **요청 모델(Request Model)**: API 요청 검증용
4. **응답 모델(Response Model)**: API 응답 직렬화용

### 예시: Drop 모델 계층 구조

```python
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

class Drop(DropBase, table=True):
    """Drop 데이터베이스 테이블"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # 1:1 관계: Drop은 반드시 하나의 File을 가져야 함
    file: "File" = Relationship(back_populates="drop", sa_relationship_kwargs={"uselist": False})
    
    # 쿼리 메서드들 (중복 제거용)
    @classmethod
    def get_by_key(cls, session: Session, key: str, include_file: bool = True) -> Optional["Drop"]:
        """키로 Drop 조회"""
        statement = select(cls).where(cls.key == key)
        if include_file:
            statement = statement.options(selectinload(cls.file))
        
        result = session.exec(statement)
        return result.first()
    
    @classmethod
    def list_all(cls, session: Session, 
                 skip: int = 0, 
                 limit: int = 100,
                 favorite_only: bool = False) -> List["Drop"]:
        """Drop 목록 조회"""
        statement = select(cls).options(selectinload(cls.file))
        
        if favorite_only:
            statement = statement.where(cls.favorite == True)
            
        statement = statement.offset(skip).limit(limit).order_by(cls.created_at.desc())
        return list(session.exec(statement))

class DropCreate(SQLModel):
    """Drop 생성 요청용"""
    title: str | None = None
    description: str | None = None
    password: str | None = None
    user_only: bool = True
    favorite: bool = False

class DropRead(DropBase):
    """읽기 응답용"""
    id: uuid.UUID
    file: Optional["FileRead"] = None

class DropPublic(DropRead):
    """공개 응답용 (민감정보 제외)"""
    password: str | None = Field(exclude=True)
    
    @computed_field
    @property
    def required_password(self) -> bool:
        """패스워드 필요 여부 (프론트엔드 표시용)"""
        return bool(self.password)

class DropListElement(SQLModel):
    """목록용 간소화된 정보 - 성능 최적화"""
    id: uuid.UUID
    key: str
    title: str | None
    favorite: bool
    user_only: bool
    created_at: datetime
    password: str | None = Field(exclude=True)
    
    # 파일 정보 요약 (조인 없이 가져올 수 있도록)
    has_file: bool = True
    file_size: int
    file_type: str
    file_name: str
    
    @computed_field
    @property
    def required_password(self) -> bool:
        return bool(self.password)

class DropsPublic(SQLModel):
    """Drop 목록 컨테이너"""
    items: List[DropListElement]
    total: int
    page: int
    page_size: int
    total_pages: int
```

## 모델의 주요 특징

### 1. UUID 기반 식별자

모든 주요 엔티티는 UUID를 기본 키로 사용하여 보안과 예측 불가능성을 높입니다:

```python
id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
```

### 2. 관계 정의

SQLModel을 사용한 명확한 관계 정의:

```python
# Drop 모델에서 File과의 1:1 관계
file: "File" = Relationship(back_populates="drop", sa_relationship_kwargs={"uselist": False})

# File 모델에서 Drop과의 1:1 관계
drop: "Drop" = Relationship(back_populates="file")
```

### 3. 계산된 필드 (Computed Fields)

Pydantic의 `@computed_field` 데코레이터를 활용하여 동적 속성을 정의합니다:

```python
@computed_field
@property
def required_password(self) -> bool:
    """패스워드 필요 여부 (프론트엔드 표시용)"""
    return bool(self.password)
```

### 4. 필드 제외 (Field Exclusion)

민감한 정보는 API 응답에서 제외합니다:

```python
password: str | None = Field(exclude=True)
```

### 5. 클래스 메서드 기반 쿼리

모델 클래스에 정의된 쿼리 메서드로 코드 중복을 방지합니다:

```python
@classmethod
def get_by_key(cls, session: Session, key: str, include_file: bool = True) -> Optional["Drop"]:
    """키로 Drop 조회"""
    statement = select(cls).where(cls.key == key)
    if include_file:
        statement = statement.options(selectinload(cls.file))
    
    result = session.exec(statement)
    return result.first()
```

### 6. 최적화된 관계 로딩

`selectinload`를 사용하여 N+1 쿼리 문제를 방지합니다:

```python
statement = select(cls).where(cls.key == key).options(selectinload(cls.file))
```

### 7. 목록 모델 최적화

목록 조회 시 필요한 데이터만 포함하는 경량화된 모델을 사용합니다:

```python
class DropListElement(SQLModel):
    """목록용 간소화된 정보 - 성능 최적화"""
    id: uuid.UUID
    key: str
    title: str | None
    # ... 최소한의 필요 필드만 포함
```

## API Key 모델 예시

API Key 모델은 특히 흥미로운 설계를 가지고 있습니다:

```python
class ApiKeyBase(SQLModel):
    """API Key 기본 모델"""
    name: str
    prefix: str = Field(index=True)  # 키 접두사 (검색용)
    key_hash: str  # 실제 키의 해시값 (보안용)
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # 권한 설정
    can_read: bool = True
    can_create: bool = False
    can_update: bool = False
    can_delete: bool = False

class ApiKey(ApiKeyBase, table=True):
    """API Key 데이터베이스 테이블"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    @classmethod
    def get_by_prefix(cls, session: Session, prefix: str) -> Optional["ApiKey"]:
        """접두사로 API Key 조회"""
        statement = select(cls).where(cls.prefix == prefix)
        result = session.exec(statement)
        return result.first()
    
    def has_permission(self, permission: str) -> bool:
        """권한 검사"""
        if permission == "read":
            return self.can_read
        elif permission == "create":
            return self.can_create
        elif permission == "update":
            return self.can_update
        elif permission == "delete":
            return self.can_delete
        return False

class ApiKeyCreate(SQLModel):
    """API Key 생성 요청"""
    name: str
    expires_at: Optional[datetime] = None
    can_read: bool = True
    can_create: bool = False
    can_update: bool = False
    can_delete: bool = False

class ApiKeyCreateResponse(SQLModel):
    """API Key 생성 응답 (원본 키 포함 - 한 번만 표시)"""
    id: uuid.UUID
    name: str
    key: str  # 원본 키 (클라이언트에 한 번만 표시)
    prefix: str
    expires_at: Optional[datetime] = None
    created_at: datetime
    can_read: bool
    can_create: bool
    can_update: bool
    can_delete: bool
```

## 모델 사용 패턴

### 1. 엔티티 생성

```python
# 새 Drop 생성
new_drop = Drop(
    key=generated_key,
    title=drop_data.title,
    description=drop_data.description,
    password=drop_data.password,
    user_only=drop_data.user_only,
    favorite=drop_data.favorite,
    created_at=self.get_current_timestamp()
)

# 세션에 추가 및 저장
session.add(new_drop)
session.commit()
session.refresh(new_drop)  # 관계 로드
```

### 2. 조회 및 필터링

```python
# 단일 엔티티 조회
drop = Drop.get_by_key(session, key, include_file=True)

# 목록 조회 및 필터링
drops = Drop.list_all(
    session, 
    skip=(page - 1) * page_size,
    limit=page_size,
    favorite_only=favorite_only
)
```

### 3. 관계 접근

```python
# 관계 데이터 접근
file = drop.file
file_path = file.storage_path
```

### 4. 응답 변환

SQLModel은 자동으로 DB 모델을 응답 모델로 변환합니다:

```python
# Drop 객체를 DropPublic 응답으로 자동 변환
@router.get("/drops/{key}", response_model=DropPublic)
async def get_drop(key: str, ...):
    drop = handler.execute(key, ...)
    return drop  # 자동으로 DropPublic으로 변환
```

## SQLModel의 장점

1. **타입 안전성**: 모든 필드에 타입 힌트 적용으로 개발 시점 오류 감지
2. **통합 모델링**: Pydantic(검증)과 SQLAlchemy(ORM) 기능을 단일 모델로 통합
3. **자동 검증**: 모든 입력 데이터에 대한 자동 검증 및 변환
4. **관계 지원**: SQLAlchemy의 강력한 관계 기능 활용 가능
5. **계산된 필드**: 응답에만 포함되는 동적 속성 정의 가능
6. **명시적 쿼리**: 클래스 메서드로 쿼리 로직 캡슐화

## 다음 문서

- [인프라스트럭처](infrastructure.md) - 데이터베이스 및 스토리지
- [보안 및 인증](security.md) - 인증 및 보안 메커니즘 