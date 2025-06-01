# 인프라스트럭처

Teledrop의 인프라스트럭처 레이어는 데이터베이스, 파일 스토리지, 설정 관리 등 외부 시스템과의 연동을 담당합니다. 이 레이어는 추상화를 통해 상위 레이어가 구체적인 구현에 의존하지 않도록 합니다.

## 구조

```
app/infrastructure/
├── database/            # 데이터베이스 연결 및 설정
│   ├── connection.py    # SQLModel 연결 관리
│   └── __init__.py      # DB 초기화
└── storage/             # 파일 저장소 추상화
    ├── base.py          # 스토리지 인터페이스
    ├── local.py         # 로컬 파일 시스템
    ├── s3.py            # AWS S3 구현 (옵션)
    └── factory.py       # 스토리지 팩토리
```

## 데이터베이스 연결 관리

Teledrop은 SQLModel을 통해 데이터베이스와 연동합니다. 연결 관리는 `app/infrastructure/database/connection.py`에서 처리합니다:

```python
# app/infrastructure/database/connection.py
from contextlib import contextmanager
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine

def get_engine(database_url: str):
    """SQLModel 엔진 생성"""
    return create_engine(
        database_url, 
        echo=False,  # 로깅 비활성화
        connect_args={"check_same_thread": False}  # SQLite 멀티스레드 지원
    )

def get_session(engine=None) -> Generator[Session, None, None]:
    """데이터베이스 세션 생성 및 관리
    
    컨텍스트 관리자 패턴을 사용하여 세션의 라이프사이클을 관리합니다.
    예외 발생 시 자동으로 롤백하고 항상 세션을 닫습니다.
    
    Yields:
        Session: SQLModel 세션 객체
    """
    if engine is None:
        from app.core.config import get_settings
        settings = get_settings()
        engine = get_engine(settings.DATABASE_URL)
    
    session = Session(engine)
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def init_db(settings):
    """데이터베이스 초기화 (테이블 생성 및 초기 데이터)"""
    engine = get_engine(settings.DATABASE_URL)
    
    # 모든 모델 임포트 (SQLModel.metadata에 등록)
    from app.models import Drop, File, ApiKey
    
    # 테이블 생성
    SQLModel.metadata.create_all(engine)
```

### 특징

1. **세션 라이프사이클 관리**: 컨텍스트 관리자 패턴으로 세션 생명주기 관리
2. **자동 롤백**: 예외 발생 시 자동으로 트랜잭션 롤백
3. **의존성 주입 지원**: FastAPI의 의존성 주입 시스템과 통합
4. **멀티스레드 지원**: SQLite를 멀티스레드 환경에서 사용 가능하도록 설정

## 스토리지 추상화

파일 스토리지는 다양한 백엔드(로컬 파일시스템, 클라우드 등)를 지원하기 위해 추상화되어 있습니다. 핵심은 `StorageInterface` 추상 클래스입니다:

```python
# app/infrastructure/storage/base.py
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Awaitable, Callable, Dict, Any, Tuple, Optional

class StorageInterface(ABC):
    """파일 스토리지 추상 인터페이스
    
    다양한 스토리지 백엔드를 지원하기 위한 인터페이스입니다.
    모든 스토리지 구현체는 이 인터페이스를 구현해야 합니다.
    """
    
    storage_type: str  # 스토리지 유형 식별자
    
    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """파일 존재 여부 확인"""
        pass
    
    @abstractmethod
    async def save_file(self, file_content: bytes, file_path: str) -> str:
        """파일 저장 (전체 내용)"""
        pass
    
    @abstractmethod
    async def save_file_streaming(self, file_path: str) -> Tuple[Callable[[bytes], Awaitable[None]], Callable[[], Awaitable[None]]]:
        """
        스트리밍 방식 파일 저장 인터페이스
        
        Returns:
            Tuple[write_chunk, finalize]: 청크 쓰기 함수와 저장 완료 함수
        """
        pass
    
    @abstractmethod
    async def read_file(self, file_path: str) -> bytes:
        """파일 읽기 (전체 내용)"""
        pass
    
    @abstractmethod
    async def read_file_streaming(self, file_path: str, chunk_size: int = 1024 * 1024) -> AsyncGenerator[bytes, None]:
        """
        스트리밍 방식 파일 읽기
        
        Args:
            file_path: 파일 경로
            chunk_size: 청크 크기 (기본 1MB)
            
        Yields:
            bytes: 파일 청크
        """
        pass
    
    @abstractmethod
    async def read_file_range(self, file_path: str, start: int, end: int) -> bytes:
        """
        파일 범위 읽기
        
        Args:
            file_path: 파일 경로
            start: 시작 바이트 위치 (포함)
            end: 끝 바이트 위치 (포함)
            
        Returns:
            bytes: 지정된 범위의 파일 데이터
        """
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """파일 삭제"""
        pass
    
    @abstractmethod
    async def move_file(self, source_path: str, destination_path: str) -> str:
        """
        파일 이동
        
        Args:
            source_path: 원본 경로
            destination_path: 대상 경로
            
        Returns:
            str: 새 파일 경로
        """
        pass
    
    @abstractmethod
    async def get_file_size(self, file_path: str) -> int:
        """파일 크기 조회"""
        pass
    
    @abstractmethod
    async def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """파일 메타데이터 조회"""
        pass
```

### 로컬 파일시스템 구현

```python
# app/infrastructure/storage/local.py
import os
import shutil
from pathlib import Path
from typing import AsyncGenerator, Awaitable, Callable, Dict, Any, Tuple, Optional

import aiofiles
from aiofiles.os import stat as aio_stat

from .base import StorageInterface

class LocalStorageService(StorageInterface):
    """로컬 파일시스템 스토리지 구현"""
    
    storage_type = "local"
    
    def __init__(self, base_path: str):
        """
        Args:
            base_path: 파일 저장 기본 경로
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_absolute_path(self, file_path: str) -> Path:
        """상대 경로를 절대 경로로 변환"""
        return self.base_path / file_path
    
    async def file_exists(self, file_path: str) -> bool:
        """파일 존재 여부 확인"""
        absolute_path = self._get_absolute_path(file_path)
        return absolute_path.exists()
    
    async def save_file(self, file_content: bytes, file_path: str) -> str:
        """파일 저장 (전체 내용)"""
        absolute_path = self._get_absolute_path(file_path)
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(absolute_path, "wb") as file:
            await file.write(file_content)
        
        return file_path
    
    async def save_file_streaming(self, file_path: str) -> Tuple[Callable[[bytes], Awaitable[None]], Callable[[], Awaitable[None]]]:
        """스트리밍 방식 파일 저장 인터페이스 구현
        
        파일 청크를 비동기적으로 저장하기 위한 함수들을 반환합니다.
        
        Returns:
            write_chunk: 청크 저장 함수
            finalize: 저장 완료 함수
        """
        absolute_path = self._get_absolute_path(file_path)
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 임시 파일 경로 생성 (원자적 작업 보장)
        temp_path = absolute_path.with_suffix(f"{absolute_path.suffix}.tmp")
        
        # 비동기 파일 핸들 생성
        file_handle = await aiofiles.open(temp_path, "wb")
        
        # 청크 쓰기 함수
        async def write_chunk(chunk: bytes) -> None:
            await file_handle.write(chunk)
        
        # 저장 완료 함수
        async def finalize() -> None:
            await file_handle.flush()
            await file_handle.close()
            
            # 임시 파일을 최종 파일로 원자적으로 이동 (파일 시스템 일관성 보장)
            try:
                temp_path.rename(absolute_path)
            except Exception as e:
                # 이미 이동된 경우 무시
                if not absolute_path.exists():
                    raise e
        
        return write_chunk, finalize
    
    async def read_file_streaming(self, file_path: str, chunk_size: int = 1024 * 1024) -> AsyncGenerator[bytes, None]:
        """스트리밍 방식 파일 읽기 구현
        
        Args:
            file_path: 파일 경로
            chunk_size: 청크 크기 (기본 1MB)
            
        Yields:
            bytes: 파일 청크
        """
        absolute_path = self._get_absolute_path(file_path)
        
        if not absolute_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        async with aiofiles.open(absolute_path, "rb") as file:
            while chunk := await file.read(chunk_size):
                yield chunk
```

### 스토리지 팩토리

스토리지 유형에 따라 적절한 스토리지 서비스를 생성합니다:

```python
# app/infrastructure/storage/factory.py
from typing import Any, Dict

from app.core.config import Settings
from .base import StorageInterface
from .local import LocalStorageService

# S3 지원 시 추가
# from .s3 import S3StorageService

def get_storage_service(settings: Settings) -> StorageInterface:
    """스토리지 서비스 팩토리
    
    설정에 따라 적절한 스토리지 서비스를 생성합니다.
    
    Args:
        settings: 애플리케이션 설정
        
    Returns:
        StorageInterface: 스토리지 서비스 인스턴스
    """
    storage_type = settings.STORAGE_TYPE.lower()
    
    if storage_type == "local":
        return LocalStorageService(base_path=settings.SHARE_DIRECTORY)
    elif storage_type == "s3":
        # S3 스토리지 서비스 구현 시 활성화
        # return S3StorageService(
        #     bucket_name=settings.S3_BUCKET_NAME,
        #     aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        #     aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        #     region_name=settings.AWS_REGION_NAME
        # )
        raise NotImplementedError("S3 storage is not implemented yet")
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")
```

## 스토리지 추상화의 이점

1. **백엔드 교체 용이성**: 로컬 파일시스템에서 클라우드 스토리지로 쉽게 전환 가능
2. **단위 테스트 용이성**: 테스트 시 가짜(Mock) 스토리지로 대체 가능
3. **비즈니스 로직 분리**: 스토리지 처리 로직과 비즈니스 로직을 명확히 분리
4. **일관된 인터페이스**: 모든 스토리지 구현체가 동일한 인터페이스 제공
5. **비동기 지원**: 모든 스토리지 메서드가 비동기(async/await) 패턴 지원
6. **스트리밍 지원**: 대용량 파일의 메모리 효율적인 처리를 위한 스트리밍 인터페이스 제공

## 비동기 처리 아키텍처

Teledrop은 파일 업로드/다운로드와 같은 I/O 작업에서 `async/await` 패턴을 활용합니다:

1. **스트리밍 인터페이스**:
   - `save_file_streaming`: 대용량 파일 업로드
   - `read_file_streaming`: 대용량 파일 다운로드
   - `read_file_range`: HTTP Range 요청 지원

2. **성능 최적화**:
   - 청크 단위 처리로 메모리 사용량 최소화
   - 비동기 I/O로 다중 요청 효율적 처리
   - Range 요청 지원으로 대용량 파일 스트리밍 최적화

3. **파일 안전성**:
   - 임시 파일을 사용한 원자적 파일 작업
   - 예외 발생 시 적절한 리소스 정리
   - 트랜잭션 실패 시 보상 트랜잭션 수행

## 설정 관리

Teledrop은 Pydantic의 BaseSettings를 활용하여 설정을 관리합니다:

```python
# app/core/config.py
from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    APP_NAME: str = "Teledrop"
    DEBUG: bool = False
    
    # 데이터베이스
    DATABASE_URL: str = "sqlite:///./teledrop.db"
    
    # 스토리지
    STORAGE_TYPE: str = "local"
    SHARE_DIRECTORY: str = "./shared"
    
    # 보안
    SECRET_KEY: str
    API_KEY_LENGTH: int = 32
    ALLOWED_HOSTS: list[str] = ["*"]
    CORS_ORIGINS: list[str] = ["*"]
    
    # 파일 업로드
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # 기능 플래그
    ENABLE_PASSWORD_PROTECTION: bool = True
    REQUIRE_AUTH_FOR_SENSITIVE_OPS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """캐시된 설정 인스턴스 반환"""
    return Settings()
```

### 설정 관리의 특징

1. **환경 변수 지원**: 환경 변수를 통한 설정 재정의
2. **`.env` 파일 지원**: 개발 환경에서의 간편한 설정
3. **타입 검증**: 설정 값의 타입 검증 및 변환
4. **기본값 제공**: 필수가 아닌 설정에 대한 기본값 제공
5. **캐싱**: `lru_cache`를 통한 설정 객체 캐싱
6. **명시적 문서화**: 각 설정 항목의 목적과 타입을 명확히 문서화

## 인프라스트럭처 초기화

Teledrop의 인프라스트럭처는 애플리케이션 시작 시 초기화됩니다:

```python
# app/main.py
from fastapi import FastAPI
from app.core.config import get_settings
from app.infrastructure.database import init_db

def create_app() -> FastAPI:
    """애플리케이션 팩토리"""
    settings = get_settings()
    
    # FastAPI 앱 생성
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG
    )
    
    # 데이터베이스 초기화
    init_db(settings)
    
    # 라우터 등록
    from app.routers import router as api_router
    app.include_router(api_router)
    
    return app

app = create_app()
```

## 다음 문서

- [보안 및 인증](security.md) - 인증 및 보안 메커니즘
- [에러 처리](error_handling.md) - 예외 처리 전략 