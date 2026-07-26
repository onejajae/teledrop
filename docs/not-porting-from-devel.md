# devel에서 이식하지 않는 것

> devel 브랜치(`origin/devel`, main 대비 37커밋 / 309파일 / +21,816줄)의 리팩토링을 폐기하기로 했다.
> devel은 **이식 대상이 아니라 아이디어 창고**다. 나중에 다시 열어봤을 때 같은 판단을 반복하지 않도록 이유를 남긴다.

## 무슨 일이 있었나

| | main | devel |
|---|---|---|
| Python | 1,138줄 | 15,764줄 (약 14배) |
| 구조 | router → service → repository | domain / application / infrastructure / interfaces / core / bootstrap |
| UI | SvelteKit SPA | Jinja2 + htmx SSR |
| 범위 | 단일 사용자 | 멀티유저, 회원가입, grant/unlock, API 키, 관리자 셋업 |

업로드 기능 하나가 devel에서는 6개 레이어에 걸쳐 20개 파일을 거친다. 원인은 **아키텍처 야심 + 범위 폭주**이며, 프레임워크나 언어의 문제가 아니었다. 같은 기간에 프론트엔드 스택 교체와 기능 확장까지 동시에 진행했다.

## 버리는 것

### 멀티유저 일체
user 테이블, 회원가입(`ENABLE_REGISTRATION`), 소유권 검사, private 드롭의 비소유자 404 마스킹, `/setup?token=` 관리자 부트스트랩, `WEB_USERNAME`/`WEB_PASSWORD` deprecation.

**이유**: 사용자는 언제나 한 명이다. 멀티유저는 실제 수요가 아니라 "제대로 된 서비스라면 있어야지"였다. 계정이 사라지면 소유권·권한·가시성 규칙이 통째로 사라진다.

### 6계층 아키텍처
`domain` / `application` / `infrastructure` / `interfaces` / `core` / `bootstrap`, ports & adapters, use case 객체, Unit of Work, presenter 레이어(3,078줄).

**이유**: 셀프호스팅 개인 파일 공유 도구에 헥사고날/DDD 풀세트를 적용한 것. 버리는 것은 로직과 구현의 분리 자체가 아니라, 그 사이에 Domain/Application/Infrastructure/Interfaces와 범용 port, Unit of Work, DTO, presenter를 모두 세운 구조다.

대체안은 `Teledrop.Core`와 Web host 두 프로젝트만 두고 양쪽 모두 기능별 폴더로 구성하는 것이다. Core에는 업무 규칙과 use case, 필요한 최소 port만 두며 범용 Repository/UoW는 만들지 않는다. [ADR 0005](adr/0005-two-project-functional-core.md) 참고.

### grant / unlock 서브시스템
`domain/drop/grants.py`, `core/drop_grants.py`, `core/drop_unlock_tokens.py`, 서명 쿠키 2종, secret key 2개(`DROP_GRANT_SECRET_KEY`, `DROP_UNLOCK_SECRET_KEY`), 버전 태그와 HMAC 직접 구현.

**이유**: 파일별 비밀번호 기능은 **남긴다**. 하지만 이 구현은 버린다. argon2 해시 + 언락 폼 + ASP.NET Data Protection으로 서명한 쿠키면 되고, HMAC을 손으로 짤 일이 아니다. 이 덩어리는 다운로드 방향이라 게스트 업로드와도 무관하다.

### API 키 서브시스템
`auth_api_key.py`, `api_key_repository.py`, `uow_api_key.py`, `use_cases/api_key.py`, `presenters/api_keys_page.py`, 템플릿 2개, 테스트 — 파일 8개.

**이유**: iOS 단축어용으로 **필요하지만** 환경변수 하나면 된다. 기기별 독립 폐기가 필요 없다. [ADR 0003](adr/0003-three-auth-paths.md) 참고.

### 단어 풀 slug 생성기
txt 파일 10개(noun/verb/adjective/abstract/direction/sound/name/date/number/phonetic) + 설정 2개(`SLUG_WORDS_FILES_ENABLED`, `SLUG_WORDS_FILES_DIR`) + 시작 시 로딩 + 로딩 실패 시 uuid 폴백.

**이유**: 읽히는 slug는 **남긴다**. 하지만 형용사·명사 배열 두 개를 코드에 박아 넣으면 된다. 컴파일에 들어가 있으면 로딩이 실패할 수 없으므로 폴백 경로 자체가 존재하지 않는다.

### 그 외
- **SSR presenter 레이어** — SSR은 남기지만 presenter 추상화는 버린다. 평범한 핸들러면 된다
- **`access_scope` enum** — main의 `user_only` 불리언으로 되돌린다
- **docs/ko + docs/en 이중 문서** — 혼자 보는 문서를 두 벌 유지할 이유가 없다
- **조회·삭제·수정 REST 엔드포인트** — SSR이면 소비자가 없다

## 가져오는 것

devel이 옳게 판단한 것도 있다.

- **세션 진단** (`session_repository.py`, `session_http.py`) — main의 JWT-as-session이 실제 문제였다는 판단은 가져온다. 이 공이 SSR이 아니라 세션에 있다는 것도([ADR 0002](adr/0002-ssr-and-csharp.md) 진단 절). 다만 **기구는 가져오지 않는다.** devel은 세션을 DB 테이블에 뒀지만, 요구의 실체는 "클라이언트가 세션 수명을 관리하지 않는 것"이고 ASP.NET Core의 암호화 쿠키가 테이블 없이 충족한다. 폐기는 비밀번호 지문 대조로 한다 — [DESIGN.md](DESIGN.md) '인증 경로' 절 참고
- **SSR 방향 자체** — 채택. 문제는 SSR이 아니라 그 위에 얹은 레이어였다
- **잠긴 드롭의 메타데이터 마스킹** — 방향이 맞다. main도 이미 401로 막고 있으므로 그 동작을 보존한다
- **`file_hash` 제거 판단** — 다만 CAS 최적화 여지로 **남기기로** 뒤집었다. 업로드 스트림을 어차피 통과시키므로 나중에 전 파일을 다시 읽는 백필보다 싸다

## 남은 흔적

작업 트리에 devel 시절의 미추적 디렉터리가 있다.

- `app/` — devel의 6계층 구조 (`__pycache__`, `application`, `bootstrap`, `core`, `domain`, `infrastructure`, `interfaces`)
- `ui-build/node_modules`

둘 다 새 구조와 충돌하므로 작업 시작 전에 정리한다. devel 브랜치 자체는 남겨두면 참조 가능하다.
