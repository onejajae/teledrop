# ADR 0002 — SvelteKit SPA를 버리고 C# + Razor SSR로 간다

- 상태: 채택 (프로젝트 경계는 ADR 0005로 일부 대체)
- 날짜: 2026-07-26

## 맥락

main은 FastAPI(백엔드 1,138줄) + SvelteKit SPA(`web/src` 1,519줄, 라우트 2개) 구조다. SPA가 REST API의 클라이언트다.

devel에서 이미 한 번 SSR(Jinja2 + htmx)로 갈아엎었다. 그 리팩토링 전체를 폐기하기로 했지만, SSR로 옮긴 판단 자체는 따로 평가할 필요가 있었다. 이유가 둘 나왔다.

**1. SPA 인증에서 쿠키 관리가 힘들었다.** 커밋 이력에 흔적이 남아 있다.

```
861d2cb feat: cookie based authorization
aad205a fix: cookie secure
a49392c fix: delete cookie when fail auth
7c84bb4 fix: token validation in utc timezone
68fd1cb fix: token revalidation
4806ff4 fix: detect token time out in preview page
```

**2. 한 언어에서 산출물이 나오는 게 깔끔했다.**

## 진단

두 이유를 코드로 검증했더니 원인이 처음 생각과 달랐다.

**인증**: main에 refresh token은 없다. 쿠키 하나(`access_token`에 `Bearer <JWT>`)뿐이고, vite 프록시(`/api` → `127.0.0.1:8000`)도 이미 걸려 있어 dev 환경은 same-origin이다. 진짜 원인은 SPA가 아니라 **JWT를 세션으로 쓴 것**이었다. 만료가 토큰에 박혀 있어 `/me`가 호출될 때마다 재발급하는 구조가 됐고(`68fd1cb`), 그래서 프론트엔드가 만료를 스스로 감지해야 했다(`4806ff4`). 서버 사이드 세션이면 프론트가 할 일이 0이다. devel에서 실제로 그렇게 고쳤는데(`session_repository.py`), SSR 전환과 같은 커밋에 묶이는 바람에 공이 SSR로 갔다.

**한 언어**: 빌드 수준에서는 달성되지 않았다. devel의 Dockerfile에도 `node:24-alpine` 스테이지가 그대로 있고, `.gitignore`가 `static/gen/*`을 제외해서 CSS를 빌드로 만들어야 했다. 다만 **개발 중에 상시로 띄우는 프로세스가 2개에서 1개로 준 것**은 실재하는 차이다. 화면 하나 고칠 때 언어와 프로세스를 오가지 않는 이득은 매일 반복된다.

## 결정

**UI는 SSR로 간다. main의 SvelteKit SPA 1,519줄을 버린다.**

**언어는 C#(.NET + Razor Pages)로 간다. Python/FastAPI를 버린다.**

## 근거

SSR로 가는 이유:

- **인증이 문제 자체를 없앤다.** SSR이면 API 인증이라는 개념이 없다. CORS도, `credentials: 'include'`도, dev 프록시도 사라진다. 설정으로 고치는 것과 존재하지 않는 것은 다르다
- **한 언어의 이득은 편집 단계에서 실재한다**
- **게스트 업로드 페이지는 이미 서버 렌더링으로 정했다.** 낯선 사람에게 SPA 번들을 받게 할 이유가 없다. 소유자 UI가 SPA면 한 앱에 UI 패러다임이 둘 공존한다

"1,519줄이 언어 이전에도 살아남는다"는 자산론은 기각했다. **그 줄을 지키는 것은 그것을 싫어한 이유(언어 갈아타기)를 함께 지키는 것**이다. 다시 쓰고 싶은 이유가 따로 있으면 그건 자산이 아니라 관성이다.

C#으로 가는 이유:

SSR 확정으로 UI는 어느 언어를 골라도 재작성이고, 백엔드 1,138줄 중 SSR 전환에서 살아남는 건 절반쯤이다. **Python에 남아 아끼는 건 600줄 정도**라 이전 비용이 결정 요인이 아니다. 그렇다면 장기 적합성으로 고른다.

- **Range 요청이 프레임워크 기본이다.** `PhysicalFile`이 Range/ETag/If-Range를 처리한다. main에서 손으로 짠 `get_file_range_by_key`가 통째로 사라진다. 파일 서버의 핵심 경로가 곧 .NET의 기본 기능이다
- **쿠키 인증이 내장이다.** 위에서 진단한 문제를 짤 필요 없이 얻는다
- **Razor 템플릿이 컴파일된다.** 오타가 빌드에서 잡힌다. Jinja2는 런타임 500이고 하필 안 쓰는 화면에서 몇 달 뒤 터진다
- **EF Core 마이그레이션이 퍼스트파티다.** devel에서 alembic을 걷어낸 자리를 메운다
- 몇 달 만에 다시 열었을 때 컴파일러가 깨진 곳을 알려준다
- 사용자가 업무에서 C#을 실무 수준으로 쓴다. 학습 부하 위험이 없다
- **코드베이스가 다시 1,500줄로 작아지는 지금이 이전 비용이 가장 싼 순간이다.** 나중에 옮기면 같은 일을 두 번 한다

## 결과

- `web/` 전체를 버린다. REST API는 UI의 클라이언트가 아니게 되고, iOS 단축어용 엔드포인트 하나만 남는다
- Node를 빌드에서 없애려면 **생성된 CSS를 커밋한다.** devel은 `gen/*`을 gitignore해서 node 스테이지가 강제됐다
- 업로드 진행률은 `htmx:xhr:progress`로 붙인다. JS 없으면 폼 POST로 동작하고 JS 있으면 진행률이 붙는 점진적 향상이다
- SSR 쪽 개발 루프도 공짜는 아니다. devel의 `run_dev.sh`는 시작할 때마다 CSS를 새로 빌드했고 HMR이 없었다

## 검토했으나 버린 것 — Blazor

SSR 안에서 Razor Pages 대신 **Blazor Web App**을 쓰는 안을 검토했다. 근거는 두 가지였고 둘 다 실재한다 — 컴포넌트 + 바인딩 + code-behind 구조가 소유자가 업무에서 하는 MVVM 앱 개발과 닮아 익숙하고, htmx가 필요 없어져 JS 라이브러리가 아예 사라진다("한 언어" 논거가 오히려 강해진다).

그럼에도 버린 이유는 셋이다.

**1. HTML 표준에서 멀어진다.** Blazor에서 `<button @onclick>`은 버튼이 아니라 회로로 가는 RPC이고, `EditForm`은 대화형 모드에서 POST하지 않는다. JS가 없거나 회로가 안 붙으면 화면이 움직이지 않는다. 렌더 결과는 HTML이지만 작성하는 것은 HTML이 아니라 렌더 트리다. 반면 htmx는 `<form method="post">`에 `hx-post`를 얹는 방식이라 JS가 죽으면 평범한 폼 POST로 떨어진다 — 이 축에서 htmx는 타협이 아니라 가장 정렬된 선택이다. 낯선 사람이 낯선 브라우저로 여는 게스트 업로드 페이지가 있는 앱에서 이 성질은 실질적인 가치다.

**2. 이 앱의 핵심 동작이 하필 Blazor가 가장 약한 지점이다.** `InputFile`은 파일 바이트를 SignalR 회로로 흘려보낸다. `maxAllowedSize`와 메시지 크기 제한을 손봐야 하고, 처리량이 평범한 multipart POST보다 떨어지며, 회로가 끊기면 업로드가 날아간다. Microsoft 문서도 큰 파일은 별도 엔드포인트를 권한다. 우회는 가능하지만 **핵심 동작을 프레임워크 밖으로 빼내는 것**이고, 그러면 진행률 때문에 결국 JS가 돌아온다.

**3. MVVM이 값을 할 만큼 복잡한 앱이 아니다.** 화면이 로그인 / 업로드 / 목록 / 드롭 상세 / 티켓 관리 다섯 개고, 전부 폼과 리스트다. 상호의존적인 클라이언트 상태도 실시간도 없다. MVVM은 상태가 얽혀 수동 관리가 어려울 때 값을 하는데 여기엔 얽힐 상태가 없다. 남는 것은 익숙함뿐이고, 그것만으로 1·2를 상쇄하지 못한다.

덧붙여, Razor Pages의 `PageModel`도 ViewModel과 상당히 닮았다 — `[BindProperty]`로 프로퍼티를 바인딩하고 `asp-for`로 뷰에 묶고 핸들러 메서드가 동작을 받으며 DI는 생성자 주입이다. 차이는 수명뿐이다. ViewModel은 살아 있으면서 `PropertyChanged`로 UI를 밀지만 `PageModel`은 요청 하나 동안 살고 화면은 다시 그려진다. **잃는 것은 라이브 반응성이고, 이 앱에는 라이브로 반응해야 할 것이 없다.**

## 경계 (중요)

**.NET 생태계의 기본 조언이 정확히 devel을 죽인 방향이다.** Clean Architecture 템플릿, MediatR, Repository + Unit of Work, Entity/DTO 분리 — 검색해서 나오는 .NET 튜토리얼 대부분이 레이어를 권한다. devel의 `domain/application/infrastructure/interfaces` 구조는 Python보다 .NET 문화권에서 더 흔한 모양이다.

**언어를 바꾸면 이 유혹은 약해지는 게 아니라 강해진다.** 이 ADR을 채택할 때는 단일 프로젝트 + 기능별 폴더를 경계로 정했다.

구현 완료 뒤 업무 규칙과 ASP.NET/EF/파일시스템 구현 사이의 의존 방향을 컴파일러로 강제할 필요가 확인되어, 프로젝트 경계만 [ADR 0005](0005-two-project-functional-core.md)의 `Teledrop.Core` + `Teledrop` 2프로젝트 구조로 대체했다. C# + Razor SSR, 기능별 폴더, MediatR·범용 Repository/UoW·Entity/DTO 복제 금지는 그대로 유지한다.
