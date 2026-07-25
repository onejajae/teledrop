# 구현 계획 — 스테이지 체크리스트

> 스테이지 하나 = Codex 스레드 하나(`/codex:rescue --fresh`) = 검수 후 커밋 하나.
> 완료된 항목은 체크하고, 스코프가 바뀌면 이 파일을 함께 고친다. 전부 끝나면 이 파일은 지운다.

## 모든 스테이지 지시문에 공통으로 들어가는 계약

- 시작 전에 `CONTEXT.md`(용어), `docs/DESIGN.md` 해당 절, 관련 ADR을 읽고 따른다
- 코드 이름에 CONTEXT.md의 용어를 그대로 쓴다 (Drop, UploadTicket — Content/Post/Code가 아니다)
- 단일 프로젝트 + `Features/` 폴더. 새 csproj, 레이어 디렉터리, MediatR, Repository/UoW 추상화 금지 ([ADR 0002](adr/0002-ssr-and-csharp.md) '경계')
- 설계 문서가 답하지 않는 결정을 만나면 임의로 정하지 말고 멈춰서 질문 목록으로 보고한다
- `docs/`, `.github/`, `README*`, `Styles/` 수정 금지. 패키지 추가는 지시문에 명시된 것만
- `git commit` 금지 — 커밋은 검수 후 사람이 한다
- 완료 기준에 `dotnet build` 경고 0 포함

## 스테이지

- [ ] **1. 데이터 기반** — Drop 엔티티, `TeledropDbContext`, SQLite 연결, 첫 마이그레이션, 설정 바인딩(`SHARE_DIRECTORY`, `MAX_UPLOAD_BYTES`), 기동 시 share 디렉터리 보장
- [ ] **2. 인증/세션** — 로그인/로그아웃 페이지, 쿠키 인증(프레임워크 기본, 암호화 쿠키), argon2 검증(`WEB_USERNAME`/`WEB_PASSWORD`), 슬라이딩 30일, 비밀번호 지문 대조 폐기(`OnValidatePrincipal`)
- [ ] **3. 파일 코어** — 업로드(디스크 스트리밍, sha256, private 고정 생성), 다운로드(`PhysicalFile` Range), 삭제(DB 행 먼저), htmx 업로드 진행률
- [ ] **4. 목록** — 제목·파일명 검색, 정렬(created_at/title/size × asc·desc), 페이지네이션, favorite 토글
- [ ] **5. 드롭 상세** — 메타 수정, publish(공개 전환), 드롭 비밀번호 설정/해제(argon2 + Data Protection 쿠키), 잠금 화면 메타 마스킹(401), slug 자동 생성(형용사+명사, 코드 내 배열)·커스텀 slug
- [ ] **6. 업로드 티켓** — 발급/목록/폐기 UI(코드 평문 표시, no-store), 게스트 업로드 페이지(없는 경로 404, 코드 10회 제한, 소진·만료 규칙, GET 무부작용, noindex/no-referrer, 진행률)
- [ ] **7. API 업로드** — `POST /api/upload`, `X-API-Key`(`TELEDROP_API_KEY`), private 고정, 공유 URL 반환
- [ ] **8. 배포** — Dockerfile(node 스테이지 없음), compose 갱신, GitHub Actions 교체, README 태그라인 수정

순서 의존: 7은 slug 생성(5) 뒤여야 한다. 6과 7은 서로 바꿔도 된다.

## 스테이지 루프

1. `/codex:rescue --fresh [--background] <지시문>` — 3·5·6·8은 background 권장
2. 백그라운드면 `/codex:status` → `/codex:result`
3. 검수: `dotnet build`·실행 + 설계 부합(위 공통 계약 위반 여부)
4. 리뷰: 5·6은 `/codex:adversarial-review`(접근 제어·티켓 규칙이 보안 전부), 나머지는 `/codex:review`
5. 수정은 같은 스레드로: `/codex:rescue --resume "<델타 지시>"`
6. 커밋 후 다음 스테이지
