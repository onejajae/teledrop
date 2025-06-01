# 아키텍처 개요

Teledrop 백엔드는 **Clean Architecture** 원칙을 기반으로 설계되었으며, **Handler 패턴**을 활용하여 구현되었습니다. 이 문서에서는 아키텍처의 핵심 원칙과 전체적인 구조를 설명합니다.

## 핵심 설계 원칙

- **단일 책임 원칙(SRP)**: 각 Handler는 하나의 명확한 책임을 가집니다
- **의존성 역전 원칙(DIP)**: 추상화에 의존하며, 구체적인 구현에 의존하지 않습니다
- **관심사 분리(SoC)**: 비즈니스 로직, 데이터 접근, 인프라스트럭처가 명확히 분리됩니다
- **테스트 가능성**: 모든 의존성이 주입되어 단위 테스트가 용이합니다
- **확장성**: 새로운 기능 추가 시 기존 코드 변경을 최소화합니다

## 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   API Routes    │  │   Web Routes    │  │  Middleware  │ │
│  │ (FastAPI)       │  │ (FastAPI)       │  │              │ │
│  │                 │  │                 │  │ • CORS       │ │
│  │ • REST API 호출  │  │ • 템플릿 렌더링   │  │ • TrustedHost│ │
│  │ • SPA 서빙      │  │ • 서버 사이드 렌더링│  │              │ │
│  │ • JSON 응답     │  │ • HTML 응답      │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Drop Handlers  │  │  File Handlers  │  │ Auth Handlers│ │
│  │                 │  │                 │  │              │ │
│  │ • DropCreate    │  │ • FileUpload    │  │ • Login      │ │
│  │ • DropUpdate    │  │ • FileDownload  │  │ • TokenValid │ │
│  │ • DropDelete    │  │ • FileDelete    │  │ • ApiKeyMgmt │ │
│  │ • DropList      │  │ • FileReplace   │  │ • AuthHandler│ │
│  │                 │  │ • FileHandler   │  │              │ │
│  │ • DropHandler   │  │                 │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Data Models   │  │   Exceptions    │  │   Mixins     │ │
│  │                 │  │                 │  │              │ │
│  │ • Drop          │  │ • TeledropError │  │ • Logging    │ │
│  │ • File          │  │ • ValidationErr │  │ • Validation │ │
│  │ • ApiKey        │  │ • AuthError     │  │ • Hashing    │ │
│  │ • User          │  │ • StorageError  │  │ • Timestamp  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Infrastructure Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │    Database     │  │     Storage     │  │    Config    │ │
│  │                 │  │                 │  │              │ │
│  │ • SQLModel      │  │ • Local Storage │  │ • Settings   │ │
│  │ • SQLite        │  │ • S3 Storage    │  │ • Environment│ │
│  │ • Connection    │  │ • Interface     │  │ • Validation │ │
│  │ • Session Mgmt  │  │ • Factory       │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 레이어 구조

Teledrop은 4개의 계층으로 구성됩니다:

1. **Presentation Layer** (`app/routers/`):
   - HTTP 요청/응답 처리, 라우팅, 입력 검증
   - API Routes: REST API 엔드포인트 (현재 구현)
   - Web Routes: SSR 웹 페이지 (향후 구현)
   - Middleware: CORS 및 보안 설정

2. **Application Layer** (`app/handlers/`):
   - 비즈니스 로직 구현, 유스케이스 조정
   - Handler 패턴을 통한 명확한 책임 분리
   - 트랜잭션 관리 및 보상 트랜잭션 패턴
   - 의존성 주입을 통한 결합도 감소

3. **Domain Layer** (`app/models/`, `app/core/exceptions.py`):
   - 데이터 모델, 비즈니스 규칙, 예외 정의
   - SQLModel을 활용한 도메인 모델 정의
   - 계층적 예외 구조
   - 믹스인을 통한 횡단 관심사 처리

4. **Infrastructure Layer** (`app/infrastructure/`):
   - 외부 시스템 연동, 데이터 저장소, 설정
   - 데이터베이스 연결 및 세션 관리
   - 스토리지 인터페이스 및 구현체
   - 환경 설정 및 관리

## 구현 특징

### 핵심 컴포넌트

- **Handler 패턴**: 비즈니스 로직의 단일 책임 단위
- **의존성 주입**: FastAPI를 활용한 의존성 관리
- **SQLModel**: SQLAlchemy와 Pydantic을 결합한 ORM
- **비동기 처리**: async/await 패턴을 활용한 효율적인 I/O 처리
- **스트리밍 인터페이스**: 대용량 파일 처리를 위한 스트리밍 API

### 보안 및 인증

- **인증**: 의존성 주입 시스템을 통한 인증 처리 (미들웨어 아님)
- **권한 검증**: Handler 내부에서 권한 검증 로직 구현
- **로깅**: LoggingMixin을 통한 구조화된 로깅

## 다음 문서

- [레이어 구조](layers.md) - 각 레이어의 상세 설명
- [Handler 패턴](handlers.md) - 비즈니스 로직 패턴 