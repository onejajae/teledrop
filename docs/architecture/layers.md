# 레이어 구조

Teledrop은 **Clean Architecture**의 원칙에 따라 4개의 핵심 레이어로 구성됩니다. 각 레이어는 명확한 책임을 가지며, 의존성은 안쪽 레이어를 향하도록 설계되었습니다.

## 레이어 개요

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Infrastructure Layer                         │
└─────────────────────────────────────────────────────────────┘
```

## 1. Presentation Layer (`app/routers/`)

**책임**: HTTP 요청/응답 처리, 입력 검증, 라우팅

```
app/routers/
├── __init__.py          # 라우터 통합 및 등록
├── api/                 # API 엔드포인트 (SPA 지원)
│   ├── auth_router.py   # 인증 관련 API
│   ├── drop_router.py   # Drop 관리 API
│   └── api_key_router.py # API Key 관리
└── web/                 # 웹 인터페이스 라우팅 (SSR 향후 구현)
    ├── __init__.py      # 웹 라우터 통합
    ├── auth_router.py   # 인증 웹 페이지
    └── drop_router.py   # Drop 관리 웹 페이지
```

**특징**:
- FastAPI의 라우터 시스템 활용
- Pydantic 모델을 통한 입력/출력 검증
- HTTP 상태 코드 및 응답 형식 관리
- 의존성 주입을 통한 Handler 호출

**미들웨어**:
- CORS 처리 (`CORSMiddleware` - 개발 모드에서 활성화)
- 신뢰할 수 있는 호스트 제한 (`TrustedHostMiddleware` - 프로덕션 모드에서 활성화)

**참고사항**: 
- **인증(Auth)** 은 미들웨어가 아닌 **의존성 주입 시스템**(`app/dependencies/auth.py`)을 통해 구현됨
  - `get_current_user_optional` - 인증 선택적 처리
  - `get_current_user` - 필수 인증 처리
  - `get_api_key_user` - API Key 인증 처리
  
- **로깅(Logging)** 은 별도 미들웨어 없이 **핸들러의 LoggingMixin**을 통해 구현됨
  - 각 핸들러에서 `log_info()`, `log_error()`, `log_warning()` 메서드로 로깅
  - 설정에 따라 로깅 레벨 조정 가능

## 2. Application Layer (`app/handlers/`)

**책임**: 비즈니스 로직 구현, 유스케이스 조정

```
app/handlers/
├── base.py              # 기본 Handler 및 Mixin들
├── auth_handlers.py     # 인증 관련 비즈니스 로직 (3개)
├── drop/                # Drop 관련 핸들러 (CRUD + 접근제어)
│   ├── __init__.py     # 핸들러 export
│   ├── create.py       # DropCreateHandler (트랜잭션 패턴)
│   ├── read.py         # DropDetailHandler, DropListHandler
│   ├── update.py       # DropUpdateHandler
│   ├── delete.py       # DropDeleteHandler
│   └── access.py       # DropAccessHandler (권한 검증)
├── file/                # File 관련 핸들러 (핵심 기능만)
│   ├── __init__.py     # 핸들러 export
│   ├── download.py     # FileDownloadHandler
│   └── stream.py       # FileRangeHandler (Range 요청 지원)
└── api_key/             # API Key 관련 핸들러 (CRUD + 검증)
    ├── __init__.py     # 핸들러 export
    ├── create.py       # ApiKeyCreateHandler
    ├── read.py         # ApiKeyListHandler (페이지네이션)
    ├── update.py       # ApiKeyUpdateHandler
    ├── delete.py       # ApiKeyDeleteHandler
    └── validate.py     # ApiKeyValidateHandler
```

**Handler 종류 및 특징**:

#### Drop Handlers (6개)
- **DropCreateHandler**: Drop과 파일을 함께 생성 (트랜잭션 + 보상 트랜잭션)
- **DropDetailHandler**: 단일 Drop 조회 (권한 검증 포함)
- **DropListHandler**: Drop 목록 조회 (페이지네이션 + 필터링)
- **DropUpdateHandler**: Drop 메타데이터 수정
- **DropDeleteHandler**: Drop과 연관 파일 삭제
- **DropAccessHandler**: 통합 접근 권한 검증 (횡단 관심사)

#### File Handlers (2개 - 최적화됨)
- **FileDownloadHandler**: 파일 다운로드 (스트리밍 지원)
- **FileRangeHandler**: Range 요청 처리 (부분 다운로드)

*참고: 파일 업로드와 교체는 Drop 생성/수정 시 함께 처리되므로 별도 핸들러 불필요*

#### API Key Handlers (5개)
- **ApiKeyCreateHandler**: API Key 생성 (한 번만 표시)
- **ApiKeyListHandler**: API Key 목록 조회 (페이지네이션)
- **ApiKeyUpdateHandler**: API Key 정보 수정
- **ApiKeyDeleteHandler**: API Key 삭제
- **ApiKeyValidateHandler**: API Key 유효성 검증

#### Auth Handlers (3개)
- **LoginHandler**: 사용자 로그인 처리
- **TokenValidateHandler**: JWT 토큰 검증
- **TokenRefreshHandler**: 토큰 갱신

## 3. Domain Layer (`app/models/`, `app/core/exceptions.py`)

**책임**: 도메인 모델, 비즈니스 규칙, 예외 정의

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

**예외 계층 구조**:
```
app/core/exceptions.py   # 도메인 예외 정의
```

**믹스인 계층**:
```python
# app/handlers/base.py에 정의된 믹스인들
class LoggingMixin:
    """로깅 기능을 제공하는 믹스인"""

class ValidationMixin:
    """검증 기능을 제공하는 믹스인"""

class HashingMixin:
    """해시 관련 기능을 제공하는 믹스인"""

class TimestampMixin:
    """타임스탬프 관련 기능을 제공하는 믹스인"""

class TransactionMixin:
    """트랜잭션 관련 기능을 제공하는 믹스인"""

class PaginationMixin:
    """페이지네이션 기능을 제공하는 믹스인"""

class FileMixin:
    """파일 관련 기능을 제공하는 믹스인"""
```

## 4. Infrastructure Layer (`app/infrastructure/`)

**책임**: 외부 시스템과의 연동, 데이터 저장소, 설정

```
app/infrastructure/
├── database/            # 데이터베이스 연결 및 설정
│   ├── connection.py    # SQLModel 연결 관리
│   └── __init__.py      # DB 초기화
└── storage/             # 파일 저장소 추상화
    ├── base.py          # 스토리지 인터페이스
    ├── local.py         # 로컬 파일 시스템
    ├── s3.py            # AWS S3 구현
    └── factory.py       # 스토리지 팩토리
```

**설정 관리**:
```
app/core/config.py       # Pydantic Settings 기반 설정 관리
```

## 계층 간 의존성

Teledrop의 레이어 구조는 **의존성 역전 원칙**을 따릅니다:

1. **Presentation Layer**는 **Application Layer**에 의존함
   - 라우터는 핸들러를 호출하여 비즈니스 로직 수행
   - 의존성 주입을 통해 핸들러 인스턴스를 얻음

2. **Application Layer**는 **Domain Layer**와 **Infrastructure Layer**에 의존함
   - 핸들러는 도메인 모델을 사용하여 비즈니스 로직 구현
   - 핸들러는 인프라스트럭처 서비스를 주입받아 사용

3. **Domain Layer**는 다른 계층에 의존하지 않음
   - 독립적인 비즈니스 규칙과 모델 정의

4. **Infrastructure Layer**는 **Domain Layer**에 의존함
   - 인프라스트럭처 구현은 도메인 모델과 인터페이스를 사용

## 핵심 원칙 적용

- **단일 책임 원칙**: 각 레이어와 컴포넌트는 하나의 명확한 책임을 가짐
- **의존성 역전**: 고수준 모듈(비즈니스 로직)이 저수준 모듈(인프라)에 의존하지 않음
- **관심사 분리**: HTTP 처리, 비즈니스 로직, 데이터 접근이 명확히 분리됨
- **인터페이스 분리**: 스토리지 같은 외부 시스템은 인터페이스를 통해 추상화됨

## 다음 문서

- [Handler 패턴](handlers.md) - 비즈니스 로직 처리 방식
- [프론트엔드 아키텍처 지원](frontend.md) - SPA 및 SSR 구현 