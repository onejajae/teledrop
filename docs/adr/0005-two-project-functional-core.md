# ADR 0005 — 업무 로직과 구현을 두 프로젝트로 분리한다

- 상태: 채택
- 날짜: 2026-07-27

## 맥락

refactor/v2는 devel의 6계층 구조를 버리고 단일 ASP.NET Core 프로젝트 안에서 기능별 폴더로 다시 만들었다. 이 선택은 범위 폭주와 추상화 증식을 멈추는 데 유효했다.

구현이 끝난 뒤 코드를 다시 보면 다른 문제가 보인다. `PageModel`과 API 엔드포인트가 다음 책임을 함께 가진다.

- HTTP 요청과 multipart 형식 해석
- 쿠키, API 키, antiforgery 처리
- 드롭 접근 규칙과 private 기본값
- 업로드 티켓의 만료, 재시도 창, 실패 횟수, 소진 규칙
- EF Core 트랜잭션과 SQLite 동시성 제어
- 실제 파일 저장과 실패 시 정리
- HTML, redirect, JSON 응답 선택

파일 수를 줄이기 위해 한곳에 모은 결과, 제품 규칙과 프레임워크 구현 사이의 의존 경계를 컴파일러가 보장하지 못한다. 특히 업로드 티켓처럼 보안 규칙이 많은 기능은 HTTP 코드 속에서 규칙을 읽고 검증해야 한다.

목표는 Clean Architecture 템플릿을 다시 도입하거나 구현체 교체를 위한 추상화를 만드는 것이 아니다. **teledrop의 업무 규칙을 ASP.NET Core, EF Core, SQLite, 파일시스템과 분리하고 그 의존 방향을 컴파일러로 고정하는 것**이다.

## 결정

프로덕션 프로젝트를 정확히 둘로 둔다.

```
src/
├── Teledrop.Core/
│   └── Teledrop.Core.csproj
└── Teledrop/
    └── Teledrop.csproj
```

- **`Teledrop.Core`** — 엔티티, 순수 정책, use case, use case가 외부에 요구하는 최소 port
- **`Teledrop`** — ASP.NET Core host이자 구현 프로젝트. Razor Pages, HTTP 엔드포인트, EF Core, SQLite, 파일시스템, 보안 구현, DI composition root

의존 방향은 `Teledrop → Teledrop.Core` 하나뿐이다. `Teledrop.Core`는 `Teledrop`을 참조하지 않으며 ASP.NET Core, EF Core, SQLite 패키지를 참조하지 않는다. 외부 패키지도 기본적으로 두지 않고, 필요해지면 그 이유를 별도 결정으로 기록한다.

테스트 프로젝트는 둘을 모두 참조할 수 있다. Core의 규칙과 use case는 단위 테스트하고, EF의 원자성·파일 저장·HTTP 접근 경계는 Web 통합 테스트로 검증한다.

## 무엇을 Core에 둔다

다음처럼 구현 기술이 바뀌어도 같아야 하는 결정을 Core에 둔다.

- `Drop`, `UploadTicket`와 그 상태
- 모든 새 드롭은 private으로 시작한다는 규칙
- private / public / 드롭 비밀번호에 따른 접근 판정
- 업로드 티켓의 24시간 만료, 최초 정상 사용 뒤 30분 재시도 창, 실패 10회 폐기, 1회 소진
- 드롭 생성, 삭제, publish, 티켓 발급·폐기·게스트 업로드의 작업 순서
- DB 행을 먼저 삭제하고 저장 파일을 나중에 지우는 순서
- 저장 성공 뒤 DB 반영이 실패했을 때 파일을 정리하는 보상 동작
- use case 결과를 표현하는 작은 enum과 record

Core는 `IActionResult`, HTTP 상태 코드, header, cookie, Razor view model을 반환하지 않는다. 엔티티와 같은 모양의 persistence DTO나 presentation DTO도 만들지 않는다.

단순 목록 조회, 페이지네이션용 EF 쿼리, 화면 전용 formatting처럼 제품 규칙이 없는 코드는 Web에 남겨도 된다. 모든 요청을 의무적으로 use case 객체로 감싸지 않는다.

## 무엇을 Web에 둔다

- multipart boundary와 section 순서 해석
- antiforgery, owner session, API key header
- redirect, HTMX header, JSON과 HTML 응답
- EF Core `DbContext`, migration, SQLite 쿼리와 원자적 update
- 실제 `FileStream`, 경로 계산, 파일 삭제
- Argon2 구현과 ASP.NET Data Protection cookie
- 로깅과 DI 등록

Web handler는 transport를 검증하고 Core use case를 호출한 뒤 그 결과를 HTTP 응답으로 변환한다. 업무 규칙을 다시 판단하지 않는다.

## Port 규칙

Port는 Core use case가 외부 세계에 요청해야 하는 **능력**이 있을 때만 Core에 선언한다.

- use case마다 인터페이스를 만들지 않는다. use case는 기본적으로 concrete class다
- `IRepository<T>` 같은 범용 CRUD repository를 만들지 않는다
- 별도 Unit of Work 추상화를 만들지 않는다
- 인터페이스는 EF나 파일시스템 API를 그대로 복사하지 않고 작업에 필요한 최소 계약만 드러낸다
- 같은 엔티티를 domain model / persistence model / DTO로 반복 정의하지 않는다. EF 매핑은 Web의 Fluent API로 Core 엔티티에 붙인다

트랜잭션 자체를 Core에 노출하지 않는다. 원자성이 업무 규칙인 경우 그 원자적 능력을 특화 port로 선언한다. 예를 들어 게스트 업로드는 드롭 생성과 티켓 소진을 함께 커밋해야 하므로 다음과 같은 계약을 둘 수 있다.

```csharp
public interface IGuestUploadCommitter
{
    Task<bool> TryCommitAsync(
        Drop drop,
        Guid uploadTicketId,
        DateTime requestStartedAtUtc,
        CancellationToken cancellationToken);
}
```

Web의 EF 구현체가 내부에서 transaction과 조건부 `ExecuteUpdate`를 사용한다. Core는 transaction 기구가 아니라 **둘이 함께 성공해야 한다**는 요구만 안다.

## 폴더 원칙

두 프로젝트 안에서도 기능별로 모은다.

```
Teledrop.Core/
├── Drops/
└── UploadTickets/

Teledrop/
├── Features/
│   ├── Auth/
│   ├── Drops/
│   └── UploadTickets/
├── Data/
└── Pages/
```

`Domain/`, `Application/`, `Infrastructure/`, `Interfaces/` 같은 전역 레이어 폴더는 만들지 않는다. 프로젝트 경계는 로직과 구현을 나누고, 폴더 경계는 기능을 모은다.

## 근거

**컴파일러가 방향을 지킨다.** 폴더만 나누면 Core 코드가 우연히 `HttpContext`나 `DbContext`를 참조해도 막을 수 없다. 별도 class library는 그 결합을 빌드에서 실패시킨다.

**규칙을 프레임워크 없이 읽고 검증할 수 있다.** 업로드 티켓 상태 전이와 접근 정책을 HTTP 요청 구성 없이 테스트할 수 있다.

**두 프로젝트면 목적을 달성한다.** Domain/Application/Infrastructure/Web을 각각 프로젝트로 만들 이유가 없다. Core와 구현 host 둘만으로 의존 역전과 배포 단순성을 함께 얻는다.

**vertical slice를 버리지 않는다.** 기능 하나가 여러 기술 레이어 디렉터리를 왕복하지 않는다. Core의 Drops와 Web의 Drops 두 장소만 보면 된다.

## 결과

- 프로덕션 csproj가 하나 늘어난다
- Web 구현을 호출하는 Core use case에는 소수의 port가 필요하다
- 단순 handler는 계속 Web에 남으므로 모든 기능이 같은 모양을 갖지는 않는다
- EF의 transaction·동시성 보장은 여전히 통합 테스트가 필요하다
- 기존 동작, route, DB schema, 저장 파일 형식은 이 분리만으로 바뀌지 않는다
- `docs/DESIGN.md`와 구현 계획은 이 경계를 기준으로 갱신한다

## 대체하는 결정

[ADR 0002](0002-ssr-and-csharp.md)의 C# + Razor SSR 결정은 유지한다. 다만 그 ADR의 “단일 프로젝트” 경계는 이 결정으로 대체한다.

## 검토했으나 버린 것

### 폴더로만 Logic과 Implementation을 나눈다

파일 이동 비용은 가장 작지만 의존 방향을 강제하지 못한다. 이번 변경의 목적을 충족하지 않는다.

### Domain / Application / Infrastructure / Web 프로젝트

devel의 6계층 구조와 같은 비용을 다시 만든다. teledrop에는 Core와 구현 host 사이보다 더 세밀한 배포·조직 경계가 없다.

### 기존 단일 프로젝트를 유지한다

현재 규모만 보면 가장 단순하다. 그러나 보안 규칙과 구현 코드가 이미 한 handler 안에서 함께 변하고 있으며, 이 결합을 유지하면 장기적으로 어떤 코드가 제품 규칙인지 다시 판별해야 한다.
