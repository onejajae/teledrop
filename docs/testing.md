# 검증

## GitHub Actions

`.github/workflows/ci.yml`은 `main` push, PR, 수동 실행에서 `global.json`의 .NET SDK로 Release 빌드, Chromium을 포함한 전체 테스트, 실행 host의 publish를 검증한다. 테스트 결과는 `test-results` artifact로 하루 보관한다.

이미지는 `main`에서만 빌드한다. `main`의 push·수동 실행이 검증을 통과하면 현재 Dockerfile로 `linux/amd64`, `linux/arm64` 이미지를 빌드해 `ghcr.io/onejajae/teledrop:latest`와 `:sha-<commit>` 태그로 게시한다. SDK 단계는 러너 아키텍처에서 대상 아키텍처용으로 publish하고 런타임 단계는 파일 복사만 하므로 QEMU를 쓰지 않는다. PR은 Dockerfile을 빌드하지 않으므로 Dockerfile 변경은 `main`에 들어간 뒤에 검증된다.

CSS는 저장소에 커밋된 산출물을 사용한다. CI는 빌드 전에 `npm ci`로 htmx, PDF.js, Pretendard를 복사하고, Node.js를 Playwright Chromium 설치에도 쓴다. CSS는 다시 생성하지 않는다.

## 로컬 검증

저장소 루트에서 실행한다.

```sh
dotnet build tests/Teledrop.Tests
node tests/Teledrop.Tests/bin/Debug/net10.0/.playwright/package/cli.js install chromium
dotnet test tests/Teledrop.Tests --no-restore
```

Playwright 패키지를 업데이트하면 해당 버전의 Chromium을 다시 설치한다. Linux에서 브라우저 시스템 라이브러리가 필요하면 Playwright의 `install --with-deps chromium`을 사용한다.

빠른 HTTP/Core 검사만 실행하려면:

```sh
dotnet test tests/Teledrop.Tests --filter 'FullyQualifiedName!~DropBrowserTests'
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

`UploadReceiverTests`는 두 HTTP 경로의 입력 제한·인증 순서와 공통 수신 module의 취소·실패 정리를 검증한다. 파일 앞뒤의 금지 필드, 복수 파일, 잘린 multipart, 크기 제한, 저장 중·저장 후 취소, DB 인계 후 실패를 다룬다. 실패한 요청 뒤에는 임시 저장 경로와 DB를 함께 검사한다.

`UploadRequestLimitTests`는 실제 Kestrel과 일반 오류 처리기가 활성화된 `Testing` 환경에서 웹·단축어의 본문 한도를 검증한다. factory의 `maxUploadBytes` 설정을 `IConfiguration`으로 공급해 Kestrel과 파일 저장이 같은 한도를 읽게 한다. 동적 HTTP 주소의 client는 redirect를 따르지 않으며 실제 Owner 로그인·CSRF 또는 API Key를 사용한다. 웹·단축어의 Content-Length와 chunked 전송, 단축어의 파일 뒤 큰 메타데이터 구성을 보내 빈 본문 413과 Drop·파일 부재를 확인한다. 정상 업로드 대조군도 같은 설정으로 검증한다.

Kestrel은 chunked 입력도 미리 읽을 수 있으므로 위 HTTP 검증은 정확한 저장 실패 시점을 보장하지 않는다. 부분 파일·완료 파일 정리는 `UploadReceiverTests`가 제어 가능한 입력 stream으로 해당 단계에 도달했음을 확인한 뒤 413을 발생시켜 검증한다. 원본 예외 보존과 다른 HTTP 오류·취소 상태의 예외가 용량 초과로 바뀌지 않는지도 확인한다. 기존 브라우저의 모의 413 검증은 화면 안내와 재시도를 계속 담당한다.


## HTTP 테스트 준비

`HttpTestSupport`는 여섯 HTTP 테스트 묶음의 client 생성, 정상 Owner 로그인, antiforgery 추출, Drop·파일 준비를 공유한다. HTTPS localhost와 redirect 비추적, 실제 cookie·로그인·SQLite를 사용한다. HTML에서 이미 받은 token을 추출할 수 있고 `name`·`value` 속성 순서는 가정하지 않는다. 로그인 실패·잘못된 CSRF·cookie 변조·multipart 입력과 assertion은 각 테스트에 남긴다.

`SeedDropAsync`는 실제 바이트의 크기와 SHA-256을 계산하고 새 Location에 파일과 행을 준비한다. `fileBytes: null`은 물리 파일 없는 행이며 빈 배열은 실제 빈 파일이다. 정상 기본값 이후 `configure`에서 테스트별 MIME·설명·공개 여부 등을 설정할 수 있다. 반환된 Drop의 준비 scope는 닫혀 있으므로 이후 상태 변경은 새 scope나 실제 HTTP로 수행한다.

모든 helper는 넘겨받은 `WebApplicationFactory<Program>`의 client·Services·저장 경로를 사용한다. `UploadReceiverTests`의 `WithWebHostBuilder` 설정이 적용된 host를 그대로 전달하며, 별도 factory를 몰래 시작하지 않는다. `FileCoreTests`는 파생 host의 변경된 저장 경로에서도 준비한 파일을 실제 다운로드할 수 있는지 확인한다. factory·client의 수명, Playwright 조작과 host 시작 전 기존 DB 준비는 원래 테스트가 소유한다.

## 미리보기와 Owner 변경 경로

`DropPreviewTests`는 판단 interface의 MIME 표와 실제 상세·Share Link HTML, 다운로드 disposition을 함께 검증한다. PDF 매개변수·대소문자, 이미지·영상·음성, plain text, SVG·HTML·기타 타입과 파일명 불일치를 포함한다. 저장된 MIME 매개변수가 그대로 전달되고 Range 응답이 동작하는지 확인하며, 잘못된 MIME은 HTML의 미리보기 부재만 확인한다.

`UiRegressionTests`는 실제 Owner Session과 유효한 CSRF로 Index에 Favorite·Delete handler POST를 일반·HTMX 요청으로 보내 404와 행·파일 불변을 확인한다. 홈이 업로드 폼, `deleted` 안내, 목록을 표시하고 Logout이 동작하는지도 확인한다. 물리 파일 없는 Drop 삭제 검증은 상세 Delete 경로를 호출한다.

## Drop 접근 module

`DropAccessModuleTests`는 production `DropAccess` interface로 조회·잠금 해제의 거부 결과에 Drop 데이터가 없고 grant도 발행되지 않는지 확인한다. 실제 임시 SQLite와 production cookie implementation을 사용하며 Core 조회 port나 mock adapter를 추가하지 않는다.

`DropAccessTests`는 페이지·다운로드·Unlock POST를 실제 HTTP로 검증한다. 메타데이터 은폐, Drop 간 grant 격리, Drop Password 변경 무효화, 없는 Drop의 Owner/비인증 차이, Owner의 Drop Password 우회, private 전환 시 Drop Password 삭제와 기존 grant 거부, 같은 비밀번호로 다시 공개해도 새 잠금 해제가 필요한 것, 잘못된 Unlock POST 뒤 기존 grant 유지, 변조·잘못된 cookie와 antiforgery를 검사한다. Slug 변경과 원래 Slug 복원에 따른 기존 grant의 동작도 고정한다.

`DropAccessLevelTests`는 private이면서 비밀번호가 있는 행을 DB가 거부하는지, `Access` handler가 모르는 공개 범위를 400으로 거부하는지 확인한다. 공개 범위 전환 규칙은 `DropUseCaseTests`가 fake store로 검증한다.

시간 검증은 테스트 host의 `TimeProvider`를 바꿔 만료 직전·정각·이후를 기다리지 않고 확인한다. GET은 만료를 연장하지 않고 올바른 Drop Password를 다시 제출한 POST만 갱신해야 한다. HTTP 상태·cookie flags·일반/HTMX 화면과 Range 다운로드도 함께 검증한다.

## 저장과 파일 module

`DropStoreContractTests`는 실제 임시 SQLite와 fake adapter를 같은 `IDropCommandStore` seam으로 검증한다. 저장 전 변경의 비영속성, 저장 후 새 scope에서의 조회, 미추적·다른 scope·삭제된 객체의 거부, 서로 다른 scope가 변경한 필드의 보존을 검사한다. EF adapter의 삽입·삭제 대기 상태도 별도로 검증한다.

공개 범위 경쟁 검증은 두 scope가 같은 public Drop을 먼저 읽은 뒤 실제 `DropUseCases.SetAccessAsync`를 호출한다. private·비밀번호 공개의 두 저장 순서를 고정해 마지막 저장의 공개 여부·Drop Password 조합이 남고, 앞선 설명·Favorite 변경은 보존되는지 SQLite와 fake 양쪽에서 확인한다. 공개 범위 저장에도 기존 추적 객체 요구 조건을 검증한다.

Slug 저장 계약은 생성·변경 충돌과 실패 후 같은 scope의 재사용을 함께 검사한다. 실패한 신규 Drop이 다음 저장에 다시 나타나지 않는지, Slug 변경 실패가 기존 수정 시각과 같은 Drop·다른 Drop의 미저장 변경을 보존하는지 확인한다. 두 scope가 저장 전에 같은 후보를 선택하도록 순서를 고정해 스케줄링에 의존하지 않고 경쟁을 검증한다. 중복 ID, 다른 Drop의 대기 변경에서 난 충돌, SQLite의 다른 고유성 제약은 대상 Slug 충돌로 바뀌면 안 된다.

`DropSlugsTests`는 module의 두 진입점으로 생성·직접 변경을 검증한다. 테스트 adapter가 앞선 저장 시도에 충돌을 돌려줘 단어 후보 12개 이후 suffix 전환, 최대 24개 소진, 성공·다른 오류·취소의 종료 조건을 확인한다. 시도 사이에 Drop ID·CreatedAt·파일이 유지되고 최종 실패에서만 정리되는지 검사하며, 성공한 저장 뒤의 취소는 파일을 지우지 않아야 한다. 난수 값 자체를 고정하는 production interface는 추가하지 않는다.

`UiRegressionTests`는 폼을 연 뒤 다른 요청이 원하는 Slug를 차지한 상황을 일반 요청·HTMX 양쪽에서 검증한다. 충돌 응답의 Share Link와 폼 대상은 원래 Slug를 유지하고, 같은 폼에서 다른 Slug로 재시도할 수 있어야 한다.

`DropFileStoreTests`는 실제 임시 디렉터리에서 저장·Location 해석·파일 읽기·삭제를 확인한다. HTTP 검증은 누락 파일의 404와 접근 통제, Range 응답을 유지한다.

## RCL과 배포 산출물

EF 도구의 대상과 시작 프로젝트는 DbContext·design-time factory가 있는 Infrastructure로 지정한다. 실행 host에 EF Design 패키지를 추가할 필요가 없다.

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

`LocalizationTests`는 영어 기본값, 지역 코드, 브라우저 선호 순서(네 번째 이후 포함), 쿠키 우선순위·유효기간, CSRF, 잘못된 언어, 외부 복귀 주소 거부, 번역 키·자리표시자 일치를 확인한다. `LocalizationBrowserTests`는 기존 `DropBrowserTests`의 독립 서버·DB를 공유하는 partial 테스트 모음이며 언어 전환 중 업로드·입력값·미디어·PDF 페이지 유지, 지연된 목록·저장 응답, 키보드 선택·취소, 저장 실패 재시도, 로그인·로그아웃, JavaScript 없는 폼, 320px 양쪽 테마를 검증한다.

화면 이미지를 확인할 때는 `TELEDROP_CAPTURE_UI=1`로 좁은 화면 테스트를 실행한다. 이미지는 시스템 임시 디렉터리의 `teledrop-language-{언어}-{테마}.png`에 저장되며 저장소에는 추가하지 않는다. 배포 검증에서는 Release publish 출력에 한국어 satellite resource assembly가 포함되고 로그인 화면이 `Accept-Language: ko-KR`로 한국어를 반환하는지도 확인한다.

`SelectMenuBrowserTests`는 정렬 메뉴의 키보드·포인터 선택(정렬 기준과 순서), 목록 교체 후 초점 유지, 좁은 화면 배치, 언어 메뉴와 한 번에 하나만 열리는 동작, JavaScript 없는 정렬 링크를 검증한다. `TELEDROP_CAPTURE_UI=1`을 지정하면 양쪽 언어·테마의 정렬 메뉴 이미지를 시스템 임시 디렉터리에 저장한다.
