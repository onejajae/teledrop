# 구현 계획 — 스테이지 체크리스트

> 스테이지 하나 = Codex 스레드 하나(`/codex:rescue --fresh`) = 검수 후 커밋 하나.
> 완료된 항목은 체크하고, 스코프가 바뀌면 이 파일을 함께 고친다. 전부 끝나면 이 파일은 지운다.
>
> 2026-07-27: 스테이지 1~8 완료 뒤 [ADR 0005](adr/0005-two-project-functional-core.md)를 채택했다. 아래 완료 기록은 유지하고, 릴리스 전에 아키텍처 분리 스테이지 9~13을 수행한다.

## 모든 스테이지 지시문에 공통으로 들어가는 계약

- 시작 전에 `docs/CONTEXT.md`(용어), `docs/DESIGN.md` 해당 절, 관련 ADR을 읽고 따른다
- 코드 이름에 `docs/CONTEXT.md`의 용어를 그대로 쓴다 (Drop, UploadTicket — Content/Post/Code가 아니다)
- 프로덕션 프로젝트는 `Teledrop.Core`와 `Teledrop` 둘만 둔다. 양쪽 모두 기능별 폴더를 쓰고, 세 번째 프로덕션 csproj, 전역 레이어 디렉터리, MediatR, 범용 Repository/UoW, Entity/DTO 복제를 금지한다 ([ADR 0005](adr/0005-two-project-functional-core.md))
- `Teledrop.Core`는 ASP.NET Core, EF Core, SQLite를 참조하지 않는다. use case는 concrete class로 두고 외부 능력이 필요할 때만 최소 port를 선언한다
- 설계 문서가 답하지 않는 결정을 만나면 임의로 정하지 말고 멈춰서 질문 목록으로 보고한다
- `docs/`, `.github/`, `README*`, `src/Teledrop/Styles/` 수정 금지. 패키지 추가는 지시문에 명시된 것만
- `git commit` 금지 — 커밋은 검수 후 사람이 한다
- 완료는 아래 '완료 게이트' 세 개를 전부 통과한 상태다

## 완료 게이트

완료 기준은 스테이지 지시문에 미리 적는다. 일이 끝난 뒤 판정하지 않는다.

**게이트 1 — 기계 검증.** Codex가 "됐다"고 보고하기 전에 스스로 돌린다(`<verification_loop>`).
- `dotnet build` 경고 0 — csproj에 `TreatWarningsAsErrors`가 켜져 있어 기계적으로 강제된다
- 마이그레이션 적용, 앱 기동, 해당 스테이지의 핵심 엔드포인트 응답
- 해당 스테이지의 통합 테스트 통과 (아래 표)

**게이트 2 — 설계·스코프 검수.** Claude 담당. 기계가 못 잡는 두 가지.
- 설계 부합: 용어가 `docs/CONTEXT.md`대로인가, 동작이 DESIGN.md·ADR대로인가
- **"안 한 것" 검사**: 스코프 밖 파일, 시키지 않은 추상화·패키지·기능.
  **초과분은 미완료와 동급으로 취급하고 걷어낸다** — devel이 죽은 방식이 "요구한 것 + 혹시 몰라서"였다

**게이트 3 — 실물 확인 + 커밋.** 사람 담당.
- 브라우저로 해당 스테이지의 시나리오를 직접 걸어본다. UI가 있는 스테이지(3~6)는 생략 금지
- **커밋이 완료 도장이다.** 커밋하면서 이 파일의 체크박스를 채운다

테스트 정책: **문서에서 굵게 강조한 불변식만** WebApplicationFactory 통합 테스트로 잠근다.
조용히 깨지면 보안이 뚫리는데 화면으로는 안 보이는 것들이다. 그 외(정렬, 화면)는 눈으로 본다.

| 스테이지 | 테스트로 잠글 것 |
|---|---|
| 1 기반 | 없음 (build + 기동으로 충분) |
| 2 인증 | 미인증 리다이렉트, 로그인 성패, **비밀번호 변경 → 전 세션 즉사** |
| 3 파일 코어 | 업로드→행+파일+해시 일치, **삭제는 DB 행 먼저**, private 고정 생성 |
| 4 목록 | 없음 (수동) |
| 5 상세 | **잠금 401 메타 마스킹**, private 비인증 차단, 비밀번호 검증 |
| 6 티켓 | **유효성 규칙 전부** — 만료/소진/30분 창/10회 제한/GET 무부작용 |
| 7 API | 키 없음·오류 401, **private 고정**, 링크 반환 |
| 8 Dockerfile | `docker build` + 컨테이너 기동 스모크 |

실패 경로는 둘을 구분한다.
- **게이트에서 걸림** → `--resume`으로 델타 지시. 같은 스레드라 맥락이 살아 있다
- **Codex가 "문서가 답하지 않는다"며 멈춤** → 실패가 아니라 계약이 작동한 것.
  결정하고, 문서를 고치고, resume한다. 이걸 실패처럼 다루면 다음부터 멈추는 대신 임의로 정해버린다

## 스테이지

- [x] **1. 데이터 기반** — Drop 엔티티, `TeledropDbContext`, SQLite 연결, 첫 마이그레이션, 설정 바인딩(`SHARE_DIRECTORY`, `MAX_UPLOAD_BYTES`), 기동 시 share 디렉터리 보장
- [x] **2. 인증/세션** — 로그인/로그아웃 페이지, 쿠키 인증(프레임워크 기본, 암호화 쿠키), argon2 검증(`WEB_USERNAME`/`WEB_PASSWORD`), 슬라이딩 30일, 비밀번호 지문 대조 폐기(`OnValidatePrincipal`)
- [x] **3. 파일 코어** — 업로드(디스크 스트리밍, sha256, private 고정 생성), 다운로드(`PhysicalFile` Range), 삭제(DB 행 먼저), htmx 업로드 진행률
- [x] **4. 목록** — 제목·파일명 검색, 정렬(created_at/title/size × asc·desc), 페이지네이션, favorite 토글
- [x] **5. 드롭 상세** — 메타 수정, publish(공개 전환), 드롭 비밀번호 설정/해제(argon2 + Data Protection 쿠키), 잠금 화면 메타 마스킹(401), slug 자동 생성(형용사+명사, 코드 내 배열)·커스텀 slug
- [x] **6. 업로드 티켓** — 발급/목록/폐기 UI(코드 평문 표시, no-store), 게스트 업로드 페이지(없는 경로 404, 코드 10회 제한, 소진·만료 규칙, GET 무부작용, noindex/no-referrer, 진행률)
- [x] **7. API 업로드** — `POST /api/upload`, `X-API-Key`(`TELEDROP_API_KEY`), private 고정, 공유 URL 반환
- [x] **8. Dockerfile** — 멀티스테이지 .NET 빌드, node 스테이지 없음(생성 CSS·htmx가 커밋되어 있음), 컨테이너 기동 스모크

순서 의존: 7은 slug 생성(5) 뒤여야 한다. 6과 7은 서로 바꿔도 된다. 8은 마지막.

## 아키텍처 분리 스테이지 — ADR 0005

이 단계는 기능 추가나 동작 변경이 아니다. route, HTTP 응답, DB schema, 저장 파일 형식을 그대로 두고 업무 로직과 구현의 의존 경계만 옮긴다.

- [x] **9. Core 경계** — `Teledrop.Core` class library와 project reference 추가, Core의 금지 참조를 빌드에서 확인, 기존 테스트 프로젝트가 Core와 Web을 모두 참조
- [x] **10. 순수 모델과 정책** — `Drop`, `UploadTicket`, 접근 판정, 티켓 유효성·상태 전이를 Core로 이동하고 프레임워크 없는 단위 테스트 추가
- [x] **11. 드롭 use case** — private 생성·삭제·publish 등 작업 순서를 Core의 concrete use case로 이동, 파일·DB 능력은 최소 port로 선언하고 Web에서 구현
- [x] **12. 게스트 업로드 use case** — 코드 실패·30분 창·소진 규칙을 Core로 이동, 드롭 생성과 티켓 소진의 원자성은 특화 port의 EF 구현으로 보장
- [x] **13. Web adapter 정리** — PageModel/API는 인증·multipart·antiforgery·응답 변환만 남기고 전체 회귀 테스트와 컨테이너 스모크 수행

순서 의존: 9 → 10 → 11·12 → 13. 각 스테이지는 동작 보존을 기존 HTTP 통합 테스트로 확인한다.

## 릴리스 작업 — Codex 위임 없음 (사람 + Claude)

스테이지가 아니라 릴리스 절차다. 공통 계약이 Codex의 `.github/`·`README*` 수정을 금지하므로 여기는 위임 대상이 아니다.
시점: **스테이지 13까지 완료하고 로컬 실사용으로 확인한 뒤, main 머지 전.**

- [ ] compose 갱신 — 이미지 참조, 환경변수(`WEB_USERNAME` `WEB_PASSWORD` `TELEDROP_API_KEY` `SHARE_DIRECTORY` `MAX_UPLOAD_BYTES`)
- [ ] GitHub Actions 교체 — 현행 워크플로는 develop/main 트리거에 Python Dockerfile 전제. 교체 전에 main에 머지하면 깨진 빌드가 발화하고, 최악의 경우 죽은 이미지가 `ghcr.io/onejajae/teledrop:latest`를 덮는다
- [ ] README 재작성 — 태그라인(`powered by REST API` 삭제)과 설치 문서 전체(환경변수·티켓 기능)
- [ ] **최종 인수: 기존 인스턴스의 파일을 새 인스턴스로 옮기고 구 버전을 내린다.** 실사용 전환이 곧 프로젝트 완료다

**릴리스 작업이 끝나기 전에는 main에 머지하지 않는다.**

## 모델 고정 — gpt-5.6-sol, effort max

- 모든 Codex 호출에 **`--model gpt-5.6-sol`을 명시**한다. 다른 모델을 쓰지 않는다
- **`--effort`는 절대 넘기지 않는다.** 플러그인 허용값(`none`~`xhigh`)에 `max`가 없어서, 명시하는 순간
  `~/.codex/config.toml`의 `model_reasoning_effort = "max"`보다 낮아진다. 비워두면 config의 max가 적용된다

## 스테이지 루프

1. `/codex:rescue --fresh --model gpt-5.6-sol [--background] <지시문>` — 3·5·6·8은 background 권장
2. 백그라운드면 `/codex:status` → `/codex:result`
3. 검수: `dotnet build`·실행 + 설계 부합(위 공통 계약 위반 여부)
4. 리뷰: 5·6은 `/codex:adversarial-review`(접근 제어·티켓 규칙이 보안 전부), 나머지는 `/codex:review`
5. 수정은 같은 스레드로: `/codex:rescue --resume --model gpt-5.6-sol "<델타 지시>"`
6. 커밋 후 다음 스테이지
