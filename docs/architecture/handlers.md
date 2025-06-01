# Handler 패턴

Handler 패턴은 **단일 책임 원칙**을 따르는 비즈니스 로직 처리 단위입니다. 각 Handler는 특정 유스케이스를 처리하며, Teledrop 백엔드의 핵심 아키텍처 패턴입니다.

## 핵심 개념

Handler 패턴의 주요 이점은 다음과 같습니다:

1. **API와 비즈니스 로직 분리**: HTTP 요청/응답 처리와 비즈니스 로직이 명확히 분리됩니다.
2. **단일 책임 원칙 준수**: 각 핸들러는 하나의 명확한 책임을 가집니다.
3. **의존성 주입 활용**: 모든 외부 의존성(DB, 스토리지, 설정)이 명시적으로 주입됩니다.
4. **테스트 용이성**: 작은 단위로 분리되어 단위 테스트가 용이합니다.
5. **코드 중복 방지**: 공통 기능은 믹스인으로 분리하여 재사용합니다.

## 구현 구조

Handler 디렉토리 구조는 도메인과 작업 유형에 따라 명확하게 구분됩니다:

```
app/handlers/
├── __init__.py           # 핸들러 모듈 통합 (94줄)
├── base.py               # 기본 핸들러 및 믹스인 정의 (369줄)
├── auth_handlers.py      # 인증 관련 핸들러 (451줄)
├── drop/                 # Drop 관련 핸들러 - CRUD 분리
│   ├── __init__.py       # Drop 핸들러 export
│   ├── create.py         # DropCreateHandler (244줄)
│   ├── read.py           # DropDetailHandler, DropListHandler (164줄) 
│   ├── update.py         # DropUpdateHandler (89줄)
│   ├── delete.py         # DropDeleteHandler (81줄)
│   └── access.py         # DropAccessHandler (165줄)
├── file/                 # File 관련 핸들러 - 핵심 기능만
│   ├── __init__.py       # File 핸들러 export
│   ├── download.py       # FileDownloadHandler
│   └── stream.py         # FileRangeHandler
└── api_key/              # API Key 관련 핸들러
    ├── __init__.py       # API Key 핸들러 export
    ├── create.py         # ApiKeyCreateHandler
    ├── read.py           # ApiKeyListHandler
    ├── update.py         # ApiKeyUpdateHandler
    ├── delete.py         # ApiKeyDeleteHandler
    └── validate.py       # ApiKeyValidateHandler
```

## 기본 구조: BaseHandler 및 믹스인

핵심은 `BaseHandler` 클래스와 기능별로 분리된 **믹스인** 클래스들입니다:

```python
@dataclass
class BaseHandler(LoggingMixin, ValidationMixin, TimestampMixin):
    """모든 Handler의 기본 베이스 클래스
    
    공통적으로 필요한 기능들을 제공합니다.
    추가적인 기능이 필요한 Handler는 다른 믹스인들을 상속받을 수 있습니다.
    """
    
    settings: Settings  # 설정 주입 필수
```

### 주요 믹스인

```python
# 다양한 믹스인들을 통한 기능 조합
class LoggingMixin:
    """로깅 기능을 제공하는 믹스인"""
    def log_info(self, message: str, **kwargs): ...
    def log_error(self, message: str, **kwargs): ...
    def log_warning(self, message: str, **kwargs): ...

class ValidationMixin:
    """검증 기능을 제공하는 믹스인"""
    def validate_drop_password(self, drop, password): ...
    def validate_file_size(self, file_size): ...
    def validate_file_extension(self, filename): ...
    def validate_api_key_format(self, api_key): ...

class HashingMixin:
    """해시 관련 기능을 제공하는 믹스인"""
    def calculate_file_hash(self, content: bytes) -> str: ...
    def generate_file_path(self, identifier: str, extension: Optional[str] = None) -> str: ...

class TimestampMixin:
    """타임스탬프 관련 기능을 제공하는 믹스인"""
    def get_current_timestamp(self) -> datetime: ...
    def update_timestamps(self, model, update_created: bool = False): ...

class TransactionMixin:
    """트랜잭션 관련 기능을 제공하는 믹스인"""
    session: Session  # 세션 주입 필요
    def execute_in_transaction(self, operation_func, *args, **kwargs): ...
    async def execute_in_transaction_async(self, operation_func, *args, **kwargs): ...
    def rollback_on_error(self, operation_func, error_message: str = "Operation failed", *args, **kwargs): ...
    async def rollback_on_error_async(self, operation_func, error_message: str = "Operation failed", *args, **kwargs): ...

class PaginationMixin:
    """페이지네이션 기능을 제공하는 믹스인"""
    def calculate_offset(self, page: int, page_size: int) -> int: ...
    def validate_pagination(self, page: int, page_size: Optional[int] = None) -> tuple[int, int]: ...

class FileMixin:
    """파일 관련 기능을 제공하는 믹스인"""
    def file_streamer(self, file_stream, chunk_size: Optional[int] = None): ...
    def parse_range_header(self, range_header: str, file_size: int) -> tuple[int, int]: ...
```

## 비동기 처리 지원

핸들러는 동기 및 비동기 작업을 모두 지원합니다:

```python
@dataclass
class DropCreateHandler(BaseHandler, HashingMixin, TransactionMixin):
    """Drop 생성 Handler - 파일과 함께 생성"""
    
    session: Session
    storage_service: StorageInterface
    settings: Settings
    
    async def execute(
        self,
        drop_data: DropCreate,
        upload_file: UploadFile,
        auth_data: Optional[Dict[str, Any]] = None
    ) -> Drop:
        """
        새로운 Drop을 파일과 함께 생성합니다.
        
        Args:
            drop_data: Drop 생성 데이터
            upload_file: 업로드할 파일 (필수)
            auth_data: 인증 정보
            
        Returns:
            Drop: 생성된 Drop (파일 포함)
        """
        self.log_info("Creating new drop with file", title=drop_data.title)
        
        # 사전 검증 (트랜잭션 외부에서 수행)
        self._validate_drop_creation(drop_data, upload_file)
        
        # 트랜잭션 내에서 Drop과 파일 생성
        return await self.execute_in_transaction_async(
            self._create_drop_with_file_transaction,
            drop_data,
            upload_file,
            auth_data=auth_data
        )
```

## 트랜잭션 및 보상 트랜잭션 패턴

데이터베이스와 파일 시스템 간의 일관성을 보장하기 위해 **보상 트랜잭션 패턴**을 구현합니다:

```python
async def _create_drop_with_file_transaction(
    self, 
    drop_data: DropCreate, 
    upload_file: UploadFile, 
    auth_data: Optional[Dict[str, Any]] = None
) -> Drop:
    """트랜잭션 내에서 실행되는 Drop과 파일 생성 로직"""
    
    saved_file_path = None  # 롤백 시 삭제할 파일 경로 추적
    
    try:
        # 1. 고유한 키 생성 (중복 체크)
        key = self._generate_unique_drop_key()
        
        # 2. Drop 생성
        drop = self._create_drop_record(drop_data, key)
        
        # 3. 파일 처리 및 저장
        file_obj, saved_file_path = await self._process_and_save_file_with_path(upload_file, drop.id)
        
        # 4. 최종 커밋은 TransactionMixin에서 자동 처리
        self.session.refresh(drop)  # 관계 데이터 로드
        
        self.log_info("Drop with file created successfully", drop_id=str(drop.id), key=drop.key)
        return drop
        
    except Exception as e:
        # 트랜잭션 롤백 시 스토리지에서도 파일 삭제 (보상 트랜잭션)
        if saved_file_path:
            try:
                await self.storage_service.delete_file(saved_file_path)
                self.log_info("Compensating transaction: deleted file from storage", path=saved_file_path)
            except Exception as cleanup_error:
                self.log_error("Failed to cleanup file during rollback", 
                             path=saved_file_path, error=str(cleanup_error))
        
        # 원래 예외를 다시 발생시켜 TransactionMixin이 DB 롤백 처리
        raise
```

## 파일 스트리밍 처리

대용량 파일 처리를 위한 스트리밍 기능을 구현합니다:

```python
async def _process_and_save_file_with_path(self, upload_file: UploadFile, drop_id: int) -> Tuple[File, str]:
    """파일 처리, 저장 및 File 레코드 생성 (저장 경로 반환 포함)"""
    # 임시 식별자 생성
    temp_file_identifier = f"temp_{str(uuid.uuid4())}"
    temp_storage_path = self.generate_file_path(temp_file_identifier)
    
    # 스트리밍 저장 인터페이스 획득
    write_chunk, finalize = await self.storage_service.save_file_streaming(temp_storage_path)
    
    file_hash_obj = hashlib.sha256()
    actual_file_size = 0
    
    try:
        # 청크 단위로 파일 스트리밍 처리
        while chunk := await upload_file.read(1024 * 1024):  # 1MB 청크
            actual_file_size += len(chunk)
            
            # 파일 크기 제한 검사
            if actual_file_size > self.settings.MAX_FILE_SIZE:
                raise ValidationError(f"File size exceeds maximum")
            
            # 해시 계산 및 청크 저장
            file_hash_obj.update(chunk)
            await write_chunk(chunk)
        
        # 스트리밍 저장 완료
        await finalize()
        
        # 파일 메타데이터 생성 및 DB 저장
        calculated_file_hash = file_hash_obj.hexdigest()
        # ... 나머지 코드 (파일 메타데이터 생성 및 DB 저장) ...
    
    except Exception as e:
        # 오류 발생 시 임시 파일 정리
        try:
            await self.storage_service.delete_file(temp_storage_path)
        except Exception:
            pass
        raise
```

## 접근 권한 검증 통합

Drop 접근 권한 검증은 `DropAccessHandler`로 통합되어 모든 접근 권한 검증을 한 곳에서 처리합니다:

```python
@dataclass
class DropAccessHandler(BaseHandler, ValidationMixin):
    """Drop 접근 권한 검증 Handler"""
    
    session: Session
    storage_service: StorageInterface
    settings: Settings
    
    def execute(
        self,
        drop_key: str,
        password: Optional[str] = None,
        auth_data: Optional[Dict[str, Any]] = None,
        require_auth: bool = False
    ) -> Drop:
        """
        Drop 접근 권한을 검증합니다.
        
        Args:
            drop_key: Drop 키
            password: Drop 패스워드 (있는 경우)
            auth_data: 인증 정보
            require_auth: 인증 필수 여부
            
        Returns:
            Drop: 검증된 Drop 객체
            
        Raises:
            DropNotFoundError: Drop을 찾을 수 없는 경우
            DropPasswordInvalidError: 패스워드가 유효하지 않은 경우
            DropAccessDeniedError: 접근 권한이 없는 경우
        """
        # 1. Drop 조회
        drop = Drop.get_by_key(self.session, drop_key)
        if not drop:
            self.log_warning("Drop not found", key=drop_key)
            raise DropNotFoundError(f"Drop with key '{drop_key}' not found")
        
        # 2. 인증 여부 확인 (필요한 경우)
        if require_auth and not auth_data and self.settings.REQUIRE_AUTH_FOR_SENSITIVE_OPS:
            self.log_warning("Authentication required", key=drop_key)
            raise AuthenticationError("Authentication required for this operation")
        
        # 3. User-only Drop 접근 권한 확인
        if drop.user_only and not auth_data and self.settings.REQUIRE_AUTH_FOR_SENSITIVE_OPS:
            self.log_warning("Access denied to user-only drop", key=drop_key)
            raise DropAccessDeniedError("This drop requires authentication")
        
        # 4. 패스워드 검증
        if self.settings.ENABLE_PASSWORD_PROTECTION and drop.password:
            if drop.password != password:
                self.log_warning("Invalid password for drop", key=drop_key)
                raise DropPasswordInvalidError("Invalid password for drop")
        
        self.log_info("Drop access validated successfully", key=drop_key)
        return drop
```

## 핸들러 사용 패턴

핸들러는 라우터에서 다음과 같이 사용됩니다:

```python
@router.post("/drops", response_model=DropPublic)
async def create_drop(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    user_only: bool = Form(True),
    favorite: bool = Form(False),
    handler: DropCreateHandler = Depends(get_drop_create_handler()),
    auth_data: Dict[str, Any] = Depends(get_current_user)
):
    """새 Drop 생성"""
    drop_data = DropCreate(
        title=title,
        description=description,
        password=password,
        user_only=user_only,
        favorite=favorite
    )
    
    try:
        result = await handler.execute(drop_data, file, auth_data=auth_data)
        return result
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 핸들러 구조의 주요 개선사항

1. **파일 크기 제한**: `MAX_FILE_SIZE` 설정으로 업로드 파일 크기 제한
2. **스트리밍 처리**: 메모리 효율적인 청크 단위 파일 업로드/다운로드
3. **Range 요청 지원**: HTTP Range 헤더를 활용한 부분 다운로드 기능
4. **트랜잭션 안전성**: DB와 파일 시스템 간 일관성 보장
5. **보안 강화**: 파일 해시, 확장자 검증, 권한 검증 등 다양한 보안 기능
6. **비동기 처리**: `async/await` 패턴을 활용한 효율적인 I/O 처리
7. **로깅 강화**: 구조화된 로깅으로 문제 추적 용이성 개선

## 다음 문서

- [프론트엔드 아키텍처 지원](frontend.md) - SPA 및 SSR 지원
- [의존성 주입 시스템](dependency_injection.md) - 의존성 주입 패턴 