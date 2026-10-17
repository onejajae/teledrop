# 검증

## GitHub Actions

`.github/workflows/ci.yml`은 `main` push, PR, 수동 실행에서 `global.json`의 .NET SDK로 Release 빌드, Chromium을 포함한 전체 테스트, 실행 host의 publish를 검증한다. `dotnet test Teledrop.slnx`로 세 테스트 프로젝트를 모두 실행한다. TRX 파일 이름은 자동 생성해 프로젝트 간 덮어쓰기를 피하고, `TestResults/*.trx`를 `test-results` artifact로 하루 보관한다.

이미지는 `main`에서만 빌드한다. `main`의 push·수동 실행이 검증을 통과하면 현재 Dockerfile로 `linux/amd64`, `linux/arm64` 이미지를 빌드해 `ghcr.io/onejajae/teledrop:latest`와 `:sha-<commit>` 태그로 게시한다. SDK 단계는 러너 아키텍처에서 대상 아키텍처용으로 publish하고 런타임 단계는 파일 복사만 하므로 QEMU를 쓰지 않는다. PR은 Dockerfile을 빌드하지 않으므로 Dockerfile 변경은 `main`에 들어간 뒤에 검증된다.

CSS는 저장소에 커밋된 산출물을 사용한다. CI는 빌드 전에 `npm ci`로 htmx, PDF.js, Pretendard를 복사하고, Node.js를 Playwright Chromium 설치에도 쓴다. CSS는 다시 생성하지 않는다.

Tailwind CLI 4.3.3이 고정한 `@parcel/watcher` 2.5.1은 취약한 `braces`를 간접 참조하므로, `package.json`에서 CLI에 한정해 watcher 2.6.0을 override한다. Tailwind CLI 업데이트 시 이 override의 필요성을 다시 확인하고, 변경 후 CSS 빌드·watch와 `npm audit`를 검증한다.

## 테스트 프로젝트

테스트가 실행하는 범위와 필요한 의존성에 따라 세 프로젝트로 나눈다.

| 프로젝트 | 검증 범위 | 프로덕션 참조 |
|---|---|---|
| `Teledrop.Core.Tests` | `DropAccessPolicyTests`, `DropUseCaseTests`, `DropSlugsTests`의 순수 규칙·use case | Core |
| `Teledrop.Infrastructure.Tests` | 저장소·파일·목록 조회·design-time DB 설정·비밀번호 hash·미리보기·아이콘·번역의 계약 검증 | Core, Infrastructure |
| `Teledrop.Tests` | 실제 앱의 HTTP·인증·Razor·정적 자산·CLI·브라우저 통합 검증 | Core, Infrastructure, Teledrop host |

Core 테스트는 ASP.NET Core·EF Core·Playwright를 참조하지 않는다. Infrastructure 테스트는 실제 임시 SQLite와 파일을 사용할 수 있지만 실행 host와 Playwright를 참조하지 않는다. `Microsoft.AspNetCore.Mvc.Testing`과 `Microsoft.Playwright`, 브라우저 검증용 PDF·영상은 `Teledrop.Tests`에만 둔다.

`DropAccessModuleTests`와 `UploadReceiverTests`는 module을 직접 호출하는 검사도 포함하지만 실제 host의 설정·DI를 사용하므로 `Teledrop.Tests`에 둔다. `TeledropWebApplicationFactory`, `HttpTestSupport`, content root 설정도 이 프로젝트가 소유한다.

세 프로젝트의 공통 빌드·xUnit 설정은 `tests/Directory.Build.props`에서 관리한다. `tests/Shared/FakeDropStore.cs`는 Core 테스트와 Infrastructure의 저장소 계약 테스트에서 같은 원본을 링크해 컴파일한다. 테스트 프로젝트끼리는 참조하지 않으며, fake와 SQLite adapter의 계약 검증은 `DropStoreContractTests`에 함께 유지한다.

## 테스트 유지 기준

테스트 수나 줄 커버리지보다 **어떤 정책의 잘못된 변경을 막는가**를 기준으로 유지한다. 정책의 결정표·상태 전이는 해당 module의 interface에서 한 번 검증하고, HTTP·브라우저는 그 결과가 실제 저장·응답·화면으로 이어지는지 확인한다. 각 계층에 같은 입력표를 복제하지 않는다.

| 정책·계약 | 주 검증 위치 | 통합 검증에서 남기는 책임 |
|---|---|---|
| Owner·private·public·비밀번호·grant 접근 결정 | Core `DropAccessPolicyTests` | 실제 인증, 메타데이터 은폐, 쿠키 수명·격리 |
| 공개 수준 3×3 전이, 새 비밀번호 필수, 원문 전달, 동일 상태의 무저장 | Core `DropUseCaseTests` | 실제 비밀번호 설정→익명 Unlock, SQLite의 공개 여부·hash 동시 저장 |
| Metadata·Favorite·수정 시각, 없는 Drop 처리 | Core `DropUseCaseTests` | 요청 바인딩·응답 형식·CSRF |
| Slug 정규화·예약어·경계·충돌 재시도·취소 | Core `DropSlugsTests` | 저장소 충돌 계약, 폼 오류·재시도와 Slug 재사용 시 원본 식별 |
| DB 삭제 성공 뒤 정확한 Location 정리, 실패 시 파일 보존 | Core `DropUseCaseTests` | 실제 파일 삭제·다른 파일 보존·누락 파일 허용 |
| scope·보류 변경·실패 원자성·다른 요청과의 경쟁 | Infrastructure `DropStoreContractTests` | fake와 SQLite에 같은 계약 적용 |
| MIME의 미리보기·inline 허용 | Infrastructure `DropPreviewPolicyTests` | 각 렌더 경로, SVG·HTML 강제 다운로드와 보안 헤더 |
| API Key·Drop grant·Owner 권한 분리 | HTTP `CredentialScopeTests`, `ApiUploadTests` | 실제 자격 증명·유효한 CSRF로 거부와 DB·파일 불변 확인 |
| 업로드 입력·한도·소유권과 실패 정리 | Infrastructure 파일 저장 + HTTP 수신·Kestrel 테스트 | 실제 요청 크기 제한과 부분·완료 파일 정리 |
| 응답 유실·순서 역전·초안 보존·PDF 실패 복구 | 브라우저 회귀 테스트 | 실제 DOM·요청 순서·미디어·포커스와 재시도 |

정상·거부·경계·상태 전이가 서로 다른 정책이면 표의 독립 행으로 남긴다. 같은 결과의 확장자 별칭, 같은 바인딩 실패를 만드는 입력, 표시 형식의 언어 조합, 동일한 일반 오류 경로는 대표값으로 줄인다. 실행 수를 낮추려고 여러 독립 테스트를 큰 `Fact`나 숨은 반복문으로 묶지 않는다. `Theory`의 입력 행도 실행 수에 포함되므로 수치만으로 중복이나 품질을 판단하지 않는다.

보안·데이터 손실·실제 버그 회귀는 별도 보호 대상이다. 중복을 통합할 때도 비밀번호 비노출, 위험한 MIME의 다운로드 헤더, 파일 hash·bytes 같은 고유 assertion은 남는 테스트로 옮긴다. 정리 후 전체 테스트를 실행하고, 정책 공백을 보완할 때는 해당 규칙을 일부러 잘못 바꾼 격리 사본에서 테스트가 실패하는지도 확인할 수 있다. 검증을 위해 실제 작업 소스나 개발 데이터를 변조하지 않는다.

## 로컬 검증

저장소 루트에서 실행한다.

```sh
npm --prefix src/Teledrop.Infrastructure ci
dotnet build Teledrop.slnx
node tests/Teledrop.Tests/bin/Debug/net10.0/.playwright/package/cli.js install chromium
dotnet test Teledrop.slnx --no-build
```

Playwright 패키지를 업데이트하면 해당 버전의 Chromium을 다시 설치한다. Linux에서 브라우저 시스템 라이브러리가 필요하면 Playwright의 `install --with-deps chromium`을 사용한다.

대화형 암호 생성 검증은 macOS와 Linux의 `script`, `stty` 명령으로 독립 가상 터미널을 만든다. Linux에서는 util-linux의 `script`를 사용한다. 실제 사용자 터미널이나 입력을 읽지 않으며, Windows에서는 이 대화형 테스트만 명시적으로 건너뛴다. 표준 입력 모드와 나머지 테스트는 별도로 실행된다.

앱 서버·브라우저 없이 Core 또는 Infrastructure만 검사하려면:

```sh
dotnet test tests/Teledrop.Core.Tests
dotnet test tests/Teledrop.Infrastructure.Tests
```

HTTP·CLI를 포함하고 브라우저 검사만 제외하려면:

```sh
dotnet test Teledrop.slnx --filter 'FullyQualifiedName!~DropBrowserTests'
```

`DropBrowserTests`는 `WebApplicationFactory.UseKestrel(0)`으로 임의 포트에 독립 서버를 띄운다. 각 테스트는 임시 SQLite와 저장 디렉터리, 별도 브라우저 컨텍스트를 사용하며 현재 개발 서버의 Drop은 읽거나 수정하지 않는다.

브라우저 검증에는 미디어 node·재생 유지, 목록 조건, dialog 재시도, 낙관적 즐겨찾기와 응답 유실, 요청 순서 역전, Slug·삭제의 저장 대기, 공유 잠금 해제, 업로드 후 이동과 Session 만료를 포함한다. 각 테스트는 실제 로드된 `htmx.version`이 `4.0.0`인지 확인한다. 업로드는 413 거부·네트워크 실패 뒤 오류 표시와 재시도를 검증하며, CSP는 실제 애플리케이션 설정 그대로 사용한다.

htmx의 제거된 속성·이벤트와 상속 패턴은 설치된 4.0.0 패키지의 공식 검사기로 확인한다. `npm --prefix src/Teledrop.Infrastructure ci` 후 다음 명령을 실행한다. Razor 파일을 포함하도록 `.cshtml`을 추가하고, vendor 파일 대신 애플리케이션 템플릿과 스크립트만 검사한다. 이 정적 검사는 위 브라우저 검증과 함께 사용한다.

```sh
node src/Teledrop.Infrastructure/node_modules/htmx.org/dist/scripts/upgrade-check.js \
  --no-color --ext .cshtml \
  src/Teledrop.Infrastructure/Pages \
  src/Teledrop.Infrastructure/wwwroot/js/i18n.js \
  src/Teledrop.Infrastructure/wwwroot/js/site.js \
  src/Teledrop.Infrastructure/wwwroot/js/drop-list.js \
  src/Teledrop.Infrastructure/wwwroot/js/drop-interactions.js \
  src/Teledrop.Infrastructure/wwwroot/js/pdf-preview.js
```

`tests/Teledrop.Tests/Fixtures/preview.webm`은 FFmpeg `testsrc=size=160x90:rate=10`으로 생성한 8초 VP8 무음 영상이다. 다운로드한 사용자 미디어를 포함하지 않는다.

`Fixtures/preview.pdf`는 이 저장소의 검증용으로 직접 만든 2페이지 PDF다. Helvetica 텍스트와 파란색·빨간색 사각형만 포함하며 외부 문서나 사용자 자료를 사용하지 않는다. 브라우저 검증은 MIME 매개변수가 붙어도 canvas가 표시되고 페이지를 오갈 수 있는지, 잠금 해제 후 같은 문서 안에서 PDF가 초기화되는지 확인한다.

`Fixtures/single-page.pdf`는 첫 페이지 렌더 검증용으로 직접 만든 1페이지 PDF다. `PdfInitialFailureBrowserTests`는 정상 단일 페이지와 단일·복수 페이지의 최초 canvas 실패를 비교한다. 아직 성공한 페이지가 없으면 이동 버튼을 비활성화하고, 오류 안내·다운로드 초점과 원본 파일 다운로드를 유지해야 한다.

`UploadReceiverTests`는 두 HTTP 경로의 입력 제한·인증 순서와 공통 수신 module의 취소·실패 정리를 검증한다. 파일 앞뒤의 금지 필드, 복수 파일, 잘린 multipart, 크기 제한, 저장 중·저장 후 취소, DB 인계 후 실패를 다룬다. 실패한 요청 뒤에는 임시 저장 경로와 DB를 함께 검사한다.

파일명은 `filename*`의 우선순위와 클라이언트 경로 제거를 확인하고, 수신을 시작하기 전 이미 취소된 요청도 DB·파일을 남기지 않는지 검사한다.

`UploadRequestLimitTests`는 실제 Kestrel과 일반 오류 처리기가 활성화된 `Testing` 환경에서 웹·단축어의 본문 한도를 검증한다. factory의 `maxUploadBytes` 설정을 `IConfiguration`으로 공급해 Kestrel과 파일 저장이 같은 한도를 읽게 한다. 동적 HTTP 주소의 client는 redirect를 따르지 않으며 실제 Owner 로그인·CSRF 또는 API Key를 사용한다. 웹·단축어의 Content-Length와 chunked 전송, 단축어의 파일 뒤 큰 메타데이터 구성을 보내 빈 본문 413과 Drop·파일 부재를 확인한다. 정상 업로드 대조군도 같은 설정으로 검증한다.

Kestrel은 chunked 입력도 미리 읽을 수 있으므로 위 HTTP 검증은 정확한 저장 실패 시점을 보장하지 않는다. 부분 파일·완료 파일 정리는 `UploadReceiverTests`가 제어 가능한 입력 stream으로 해당 단계에 도달했음을 확인한 뒤 413을 발생시켜 검증한다. 원본 예외 보존과 다른 HTTP 오류·취소 상태의 예외가 용량 초과로 바뀌지 않는지도 확인한다. 기존 브라우저의 모의 413 검증은 화면 안내와 재시도를 계속 담당한다.


## HTTP 테스트 준비

`HttpTestSupport`는 HTTP 테스트들의 client 생성, 정상 Owner 로그인, antiforgery 추출, Drop·파일 준비를 공유한다. HTTPS localhost와 redirect 비추적, 실제 cookie·로그인·SQLite를 사용한다. HTML에서 이미 받은 token을 추출할 수 있고 `name`·`value` 속성 순서는 가정하지 않는다. 로그인 실패·잘못된 CSRF·cookie 변조·multipart 입력과 assertion은 각 테스트에 남긴다.

`SeedDropAsync`는 실제 바이트의 크기와 SHA-256을 계산하고 새 Location에 파일과 행을 준비한다. `fileBytes: null`은 물리 파일 없는 행이며 빈 배열은 실제 빈 파일이다. 정상 기본값 이후 `configure`에서 테스트별 MIME·설명·공개 여부 등을 설정할 수 있다. 반환된 Drop의 준비 scope는 닫혀 있으므로 이후 상태 변경은 새 scope나 실제 HTTP로 수행한다.

모든 helper는 넘겨받은 `WebApplicationFactory<Program>`의 client·Services·저장 경로를 사용한다. `UploadReceiverTests`의 `WithWebHostBuilder` 설정이 적용된 host를 그대로 전달하며, 별도 factory를 몰래 시작하지 않는다. `FileHttpTests`는 파생 host의 변경된 저장 경로에서도 준비한 파일을 실제 다운로드할 수 있는지 확인한다. factory·client의 수명, Playwright 조작과 host 시작 전 기존 DB 준비는 원래 테스트가 소유한다.

## 로그인·설정·오류 처리

`AuthenticationTests`는 잘못된 비밀번호뿐 아니라 username 불일치·대소문자, 필수 입력 누락, 실패 응답의 비밀번호 제거, 외부 ReturnUrl 거부, 로그인 CSRF와 fingerprint가 없거나 잘못된 Session의 거부·쿠키 삭제를 검증한다.

Owner Session 수명은 고정된 `TimeProvider`와 실제 발행된 인증 쿠키로 검증한다. 최초 30일 만료, 정확히 15일에서는 재발행 없음, 15일이 지난 요청에서 새 30일 만료, 이전 쿠키와 갱신 쿠키의 독립적인 만료를 확인한다. 쿠키 교체를 명시적으로 제어하므로 자동 갱신 때문에 이전 쿠키의 만료 검사가 우회되지 않는다.

`StartupValidationTests`는 필수 설정 누락·잘못된 암호 형식·0 이하 업로드 한도가 저장소 생성 전에 시작을 막는지 확인한다. `ErrorHandlingTests`는 Production 환경의 실제 DB 조회·저장 실패와 DB 전체 장애를 주입해 오류 미들웨어의 500 응답, 영어·한국어 화면, Request ID, 캐시 방지와 내부 오류 정보 비노출을 검증한다. Activity가 없을 때 HTTP trace identifier를 사용하는 것도 확인한다.

익명 GET의 오류 화면은 영어·한국어를 확인하고, Owner의 DB 전체 장애·POST 실패는 한국어 대표 사례로 언어와 `Content-Language`를 확인한다. 언어 미들웨어는 예외 처리보다 안쪽에서 실행해 `/Error` 재실행에도 응답 언어 헤더를 적용한다.

Owner의 오류 화면도 목록을 추가 조회하지 않아 DB 전체 장애에 영향을 받지 않아야 한다. 오류 페이지의 Request ID는 GET뿐 아니라 기존 HTTP 메서드와 handler query가 유지되는 POST 재실행에서도 설정한다. 정상 CSRF를 가진 저장 요청의 실패 뒤에는 기존 DB 값도 보존되는지 확인한다.

`HashPasswordCommandTests`는 별도 프로세스에서 표준 입력 모드·도움말을 검증한다. `InteractiveHashPasswordTests`는 프롬프트를 받은 뒤 가상 터미널에 키를 보내 숨김 입력, Backspace, 확인 불일치, Escape와 빈 입력을 확인한다. 임의 대기 대신 프롬프트와 프로세스 종료를 기다리며 시간 제한을 넘기면 해당 자식 프로세스를 정리한다. `HashPasswordInputFailureTests`의 입력 오류 검증은 Console을 바꾸므로 별도 비병렬 collection에서 실행하고 원래 스트림을 복원한다.

`SecurityHeadersTests`는 서로 다른 응답의 CSP nonce가 달라지고 각 응답의 모든 inline script nonce가 헤더와 일치하는지 검사한다. `RenderingSafetyTests`는 파일명·설명의 HTML 특수문자가 Owner·Share Link·목록 fragment에서 텍스트로 인코딩되는지 확인한다.

## 비밀번호 해시 호환성

비밀번호 생성·검증은 Infrastructure의 `PasswordHash`가 Geralt와 네이티브 libsodium으로 처리한다. `PasswordHashTests`는 이전 Isopoh 구현으로 생성한 `p=1`·`p=4` 해시, UTF-8 비밀번호, 잘못된 비밀번호와 깨진 해시를 검증한다. `HashPasswordCommandTests`는 새 해시의 비용(`m=65536,t=3,p=1`)·salt와 이전 구현에서의 검증을 확인한다. Isopoh 패키지는 기존 해시와의 호환성을 검증하기 위해 테스트 프로젝트에만 유지한다.

## 미리보기와 Owner 변경 경로

Infrastructure의 `DropPreviewPolicyTests`는 판단 interface의 MIME 표를 검증하고, 통합 검증의 `DropPreviewTests`는 실제 상세·Share Link HTML과 다운로드 disposition이 일치하는지 확인한다. PDF 매개변수·대소문자, 이미지·영상·음성, plain text, SVG·HTML·기타 타입과 파일명 불일치를 포함한다. 저장된 MIME 매개변수가 그대로 전달되고 Range 응답이 동작하는지 확인하며, 잘못된 MIME의 HTTP 검증은 HTML의 미리보기 부재만 확인한다.

`UiRegressionTests`는 실제 Owner Session과 유효한 CSRF로 Index에 Favorite·Delete handler POST를 일반·HTMX 요청으로 보내 404와 행·파일 불변을 확인한다. 홈이 업로드 폼, `deleted` 안내, 목록을 표시하고 Logout이 동작하는지도 확인한다. 물리 파일 없는 Drop 삭제 검증은 상세 Delete 경로를 호출한다.

`DropDetailFailureTests`는 관리 화면을 연 뒤 Drop이 삭제된 경우 조회·state·변경 handler의 일반/HTMX 404와 다른 Drop의 불변을 확인한다. 잘못된 Favorite 값의 거부와 페이지 번호 파싱 실패도 포함한다.

`MutationRecoveryBrowserTests`는 Access·Slug·Delete의 전송 실패/500과 서버 저장 뒤 응답 유실을 구분해 검증한다. 결과를 알 수 없는 변경은 쓰기 요청을 자동 재전송하지 않고 Owner 전용 `RecoveryState`로 원래 Drop ID를 조회한다. 공개 범위·공유 안내를 갱신하되 대화상자의 입력과 미디어를 보존하고, Slug 변경·삭제가 완료됐다면 현재 위치로 이동한다. 이전 Slug를 다른 Drop이 재사용해도 그 Drop을 오인하거나 변경하면 안 된다. 복구 조회 자체가 실패한 뒤 목록 새로고침은 조회만 다시 시도한다.

`MutationRecoveryHttpTests`는 위 복구 조회의 Owner 인증, 잘못된 ID 거부, 캐시 방지, Slug 재사용 이후 원본 식별과 DB·파일 불변을 검사한다.

복구 조회까지 실패하면 원본의 상태를 확인할 때까지 쓰기 폼과 대기 중인 변경 요청을 잠근다. 조회 재시도와 대화상자 닫기는 허용하며, 조회가 성공한 뒤에만 대기 작업을 계속한다. Slug 재사용과 조회 실패가 겹쳐도 대체 Drop을 변경하지 않는지, 복구로 교체된 공개 범위 버튼에 키보드 초점이 돌아오는지도 검증한다.

`RecoveryOrderingBrowserTests`는 SharedState 응답이 지연된 동안 FavoriteState와 RecoveryState가 필요해지는 순서를 고정한다. 이미 진행·대기 중인 즐겨찾기 조회가 끝난 뒤 복구 조회를 보내 htmx 대기열에서 요청이 누락되지 않는지, 이후 쓰기 잠금이 풀리고 초안·영상 재생이 유지되는지 확인한다.

`FailureRecoveryBrowserTests`는 실제 DataTransfer 드롭·선택 미리보기, 설명 저장·목록·공개 Unlock의 요청 실패 뒤 초안·화면 보존과 재시도, PDF 로드·렌더 실패와 다운로드 대체 동작을 검증한다. 공유 상태 조회 실패 후에는 안내대로 목록 새로고침을 눌러 공유 상태도 다시 읽고 URL 초안을 보존해야 한다. 상대 날짜는 고정된 브라우저 시계로, 파일 크기는 단위 경계값으로 양쪽 언어의 실제 표시를 확인한다.

PDF 페이지 전환 중 렌더 실패는 실제 PDF.js와 canvas를 사용해 재현한다. 실패한 render task를 취소해 캔버스 점유를 해제한 뒤 같은 대상 페이지를 다시 그릴 수 있어야 한다. 최초 표시 자체가 실패한 경우의 안내와 다운로드는 별도 로드 실패 검증에서 확인한다.

## Drop 접근 module

`DropAccessModuleTests`는 production `DropAccess` interface로 조회·잠금 해제의 거부 결과에 Drop 데이터가 없고 grant도 발행되지 않는지 확인한다. 실제 임시 SQLite와 production cookie implementation을 사용하며 Core 조회 port나 mock adapter를 추가하지 않는다.

`DropAccessTests`는 페이지·다운로드·Unlock POST를 실제 HTTP로 검증한다. 메타데이터 은폐, Drop 간 grant 격리, Drop Password 변경 무효화, 없는 Drop의 Owner/비인증 차이, Owner의 Drop Password 우회, private 전환 시 Drop Password 삭제와 기존 grant 거부, 같은 비밀번호로 다시 공개해도 새 잠금 해제가 필요한 것, 잘못된 Unlock POST 뒤 기존 grant 유지, 변조·잘못된 cookie와 antiforgery를 검사한다. Slug 변경과 원래 Slug 복원에 따른 기존 grant의 동작도 고정한다.

`DropAccessLevelTests`는 private이면서 비밀번호가 있는 행을 DB가 거부하는지, `Access` handler가 모르는 공개 범위를 400으로 거부하는지 확인한다. 공개 범위 전환 규칙은 `DropUseCaseTests`가 fake store로 검증한다.

`CredentialScopeTests`는 유효한 API Key와 실제 Unlock으로 발급받은 grant가 Owner 관리 권한이 되지 않는지 확인한다. grant는 해당 보호 파일만 읽고 private Drop은 읽지 못한다. Metadata·Access·Favorite·Slug·Delete 각각에 유효한 익명 CSRF를 보내 로그인 요구와 DB 전체 값·파일 bytes 불변을 확인한다. Owner Session만으로 API 업로드할 수 없다는 반대 방향은 `ApiUploadTests`가 맡는다.

비밀번호 설정과 잠금 해제의 연결은 실제 Owner HTTP 요청으로 새 Drop Password를 설정한 뒤 익명 client로 오답 거부·정답 성공을 확인한다. Slug나 Drop이 달라진 뒤 쿠키 이름만 바꿔 같은 보호 값을 보내도 거부되는지, 잠금·정상·오답의 전체 화면과 HTMX 응답이 `no-store`인지도 검증한다. `ApiUploadTests`는 유효한 값을 포함한 중복 API Key 헤더도 거부하고 기존 DB·파일을 보존하는지 확인한다.

`Argon2DropPasswordHasherTests`는 공백·유니코드를 포함한 원래 비밀번호가 검증되고 다른 입력은 거부되는지, 같은 입력에도 서로 다른 salt가 적용되는지 확인한다.

시간 검증은 테스트 host의 `TimeProvider`를 바꿔 만료 직전·정각·이후를 기다리지 않고 확인한다. GET은 만료를 연장하지 않고 올바른 Drop Password를 다시 제출한 POST만 갱신해야 한다. HTTP 상태·cookie flags·일반/HTMX 화면과 Range 다운로드도 함께 검증한다.

## 저장과 파일 module

`DropIdMigrationTests`는 이전 데이터 이관에서 남은 소문자 GUID를 초기 migration DB에 준비한 뒤 최신 migration을 적용한다. 파일·공개 범위·비밀번호 해시와 논리적 ID를 유지하면서 기존 Drop의 비밀번호 해제와 삭제가 가능한지 검증한다. 대소문자만 다른 중복 ID가 있으면 어느 Drop도 버리지 않고 migration 전체가 실패해야 한다.

`DropStoreContractTests`는 실제 임시 SQLite와 fake adapter를 같은 `IDropCommandStore` seam으로 검증한다. 저장 전 변경의 비영속성, 저장 후 새 scope에서의 조회, 미추적·다른 scope·삭제된 객체의 거부, 서로 다른 scope가 변경한 필드의 보존을 검사한다. EF adapter의 삽입·삭제 대기 상태도 별도로 검증한다.

다른 scope가 삭제한 행을 추적 중이어도 그 행을 바꾸지 않았다면 관계없는 저장은 성공해야 한다. 삭제된 행을 수정했다면 함께 보류 중인 다른 변경도 저장되면 안 된다. 공개 범위 저장이 다른 Slug 충돌 때문에 실패할 때도 기존 공개 여부·hash 조합이 보존되는지 fake와 SQLite에 같은 사례를 실행한다.

공개 범위 경쟁 검증은 두 scope가 같은 public Drop을 먼저 읽은 뒤 실제 `DropUseCases.SetAccessAsync`를 호출한다. private·비밀번호 공개의 두 저장 순서를 고정해 마지막 저장의 공개 여부·Drop Password 조합이 남고, 앞선 설명·Favorite 변경은 보존되는지 SQLite와 fake 양쪽에서 확인한다. 공개 범위 저장에도 기존 추적 객체 요구 조건을 검증한다.

Slug 저장 계약은 생성·변경 충돌과 실패 후 같은 scope의 재사용을 함께 검사한다. 실패한 신규 Drop이 다음 저장에 다시 나타나지 않는지, Slug 변경 실패가 기존 수정 시각과 같은 Drop·다른 Drop의 미저장 변경을 보존하는지 확인한다. 두 scope가 저장 전에 같은 후보를 선택하도록 순서를 고정해 스케줄링에 의존하지 않고 경쟁을 검증한다. 중복 ID, 다른 Drop의 대기 변경에서 난 충돌, SQLite의 다른 고유성 제약은 대상 Slug 충돌로 바뀌면 안 된다.

`DropSlugsTests`는 module의 두 진입점으로 생성·직접 변경을 검증한다. 테스트 adapter가 앞선 저장 시도에 충돌을 돌려줘 단어 후보 12개 이후 suffix 전환, 최대 24개 소진, 성공·다른 오류·취소의 종료 조건을 확인한다. 시도 사이에 Drop ID·CreatedAt·파일이 유지되고 최종 실패에서만 정리되는지 검사하며, 성공한 저장 뒤의 취소는 파일을 지우지 않아야 한다. 난수 값 자체를 고정하는 production interface는 추가하지 않는다.

Core 검증은 Slug의 1·64·65자 경계, 예약어와 잘못된 문자, 없는 Drop에 대한 명령, Favorite의 해제·같은 값 재설정, 알 수 없는 접근 수준을 포함한다. 저장 호출까지 취소 token이 전달되는지, 저장 대기 중 취소와 일반 오류가 그대로 전파되는지도 검증한다.

접근 결정은 정상 세 공개 수준 × Owner 여부 × grant 여부의 표로 고정한다. 공개 범위 전이 9개는 기대 공개 여부·hash·수정 시각을 명시한다. 같은 Private/Public 상태 요청은 기존 수정 시각과 미저장 변경을 그대로 두며, 비밀번호 공개를 요청하면 출발 상태와 관계없이 새 비밀번호가 필요하다. null·빈 입력을 거부할 때 추적 객체·저장 상태·hash·수정 시각이 바뀌지 않아야 하고, 비밀번호 원문은 공백·유니코드까지 그대로 hasher에 전달해야 한다.

삭제는 DB 저장 성공 후 Slug와 다른 정확한 `Location`을 정리해야 한다. 저장 실패·취소 때는 정리가 호출되지 않고 원래 예외와 행이 보존되는지 확인한다. HTTP에서는 물리 파일의 정상 삭제와 이미 없는 파일을 함께 다루며, 삭제 대상 Slug를 Location으로 가진 다른 파일도 보존되는지 검사한다.

`UiRegressionTests`는 폼을 연 뒤 다른 요청이 원하는 Slug를 차지한 상황을 일반 요청·HTMX 양쪽에서 검증한다. 충돌 응답의 Share Link와 폼 대상은 원래 Slug를 유지하고, 같은 폼에서 다른 Slug로 재시도할 수 있어야 한다.

`DropFileStoreTests`는 실제 임시 디렉터리에서 저장·Location 해석·파일 읽기·삭제를 확인한다. 빈 파일, 정확한 용량 한계와 1바이트 초과, 입력 오류의 원본 예외 보존과 부분 파일 정리, 삭제 실패의 경고·예외 비전파도 검사한다. HTTP 검증은 누락 파일의 404와 접근 통제, Range 응답을 유지한다.

`DropListTests`는 SQLite에서 `%`, `_`, 역슬래시를 문자 그대로 검색하는지 확인한다. 세 정렬 기준의 양방향 순서, 동일 값의 ID 순서와 페이지 경계, 잘못된 조건의 기본값, 페이지 보정과 빈 결과를 고정된 기대 순서로 검증한다.

## RCL과 배포 산출물

EF 도구의 대상과 시작 프로젝트는 DbContext·design-time factory가 있는 Infrastructure로 지정한다. 실행 host에 EF Design 패키지를 추가할 필요가 없다.

`TeledropDbContextFactoryTests`는 환경변수 연결 문자열과 기본값을 확인하며 DB 연결을 열지 않는다. 환경변수 변경은 비병렬 collection으로 격리하고 원래 값을 복원한다.

```sh
dotnet ef migrations list --no-connect --project src/Teledrop.Infrastructure --startup-project src/Teledrop.Infrastructure
```

`StaticAssetTests`는 인증 없이 `/css`, `/js`, `/fonts`, `/static`, favicon URL과 Razor가 생성한 fingerprint CSS URL을 읽는다. 테스트는 `WebApplicationFactory<Program>`으로 실제 Teledrop host를 실행하며, RCL 페이지·partial은 이 host가 발견한다.

로그인 페이지의 `_FontFaces`가 네 가지 굵기의 fingerprint 글꼴 URL을 렌더링하는지 확인한다. 이 검증에서는 개발 환경의 정적 자산 캐시를 활성화해 각 응답의 1년 `max-age`, `immutable`, ETag와 조건부 요청의 304·빈 본문을 검사한다.

배포 변경 시에는 전체 테스트에 더해 Release publish와 컨테이너 이미지 build를 확인한다.

```sh
teledrop_publish_dir="$(mktemp -d)"
dotnet publish src/Teledrop -c Release -o "$teledrop_publish_dir"
docker build -t teledrop:architecture-check .
```

macOS의 Apple `container`에서는 같은 Dockerfile을 다음과 같이 빌드한다.

```sh
container build --platform linux/arm64 --progress plain -t teledrop:architecture-check .
```

실행 검증에는 테스트용 `WEB_USERNAME`, Argon2id 해시인 `WEB_PASSWORD`, `TELEDROP_API_KEY`를 담은 env 파일과 이미지의 `app` 사용자가 쓸 수 있는 임시 저장 디렉터리를 준비한다. 이미지 기본 진입점과 사용자를 그대로 사용한다.

```sh
container run --detach --name teledrop-check \
  --env-file /path/to/test.env \
  --publish 127.0.0.1:18080:8080 \
  --volume /path/to/test-share:/app/share \
  teledrop:architecture-check
container stop teledrop-check
container start teledrop-check
```

HTTP 검증과 재시작 검증이 끝나면 `container stop teledrop-check`와 `container delete teledrop-check`로 해당 테스트 컨테이너만 정리한다.

publish 결과는 별도 임시 DB·저장 디렉터리와 테스트용 Owner 설정으로 실행한다. 로그인 페이지·Drop 상세·공유 화면, CSS·JavaScript·글꼴·아이콘과 fingerprint URL이 정상 응답하는지 확인한다. 같은 DB와 파일로 프로세스를 다시 시작해 기존 Drop을 읽고 Range 다운로드가 되는지도 확인한다. 현재 개발 데이터는 이 검증에 사용하지 않는다.


## 다국어와 접근성

기존 HTTP UI 테스트의 기본 언어는 `HttpTestSupport.CreateClient`에서 `ko`를 명시하고, 브라우저 회귀 테스트는 `ko-KR` 컨텍스트로 실행한다. 기본값 자체를 확인하는 테스트는 `language: null`로 브라우저 언어 헤더를 생략한다.

Infrastructure의 `LocalizationResourceTests`는 번역 키·자리표시자 일치를 확인한다. 통합 검증의 `LocalizationTests`는 영어 기본값, 지역 코드, 브라우저 선호 순서(네 번째 이후 포함), 쿠키 우선순위·유효기간, CSRF, 잘못된 언어, 외부 복귀 주소 거부를 확인한다. `LocalizationBrowserTests`는 기존 `DropBrowserTests`의 독립 서버·DB를 공유하는 partial 테스트 모음이며 언어 전환 중 업로드·입력값·미디어·PDF 페이지 유지, 지연된 목록·저장 응답, 키보드 선택·취소, 저장 실패 재시도, 로그인·로그아웃, JavaScript 없는 폼, 320px 양쪽 테마를 검증한다.

화면 이미지를 확인할 때는 `TELEDROP_CAPTURE_UI=1`로 좁은 화면 테스트를 실행한다. 이미지는 시스템 임시 디렉터리의 `teledrop-language-{언어}-{테마}.png`에 저장되며 저장소에는 추가하지 않는다. 배포 검증에서는 Release publish 출력에 한국어 satellite resource assembly가 포함되고 로그인 화면이 `Accept-Language: ko-KR`로 한국어를 반환하는지도 확인한다.

`SelectMenuBrowserTests`는 정렬 메뉴의 키보드·포인터 선택(정렬 기준과 순서), 목록 교체 후 초점 유지, 좁은 화면 배치, 언어 메뉴와 한 번에 하나만 열리는 동작, JavaScript 없는 정렬 링크를 검증한다. `TELEDROP_CAPTURE_UI=1`을 지정하면 양쪽 언어·테마의 정렬 메뉴 이미지를 시스템 임시 디렉터리에 저장한다.

`LocalizationFormattingTests`는 파일 크기의 단위 경계와 culture, 번역의 기본 언어·없는 키 처리를 확인한다. `TranslationTagHelperTests`는 번역 대상 속성, 인자 JSON과 HTML 인코딩을 검증한다. `AppearanceBrowserTests`는 OS 테마와 저장된 선택의 우선순위, 실제 테마 버튼과 재방문, 공유 링크·hash 복사의 성공·클립보드 거부 시 선택 대체 동작을 확인한다. 복사 안내의 복귀 시간은 브라우저 시계를 진행해 검증한다.

`RequestOrderingBrowserTests`는 실제 목록 응답을 보류했다가 새 검색 응답 뒤에 반환해 결과·안내·포커스가 되돌아가지 않는지 확인한다. 별도로 변경 작업 전의 목록을 변경 응답보다 먼저 반환해, 새 목록 요청이 없어도 낙관적 즐겨찾기 상태가 보존되는지 검증한다.

`LanguageFailureBrowserTests`는 거부 응답 400·잘못된 성공 응답 200과 10초 시간 초과를 검증한다. 저장 중 중복 선택 차단, 오류 뒤 언어·초안 보존과 busy 해제, 재시도 이후 이전 응답 도착과 재방문까지 확인한다. 시간 초과는 브라우저 시계로 진행하며 응답 순서는 gate로 제어한다.
