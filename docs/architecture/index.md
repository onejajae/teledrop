# Teledrop 백엔드 아키텍처

Teledrop 백엔드는 **Handler 패턴**을 중심으로 한 **Clean Architecture** 원칙을 따르는 FastAPI 기반 애플리케이션입니다.
이 문서 시리즈는 백엔드 아키텍처의 전체적인 구조와 설계 원칙을 설명합니다.

## 📋 목차

1. [아키텍처 개요](overview.md) - 핵심 설계 원칙 및 다이어그램
2. [레이어 구조](layers.md) - 4계층 아키텍처 설명
3. [Handler 패턴](handlers.md) - 비즈니스 로직 처리 패턴
4. [프론트엔드 아키텍처 지원](frontend.md) - SPA 및 SSR 지원
5. [의존성 주입 시스템](dependency_injection.md) - 의존성 주입 패턴
6. [데이터 모델](data_models.md) - SQLModel 기반 데이터 모델링
7. [인프라스트럭처](infrastructure.md) - 데이터베이스 및 스토리지
8. [보안 및 인증](security.md) - 인증 및 보안 메커니즘
9. [에러 처리](error_handling.md) - 예외 처리 전략
10. [설정 관리](configuration.md) - 환경 설정 관리
11. [확장성 고려사항](extensibility.md) - 시스템 확장 가이드라인

## 📚 문서 사용 가이드

- 각 문서는 독립적으로 읽을 수 있으나, 순서대로 읽는 것을 권장합니다.
- 코드 예제는 실제 애플리케이션 코드에서 추출하였습니다.
- 다이어그램은 실제 구현을 기반으로 작성되었습니다.

## 🔑 핵심 설계 원칙

1. **단일 책임 원칙(SRP)**: 각 클래스/모듈은 하나의 책임만 가짐
2. **의존성 역전 원칙(DIP)**: 추상화에 의존하고 구체적인 구현에 의존하지 않음
3. **관심사 분리**: API 라우팅, 비즈니스 로직, 데이터 접근 레이어 분리
4. **코드 재사용**: Handler 패턴으로 REST API와 SSR 간 로직 공유
5. **명시적 의존성**: 의존성 주입을 통한 컴포넌트 간 명확한 관계
6. **테스트 용이성**: 모든 컴포넌트는 독립적으로 테스트 가능

## 🧩 코드 구조

```
app/
├── main.py             # 애플리케이션 진입점
├── core/               # 핵심 기능 모듈
├── routers/            # API 및 웹 라우터
│   ├── api/            # REST API 라우터
│   └── web/            # SSR 웹 라우터
├── handlers/           # 비즈니스 로직 핸들러
├── models/             # 데이터 모델
├── dependencies/       # 의존성 주입 모듈
│   └── handlers/       # 핸들러 팩토리
└── infrastructure/     # 인프라스트럭처 계층
    ├── database/       # 데이터베이스 연결
    └── storage/        # 파일 스토리지 추상화
```

## 📄 관련 문서

- [API 문서](../API.md)
- [개발 가이드](../DEVELOPMENT.md)
- [배포 가이드](../DEPLOYMENT.md) 