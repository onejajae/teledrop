# 업무 규칙은 Core에, 구현은 Infrastructure에, 조립은 host에 둔다

프로덕션 프로젝트를 `Teledrop.Core`(Drop 규칙·use case·최소 port), `Teledrop.Infrastructure`(HTTP·Razor·EF Core·SQLite·파일·보안 구현을 담은 Razor Class Library), `Teledrop`(설정·조립·실행)으로 나눠, 업무 규칙이 ASP.NET Core와 EF Core에 기대지 못하게 컴파일러로 막는다. 프로젝트 안은 기능별 폴더로 모으고 MediatR, 범용 Repository·Unit of Work, Entity/DTO 복제, use case별 interface, 전역 레이어 폴더는 두지 않는다. 모두 혹시 몰라서 넣는 추상화이고, 구현이 하나뿐인 interface와 같은 모양의 DTO는 고칠 곳만 늘린다.

## 버린 안

- **단일 프로젝트 + 폴더 구분** — Core 코드가 `HttpContext`나 `DbContext`를 참조해도 막을 수 없다
- **Domain / Application / Infrastructure / Web 프로젝트** — 이 규모에 필요 없는 경계와 전달 코드를 만든다
- **HTTP를 별도 Web 프로젝트로 분리** — HTTP와 EF 사이 참조를 막는 것보다 기능 하나를 한 프로젝트에서 읽는 이득이 크다
