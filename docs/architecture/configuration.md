# 설정 관리

Teledrop은 다양한 환경에서 유연하게 구성할 수 있도록 강력한 설정 관리 시스템을 제공합니다. 이 문서에서는 설정 관리 방식, 환경 변수 통합, 설정 검증 등을 설명합니다.

## 설정 아키텍처

Teledrop은 Pydantic의 `BaseSettings` 클래스를 활용하여 타입 안전한 설정 관리를 구현합니다:

```
app/core/config.py
```

## 핵심 설정 클래스

```python
# app/core/config.py
from functools import lru_cache
from typing import List, Optional
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    """애플리케이션 설정
    
    환경 변수 또는 .env 파일에서 설정을 로드합니다.
    모든 설정은 타입 검증을 거치며, 기본값이 제공됩니다.
    """
    
    # 기본 설정
    APP_NAME: str = "Teledrop"
    DEBUG: bool = False
    VERSION: str = "0.1.0"
    
    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 데이터베이스
    DATABASE_URL: str = "sqlite:///./teledrop.db"
    
    # 스토리지
    STORAGE_TYPE: str = "local"  # 'local' 또는 's3'
    SHARE_DIRECTORY: str = "./shared"
    
    # S3 설정 (STORAGE_TYPE이 's3'일 때 사용)
    S3_BUCKET_NAME: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION_NAME: str = "us-east-1"
    
    # 보안
    SECRET_KEY: str
    API_KEY_LENGTH: int = 32
    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: List[str] = ["*"]
    
    # JWT 설정
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 파일 업로드
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: List[str] = ["*"]  # 모든 확장자 허용
    
    # 기능 플래그
    ENABLE_PASSWORD_PROTECTION: bool = True
    REQUIRE_AUTH_FOR_SENSITIVE_OPS: bool = True
    
    # 로깅
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # 검증 메서드들
    @validator("STORAGE_TYPE")
    def validate_storage_type(cls, v):
        """스토리지 타입 검증"""
        if v not in ["local", "s3"]:
            raise ValueError("STORAGE_TYPE must be 'local' or 's3'")
        return v
    
    @validator("S3_BUCKET_NAME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
    def validate_s3_settings(cls, v, values):
        """S3 설정 검증"""
        if values.get("STORAGE_TYPE") == "s3" and not v:
            raise ValueError("S3 credentials must be provided when STORAGE_TYPE is 's3'")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """로그 레벨 검증"""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in allowed_levels:
            raise ValueError(f"LOG_LEVEL must be one of {allowed_levels}")
        return v
    
    @validator("LOG_FORMAT")
    def validate_log_format(cls, v):
        """로그 포맷 검증"""
        allowed_formats = ["json", "text"]
        if v not in allowed_formats:
            raise ValueError(f"LOG_FORMAT must be one of {allowed_formats}")
        return v
    
    @validator("SECRET_KEY", pre=True)
    def validate_secret_key(cls, v):
        """비밀 키 검증"""
        if not v:
            raise ValueError("SECRET_KEY is required")
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    class Config:
        """Pydantic 설정 클래스 구성"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True  # 환경 변수 이름은 대소문자를 구분합니다
```

## 설정 인스턴스 관리

애플리케이션 전체에서 일관된 설정 인스턴스를 사용하기 위해 캐싱된 설정 함수를 제공합니다:

```python
@lru_cache()
def get_settings() -> Settings:
    """캐싱된 설정 인스턴스 반환
    
    애플리케이션 전체에서 일관된 설정 객체를 사용하기 위해
    functools.lru_cache를 사용하여 설정 인스턴스를 캐싱합니다.
    
    Returns:
        Settings: 설정 인스턴스
    """
    return Settings()
```

## 설정 관리의 장점

1. **타입 안전성**: 모든 설정 값이 타입 힌트를 통해 검증됩니다.
2. **환경 변수 통합**: 환경 변수와 `.env` 파일에서 설정을 로드합니다.
3. **검증 규칙**: 복잡한 검증 규칙을 적용하여 설정 오류를 방지합니다.
4. **기본값 제공**: 대부분의 설정에 합리적인 기본값을 제공합니다.
5. **의존성 주입**: FastAPI의 의존성 주입 시스템과 통합됩니다.
6. **캐싱**: 불필요한 설정 재생성을 방지하여 성능을 향상시킵니다.

## 설정 의존성 주입

설정은 FastAPI의 의존성 주입 시스템을 통해 쉽게 접근할 수 있습니다:

```python
# app/dependencies/base.py
from fastapi import Depends
from app.core.config import Settings, get_settings

def get_app_settings() -> Settings:
    """애플리케이션 설정 의존성"""
    return get_settings()

# 라우터 또는 핸들러에서의 사용
@router.get("/api/info")
async def get_api_info(settings: Settings = Depends(get_app_settings)):
    """API 정보 반환"""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.VERSION
    }
```

## 환경별 설정

Teledrop은 다양한 환경(개발, 테스트, 프로덕션)에서 다른 설정을 사용할 수 있습니다:

```bash
# 개발 환경 (.env.dev)
DEBUG=true
DATABASE_URL=sqlite:///./teledrop_dev.db
LOG_LEVEL=DEBUG

# 테스트 환경 (.env.test)
DEBUG=false
DATABASE_URL=sqlite:///./teledrop_test.db
LOG_LEVEL=INFO

# 프로덕션 환경 (.env.prod)
DEBUG=false
DATABASE_URL=sqlite:///./teledrop_prod.db
ALLOWED_HOSTS=example.com,www.example.com
CORS_ORIGINS=https://example.com
LOG_LEVEL=WARNING
```

환경별 설정 파일을 로드하기 위해 환경 변수 선택 로직을 추가할 수 있습니다:

```python
# app/core/config.py
import os
from functools import lru_cache

@lru_cache()
def get_settings() -> Settings:
    """환경에 따른 설정 로드"""
    env = os.getenv("ENVIRONMENT", "dev").lower()
    env_file = f".env.{env}"
    
    # 환경별 설정 파일이 존재하는지 확인
    if os.path.isfile(env_file):
        return Settings(_env_file=env_file)
    else:
        # 기본 .env 파일 사용
        return Settings()
```

## Docker 환경 설정

Docker 컨테이너에서 실행할 때는 환경 변수를 통해 설정을 주입합니다:

```yaml
# docker-compose.yml
version: '3'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=prod
      - SECRET_KEY=your-secure-secret-key-here
      - DATABASE_URL=sqlite:///./data/teledrop.db
      - STORAGE_TYPE=local
      - SHARE_DIRECTORY=/app/data/shared
      - ALLOWED_HOSTS=example.com,localhost
      - CORS_ORIGINS=https://example.com
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
```

## 민감한 설정 관리

민감한 설정(비밀 키, API 키 등)은 `.env` 파일이 아닌 환경 변수를 통해 주입하는 것이 좋습니다:

```bash
# 로컬 개발 환경에서 설정 (Linux/macOS)
export SECRET_KEY="your-secure-secret-key-here"
export AWS_ACCESS_KEY_ID="your-aws-access-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret-key"

# Windows 환경에서 설정
set SECRET_KEY=your-secure-secret-key-here
set AWS_ACCESS_KEY_ID=your-aws-access-key
set AWS_SECRET_ACCESS_KEY=your-aws-secret-key
```

## 설정 접근 패턴

### 핸들러에서 설정 접근

모든 핸들러는 `settings` 매개변수를 통해 설정에 접근할 수 있습니다:

```python
@dataclass
class DropCreateHandler(BaseHandler):
    """Drop 생성 핸들러"""
    
    session: Session
    storage_service: StorageInterface
    settings: Settings
    
    def execute(self, data: DropCreate):
        # 설정 접근
        max_file_size = self.settings.MAX_FILE_SIZE
        
        # 파일 크기 검증
        if data.file_size > max_file_size:
            raise ValidationError(f"File size exceeds maximum allowed size of {max_file_size} bytes")
        
        # ... 나머지 로직 ...
```

### 라우터에서 설정 접근

라우터 함수에서도 의존성 주입을 통해 설정에 접근할 수 있습니다:

```python
@router.post("/drops", response_model=DropPublic)
async def create_drop(
    data: DropCreate,
    handler: DropCreateHandler = Depends(get_drop_create_handler()),
    settings: Settings = Depends(get_app_settings)
):
    """Drop 생성"""
    # 설정 접근 (필요한 경우)
    if settings.DEBUG:
        print(f"Creating drop with data: {data}")
        
    # 핸들러 실행
    result = handler.execute(data)
    return result
```

## 설정 확장하기

새로운 설정 요구사항이 있을 때 설정 클래스를 확장하는 방법:

```python
# 기존 설정 클래스 확장
class Settings(BaseSettings):
    # ... 기존 설정 ...
    
    # 새로운 설정 추가
    ENABLE_ANALYTICS: bool = False
    ANALYTICS_PROVIDER: str = "none"
    ANALYTICS_API_KEY: Optional[str] = None
    
    @validator("ANALYTICS_PROVIDER")
    def validate_analytics_provider(cls, v, values):
        """분석 제공자 검증"""
        if values.get("ENABLE_ANALYTICS") and v == "none":
            raise ValueError("ANALYTICS_PROVIDER must be specified when ENABLE_ANALYTICS is True")
        
        allowed_providers = ["none", "google", "mixpanel", "custom"]
        if v not in allowed_providers:
            raise ValueError(f"ANALYTICS_PROVIDER must be one of {allowed_providers}")
        
        return v
```

## 설정 문서화

애플리케이션 실행 시 현재 설정을 출력하는 도우미 함수:

```python
def print_settings(settings: Settings, hide_secrets: bool = True):
    """현재 설정 출력 (비밀 값 숨김)"""
    settings_dict = settings.dict()
    
    # 민감한 설정 마스킹
    if hide_secrets:
        secret_fields = ["SECRET_KEY", "AWS_SECRET_ACCESS_KEY"]
        for field in secret_fields:
            if field in settings_dict and settings_dict[field]:
                settings_dict[field] = "***HIDDEN***"
    
    # 설정 출력
    print("Current application settings:")
    for key, value in settings_dict.items():
        print(f"  {key}: {value}")
```

## 설정 검증 오류 처리

Pydantic의 검증 오류를 처리하여 명확한 오류 메시지 제공:

```python
# app/main.py
from pydantic import ValidationError as PydanticValidationError

def create_app():
    """애플리케이션 생성"""
    try:
        settings = get_settings()
    except PydanticValidationError as e:
        print(f"설정 검증 오류가 발생했습니다:")
        for error in e.errors():
            field = error["loc"][0]
            message = error["msg"]
            print(f"  - {field}: {message}")
        sys.exit(1)
    
    # ... 나머지 앱 초기화 코드 ...
```

## 설정 문서 자동 생성

설정 스키마를 자동으로 문서화하는 도우미 함수:

```python
def generate_settings_docs():
    """설정 문서 자동 생성"""
    schema = Settings.schema()
    
    print("# 애플리케이션 설정 문서")
    print("\n## 설정 개요")
    print(schema.get("description", ""))
    
    print("\n## 설정 항목")
    for name, prop in schema["properties"].items():
        print(f"### {name}")
        print(prop.get("description", ""))
        print(f"- **타입**: {prop.get('type')}")
        if "default" in prop:
            print(f"- **기본값**: {prop['default']}")
        print()
```

## 주요 설정 그룹

Teledrop 설정은 다음과 같은 주요 그룹으로 분류됩니다:

1. **애플리케이션 기본 설정**: `APP_NAME`, `DEBUG`, `VERSION`
2. **서버 설정**: `HOST`, `PORT`
3. **데이터베이스 설정**: `DATABASE_URL`
4. **스토리지 설정**: `STORAGE_TYPE`, `SHARE_DIRECTORY`, S3 관련 설정
5. **보안 설정**: `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ORIGINS`
6. **파일 업로드 설정**: `MAX_FILE_SIZE`, `ALLOWED_EXTENSIONS`
7. **기능 플래그**: `ENABLE_PASSWORD_PROTECTION`, `REQUIRE_AUTH_FOR_SENSITIVE_OPS`
8. **로깅 설정**: `LOG_LEVEL`, `LOG_FORMAT`

## 다음 문서

- [확장성 고려사항](extensibility.md) - 시스템 확장 가이드라인 