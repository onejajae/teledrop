# 보안 및 인증

Teledrop은 다양한 보안 메커니즘을 통해 데이터와 리소스를 보호합니다. 이 문서에서는 인증, 권한 부여, 데이터 보호에 대한 구현을 설명합니다.

## 인증 아키텍처

Teledrop은 두 가지 주요 인증 방식을 지원합니다:

1. **JWT 토큰 인증**: 웹 인터페이스 및 SPA 사용자를 위한 인증
2. **API 키 인증**: 프로그래밍 방식의 접근을 위한 인증

```
┌─────────────────────────────────────────────────────────┐
│                   인증 시스템                            │
│                                                         │
│  ┌────────────────┐            ┌────────────────┐       │
│  │  JWT 토큰 인증  │            │  API 키 인증   │       │
│  │                │            │                │       │
│  │ • 웹 인터페이스 │            │ • 프로그래밍   │       │
│  │ • SPA 사용자   │            │ • 자동화 도구  │       │
│  │ • 세션 기반    │            │ • 장기 접근    │       │
│  └────────────────┘            └────────────────┘       │
│          │                             │                │
│          ▼                             ▼                │
│  ┌────────────────┐            ┌────────────────┐       │
│  │ Authorization  │            │   X-API-Key    │       │
│  │     헤더       │            │      헤더      │       │
│  └────────────────┘            └────────────────┘       │
│          │                             │                │
│          └──────────────┬──────────────┘                │
│                         ▼                               │
│               ┌────────────────┐                        │
│               │ FastAPI 의존성 │                        │
│               │    주입 시스템  │                        │
│               └────────────────┘                        │
│                         │                               │
│                         ▼                               │
│               ┌────────────────┐                        │
│               │  auth_data 객체 │                        │
│               │  (표준화된 형식) │                        │
│               └────────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

## JWT 토큰 인증

### 토큰 생성 및 검증

```python
# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

# 패스워드 해싱에 사용할 컨텍스트
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None, data: Optional[Dict[str, Any]] = None) -> str:
    """JWT 액세스 토큰 생성
    
    Args:
        subject: 토큰 주체 (일반적으로 사용자 ID)
        expires_delta: 만료 시간 델타
        data: 토큰에 포함할 추가 데이터
        
    Returns:
        str: 인코딩된 JWT 토큰
    """
    settings = get_settings()
    
    # 기본 만료 시간
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    # 현재 시간 + 만료 시간 델타
    expire = datetime.utcnow() + expires_delta
    
    # 토큰 페이로드
    to_encode = {"exp": expire, "sub": str(subject)}
    
    # 추가 데이터가 있으면 페이로드에 추가
    if data:
        to_encode.update(data)
        
    # 토큰 인코딩
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def verify_token(token: str) -> Dict[str, Any]:
    """JWT 토큰 검증
    
    Args:
        token: 검증할 JWT 토큰
        
    Returns:
        Dict[str, Any]: 디코딩된 페이로드
        
    Raises:
        JWTError: 토큰이 유효하지 않은 경우
    """
    settings = get_settings()
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
```

### 의존성 주입을 통한 인증

```python
# app/dependencies/auth.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlmodel import Session
from typing import Optional, Dict, Any

from app.core.config import get_settings
from app.core.security import verify_token
from app.dependencies.base import get_db_session
from app.models.auth import TokenPayload

# OAuth2 스키마 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_current_user_optional(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings)
) -> Optional[Dict[str, Any]]:
    """선택적 사용자 인증 - 실패해도 None 반환 (API/웹 공통)"""
    if not token:
        # 쿠키에서 토큰 찾기 시도
        token = request.cookies.get("access_token")
        if not token:
            return None
    
    try:
        # 토큰 검증
        payload = verify_token(token)
        token_data = TokenPayload(**payload)
        
        # 토큰이 만료되었는지 확인
        if datetime.fromtimestamp(token_data.exp) < datetime.utcnow():
            return None
            
        # 인증 데이터 반환
        return {
            "user_id": token_data.sub,
            "is_admin": token_data.is_admin if hasattr(token_data, "is_admin") else False,
            "token_data": token_data
        }
    except (JWTError, ValidationError):
        return None

def get_current_user(
    auth_data: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """필수 사용자 인증 - 실패 시 401 에러"""
    if not auth_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return auth_data
```

## API 키 인증

### API 키 생성 및 검증

```python
# app/handlers/api_key/create.py
@dataclass
class ApiKeyCreateHandler(BaseHandler, HashingMixin, TimestampMixin):
    """API Key 생성 핸들러"""
    
    session: Session
    settings: Settings
    
    def execute(self, data: ApiKeyCreate, auth_data: Optional[Dict[str, Any]] = None) -> ApiKeyCreateResponse:
        """새 API 키 생성
        
        Args:
            data: API 키 생성 요청 데이터
            auth_data: 인증 정보
            
        Returns:
            ApiKeyCreateResponse: 생성된 API 키 정보 (해시 전 원본 키 포함)
        """
        self.log_info("Creating new API key", name=data.name)
        
        # 1. 랜덤 API 키 생성 (원본)
        raw_key = self._generate_api_key()
        
        # 2. 키 접두사 (앞 8자리)
        prefix = raw_key[:8]
        
        # 3. 키 해시 계산
        key_hash = self.calculate_api_key_hash(raw_key)
        
        # 4. API 키 레코드 생성
        api_key = ApiKey(
            name=data.name,
            prefix=prefix,
            key_hash=key_hash,
            expires_at=data.expires_at,
            created_at=self.get_current_timestamp(),
            can_read=data.can_read,
            can_create=data.can_create,
            can_update=data.can_update,
            can_delete=data.can_delete
        )
        
        # 5. 데이터베이스에 저장
        self.session.add(api_key)
        self.session.commit()
        self.session.refresh(api_key)
        
        # 6. 응답 생성 (원본 키 포함 - 이것이 클라이언트에 표시되는 유일한 시점)
        return ApiKeyCreateResponse(
            id=api_key.id,
            name=api_key.name,
            key=raw_key,  # 원본 키 (저장되지 않음)
            prefix=api_key.prefix,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
            can_read=api_key.can_read,
            can_create=api_key.can_create,
            can_update=api_key.can_update,
            can_delete=api_key.can_delete
        )
        
    def _generate_api_key(self) -> str:
        """안전한 API 키 생성
        
        Format: tk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx (34자)
        """
        # 랜덤 바이트 생성
        random_bytes = secrets.token_bytes(self.settings.API_KEY_LENGTH // 2)
        
        # Base16 인코딩 (hex)
        hex_token = secrets.token_hex(self.settings.API_KEY_LENGTH // 2)
        
        # 접두사 추가
        return f"tk_{hex_token}"
```

### API 키 검증

```python
# app/handlers/api_key/validate.py
@dataclass
class ApiKeyValidateHandler(BaseHandler, HashingMixin):
    """API Key 유효성 검증 핸들러"""
    
    session: Session
    settings: Settings
    
    def execute(self, api_key: str) -> ApiKey:
        """API 키 유효성 검증
        
        Args:
            api_key: 검증할 API 키
            
        Returns:
            ApiKey: 검증된 API 키 객체
            
        Raises:
            ValidationError: API 키 형식이 잘못된 경우
            ApiKeyNotFoundError: API 키를 찾을 수 없는 경우
            ApiKeyExpiredError: API 키가 만료된 경우
        """
        self.log_info("Validating API key")
        
        # 1. API 키 형식 검증
        if not api_key.startswith("tk_") or len(api_key) != 34:
            self.log_warning("Invalid API key format")
            raise ValidationError("Invalid API key format")
        
        # 2. 키 접두사 추출
        prefix = api_key[:8]
        
        # 3. 데이터베이스에서 API 키 조회
        db_key = ApiKey.get_by_prefix(self.session, prefix)
        if not db_key:
            self.log_warning("API key not found", prefix=prefix)
            raise ApiKeyNotFoundError(f"API key with prefix '{prefix}' not found")
        
        # 4. 키 해시 검증
        key_hash = self.calculate_api_key_hash(api_key)
        if key_hash != db_key.key_hash:
            self.log_warning("API key hash mismatch", prefix=prefix)
            raise ApiKeyNotFoundError("Invalid API key")
        
        # 5. 만료 여부 확인
        if db_key.expires_at and db_key.expires_at < self.get_current_timestamp():
            self.log_warning("API key expired", prefix=prefix, expires_at=db_key.expires_at)
            raise ApiKeyExpiredError("API key has expired")
        
        self.log_info("API key validated successfully", prefix=prefix)
        return db_key
```

### API 키 의존성 주입

```python
# app/dependencies/auth.py
def get_api_key_user(
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings)
) -> Dict[str, Any]:
    """API Key 인증 - X-API-Key 헤더 사용"""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key가 필요합니다"
        )
    
    # API Key 검증 로직
    handler = ApiKeyValidateHandler(session=session, settings=settings)
    try:
        result = handler.execute(api_key)
        return {
            "user_id": "api",
            "is_api_key": True,
            "api_key_data": result
        }
    except ApiKeyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 API Key"
        )
    except ApiKeyExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="만료된 API Key"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"API Key 인증 실패: {str(e)}"
        )
```

## 비밀번호 보안

### Argon2 해싱

Teledrop은 강력한 비밀번호 보안을 위해 Argon2 알고리즘을 사용합니다:

```python
# app/core/security.py
from passlib.context import CryptContext

# Argon2 해싱 컨텍스트
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)
```

### Drop 패스워드 보호

Drop은 선택적으로 패스워드로 보호될 수 있습니다:

```python
# app/handlers/drop/access.py
@dataclass
class DropAccessHandler(BaseHandler, ValidationMixin):
    """Drop 접근 권한 검증 Handler"""
    
    session: Session
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
        """
        # ... 다른 검증 로직 ...
        
        # 패스워드 검증
        if self.settings.ENABLE_PASSWORD_PROTECTION and drop.password:
            if not password:
                self.log_warning("Password required but not provided", key=drop_key)
                raise DropPasswordRequiredError("Password is required for this drop")
            
            if not verify_password(password, drop.password):
                self.log_warning("Invalid password for drop", key=drop_key)
                raise DropPasswordInvalidError("Invalid password for drop")
        
        return drop
```

## 파일 해싱 및 무결성

파일 무결성을 보장하기 위해 SHA-256 해싱을 사용합니다:

```python
# app/handlers/base.py
class HashingMixin:
    """해시 관련 기능을 제공하는 믹스인"""
    
    def calculate_file_hash(self, content: bytes) -> str:
        """파일 해시 계산 (SHA-256)"""
        return hashlib.sha256(content).hexdigest()
    
    def calculate_api_key_hash(self, api_key: str) -> str:
        """API 키 해시 계산 (SHA-256)"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def generate_file_path(self, identifier: str, extension: Optional[str] = None) -> str:
        """고유한 파일 경로 생성"""
        hash_obj = hashlib.sha256(identifier.encode())
        path_hash = hash_obj.hexdigest()
        
        # 경로 구성: {첫 2자}/{다음 2자}/{나머지}.{확장자}
        if extension:
            return f"{path_hash[:2]}/{path_hash[2:4]}/{path_hash[4:]}.{extension}"
        return f"{path_hash[:2]}/{path_hash[2:4]}/{path_hash[4:]}"
```

## 보안 헤더

Teledrop은 보안 강화를 위해 다양한 HTTP 헤더를 사용합니다:

```python
# app/main.py
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    """애플리케이션 팩토리"""
    # ... 다른 초기화 코드 ...
    
    # CORS 미들웨어 추가
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 프로덕션 모드에서 신뢰할 수 있는 호스트 제한
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware, 
            allowed_hosts=settings.ALLOWED_HOSTS
        )
    
    # 보안 헤더 미들웨어
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        
        # 보안 헤더 추가
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        return response
```

## 권한 제어

API 키에 대한 세분화된 권한 제어:

```python
# app/handlers/api_key/validate.py
def check_permission(self, api_key: ApiKey, required_permission: str) -> bool:
    """API 키 권한 검사
    
    Args:
        api_key: API 키 객체
        required_permission: 필요한 권한 (read, create, update, delete)
        
    Returns:
        bool: 권한이 있으면 True, 없으면 False
    """
    if required_permission == "read":
        return api_key.can_read
    elif required_permission == "create":
        return api_key.can_create
    elif required_permission == "update":
        return api_key.can_update
    elif required_permission == "delete":
        return api_key.can_delete
    return False

# app/routers/api/drop_router.py
@router.post("/drops", response_model=DropPublic)
async def create_drop_api(
    data: DropCreateRequest,
    auth_data: Dict[str, Any] = Depends(get_api_key_user)
):
    """API Key로 Drop 생성"""
    # API Key 권한 검사
    if auth_data.get("is_api_key"):
        api_key = auth_data.get("api_key_data")
        if not api_key.can_create:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 API 키에는 생성 권한이 없습니다"
            )
    
    # 나머지 로직
    # ...
```

## 보안 측면의 핵심 기능

1. **인증 분리**: JWT 토큰과 API 키를 통한 다중 인증 방식 지원
2. **안전한 해싱**: Argon2 알고리즘을 사용한 패스워드 해싱
3. **토큰 관리**: 적절한 만료 시간과 검증 로직
4. **세분화된 권한**: API 키에 대한 CRUD 기반 권한 제어
5. **파일 무결성**: SHA-256 해시를 통한 파일 무결성 검증
6. **보안 헤더**: XSS, CSRF 등의 공격 방지를 위한 HTTP 헤더
7. **안전한 파일 경로**: 해시 기반 파일 경로로 경로 탐색 공격 방지
8. **CORS 보호**: 허용된 출처에서만 API 호출 허용

## 다음 문서

- [에러 처리](error_handling.md) - 예외 처리 전략
- [설정 관리](configuration.md) - 환경 설정 관리 