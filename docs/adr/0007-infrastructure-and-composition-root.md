# ADR 0007 — implementation을 Infrastructure로 옮기고 실행 host를 composition root로 둔다

- 상태: 채택
- 날짜: 2026-09-24
- ADR 0005의 프로젝트 배치 결정을 대체한다. Core의 의존 방향과 최소 port 원칙은 유지한다.

`Teledrop.Core`는 Drop 규칙·use case·port를, `Teledrop.Infrastructure`는 HTTP·Razor·EF·파일·보안 implementation을, `Teledrop`은 설정 공급·조립·실행 순서를 소유한다. Infrastructure는 Core만 참조하고 실행 host는 둘을 참조한다. HTTP를 포함하는 adapter assembly를 Razor Class Library로 만들어 세 프로젝트 안에서 순수 composition root와 기존 기능별 locality를 함께 얻는다.

프로젝트 이동 자체가 module의 depth를 높이지는 않는다. 실제 마찰이 있던 저장 interface의 scope·추적 조건을 명시하고 SQLite와 fake adapter를 같은 command seam으로 검증한다. 파일 저장 module에는 저장·다운로드가 공유하는 Location 해석과 존재 확인을 모으고, HTTP Range 응답은 다운로드 adapter가 맡는다.

## 선택과 결과

- Infrastructure 안에서는 Auth / Drops / Api 기능별 구성을 유지한다. 단순 EF 조회도 내부 implementation으로 남겨 새 Core 읽기 port를 만들지 않는다.
- Web RCL을 네 번째 프로젝트로 두는 대안은 채택하지 않는다. 현재는 HTTP와 EF 사이의 직접 참조를 컴파일러로 금지하는 것보다 기능별 locality를 보존하는 이득이 크다.
- root에는 Core·Infrastructure 등록, 저장소 초기화, middleware·endpoint 순서가 보인다. SQLite 경로·migration 적용, 인증 callback과 보안 헤더의 구현은 Infrastructure가 담당한다.
- RCL 자산의 기본 경로를 `/`로 지정해 기존 URL을 보존한다. 실행 host의 identity·content root, DB schema·migration ID, cookie 보호 문자열과 환경변수도 유지한다.
- 범용 Repository, 별도 Unit of Work, Entity/DTO 복제와 use case별 interface는 도입하지 않는다. 도메인 용어는 변하지 않는다.
