# teledrop — 제품 정의와 범위

> 2026-07-26 기획 재검토 결과. devel 브랜치의 리팩토링을 폐기하고 main을 기준점으로 다시 세운 설계다.
> 용어는 [CONTEXT.md](CONTEXT.md), 개별 결정의 배경은 [adr/](adr/), 이식하지 않기로 한 것들은 [not-porting-from-devel.md](not-porting-from-devel.md) 참고.

## 제품

자체 호스팅 서버에서 돌리는 **개인** 파일 공유 도구. 서버 주인 한 명이 쓴다.

**원래 구상은 instant cloud다.** 말 그대로 지금 당장 파일을 올려두고 바깥에서 꺼내 쓰는 것. 믿을 수 없는 환경에서 구글 드라이브나 드롭박스에 로그인하지 않아도 되게 하는 게 동기였다.

이 문장이 판단 기준이다. **올리고 쓰기까지의 마찰이 늘어나는 변경은 기본적으로 의심한다.** 단축어 경로(공유 시트 → 탭 한 번 → 링크가 클립보드에)가 이 제품의 이상적인 형태이고, 웹 업로드도 거기에 가까워야 한다.

업로드는 소유자의 웹 UI와 API 키 경로만 지원한다. 게스트 업로드는 범위에서 제외했다([ADR 0006](adr/0006-remove-guest-upload.md)).

## 범위

**한다**
- 파일 업로드 / 다운로드 / 삭제 / 메타데이터 수정
- 공유 링크
- iOS 단축어에서 API 키로 업로드

**안 한다**
- 사용자 계정, 회원가입, 소유권, 권한 위임 — **사용자는 언제나 한 명이다**
- 드롭 만료 / 자동 삭제
- 폴더, 컬렉션, 다중 파일 드롭
- 게스트 업로드 및 게스트용 관리 화면

## 접근 모델

드롭 하나는 **파일 하나**다. 컬렉션이 아니다.

| 상태 | 누가 볼 수 있나 | 방어 수단 |
|---|---|---|
| private (기본값) | 소유자만 | 로그인 |
| public | 누구나 | 없음 — **공개하기로 한 것** |
| public + 드롭 비밀번호 | 비밀번호를 아는 사람 | 비밀번호 |

**업로드와 공개는 분리된 단계다.** 모든 경로에서 드롭은 private으로 생기고, 공개는 드롭 상세 화면에서 파일을 보면서 따로 결정한다(publish). devel의 웹 플로우를 그대로 가져온 것이다. 되돌릴 수 없는 행위는 올리는 순간의 체크박스가 아니라 대상을 눈으로 확인한 뒤에 일어나야 한다.

**slug는 보안 부담을 지지 않는다.** private은 로그인이 막고, public은 애초에 공개고, 비밀번호 걸린 것은 비밀번호가 막는다. 따라서 slug를 열거해도 얻는 게 없고, 커스텀 slug를 써도 무방하며, 자동 생성 slug에 높은 엔트로피가 필요하지 않다.

이 전제가 성립하려면 **열거로 메타데이터도 새지 않아야 한다.** 잠긴 드롭에 대한 비인증 요청은 파일명·제목·크기 없이 401을 반환한다. (main의 현재 동작이며, 이식 시 보존할 것)

### 접근 절차

Infrastructure의 concrete `DropAccess` module이 Share Link 페이지·다운로드의 조회와 잠금 해제를 함께 맡는다. `ReadAsync`와 `UnlockAsync`가 Drop 조회, Owner 확인, Drop Password grant 검증·발행 순서를 숨기고, 허용된 결과에만 Drop 데이터를 담는다. Core의 `DropAccessPolicy`는 순수 접근 규칙을 유지한다. 각 HTTP adapter는 로그인 요구·404·잠금 화면·파일 응답을 표현한다.

- 없는 Drop은 비인증 요청에 로그인 요구, Owner에게 404를 반환한다. private Drop은 기존 grant나 올바른 Drop Password가 있어도 Owner 로그인이 필요하다.
- GET은 기존 grant를 인정하며 만료를 연장하지 않는다. Unlock POST는 기존 grant와 별개로 제출한 Drop Password를 검증한다. 틀린 입력은 401과 빈 입력 필드로 돌아가지만 기존 grant를 지우지 않는다. 올바른 입력만 새 grant를 발행한다. Owner와 Drop Password 없는 public Drop은 grant 발행 없이 통과한다.
- grant는 발행부터 정확히 1시간이며 만료 시각부터 거부한다. `DropUnlockCookie`는 주입받은 `TimeProvider`로 시간을 읽는다. cookie 이름·보호 목적 문자열·payload·flags는 유지한다.
- grant는 Slug와 Drop Password hash에 묶인다. Slug를 바꾸면 새 Share Link에는 기존 cookie가 적용되지 않으며, 만료 전에 원래 Slug로 되돌리고 hash도 같다면 기존 cookie가 다시 유효하다. 별도의 영구 폐기 상태는 두지 않는다.

## 인증 경로 — 정확히 둘

| 경로 | 누가 | 권한 | 수명 |
|---|---|---|---|
| 세션 쿠키 | 소유자, 웹 UI | 전체 | 로그인 동안 |
| API 키 | 소유자의 iOS 단축어 | 업로드 (**private 고정**) | 장기, 재사용 (환경변수) |

세션과 API 키는 권한 범위가 다르다. API 키는 업로드만 허용하며 조회·수정·삭제·공개는 소유자 세션으로 한다. API 키를 다른 사람에게 전달하는 업로드 수단으로 쓰지 않는다.

로그인은 환경변수 `WEB_USERNAME` / `WEB_PASSWORD`(argon2 해시)로 한다.

**세션은 ASP.NET Core 쿠키 인증의 기본값 그대로다** — 세션 전체가 암호화되어 쿠키에 담기고, 서버는 아무 상태도 두지 않는다. 이 문서는 원래 "서버 사이드 세션"이라 적었으나, 그 요구의 실체는 **클라이언트가 세션 수명 관리에 관여하지 않는 것**(main의 JWT-as-session 문제 제거)이고 암호화 쿠키가 그것을 이미 충족한다. 단일 사용자에게 세션 테이블과 `ITicketStore`는 혹시 몰라서 넣는 인프라다.

폐기도 테이블 없이 한다. 비밀번호 해시에서 파생한 지문을 세션에 넣고 요청마다 현재 값과 대조한다(`OnValidatePrincipal`). **`WEB_PASSWORD`를 바꾸면 모든 기기의 세션이 즉시 죽는다** — 기기를 잃어버렸을 때의 폐기 수단이 이것이다.

**세션은 슬라이딩 30일이다.** 접근할 때마다 갱신되고 30일 놀면 죽는다. "기억하기" 체크박스는 두지 않는다 — 동작이 하나면 고를 것이 없다. 길게 잡는 근거는 **teledrop에 로그인하는 것이 믿는 기기뿐**이라는 점이다. 낯선 PC에서는 로그인하지 않고 public 드롭이나 드롭 비밀번호로 파일에 접근한다.

## REST API

`POST /api/upload` **하나뿐이다.** multipart로 파일을 받고 JSON으로 URL을 반환한다. 인증은 `X-API-Key` 헤더, 키는 환경변수 `TELEDROP_API_KEY` 하나.

**업로드는 private 고정이다.** `public` 파라미터를 받지 않는다 — 공개는 되돌릴 수 없는 행위이므로 폰의 공유 시트 한 번으로 일어나는 경로를 만들지 않는다.

따라서 반환하는 URL은 **남에게 줄 수 있는 링크가 아니다.** 로그인해야 열리며, 용도는 내가 나중에 그 파일로 바로 찾아가는 것이다.

용도는 iOS 단축어다. 공유 시트 → 서버에 던져넣기. 그 외의 조회·삭제·수정은 웹 UI에서 하며, 단축어가 부르지 않는 엔드포인트를 인터넷에 열어두지 않는다.

## 기능

**있다**
- Range 다운로드 (이어받기, 동영상 시킹)
- 이미지·영상 미리보기
- title / description
- private 플래그
- 드롭 비밀번호
- 커스텀 slug
- 자동 생성 slug — 형용사 + 명사 조합. 단어 배열은 코드에 박아 넣는다(파일도 설정도 폴백도 없음)
- favorite
- 목록 정렬 (created_at / title / size × asc·desc) + 페이지네이션
- 제목·파일명 검색
- `file_hash` (SHA-256) — 지금은 읽는 곳이 없다. 나중에 CAS 최적화를 붙일 여지로 남긴다. 업로드 스트림을 어차피 통과시키므로, 나중에 전 파일을 다시 읽는 백필보다 싸다

**상한**
- 전역 파일당 최대 크기 하나. 웹 UI와 API 모두 요청 하나에 파일 하나만 받는다

## 업로드 수신

Infrastructure의 `DropUploadReceiver`가 multipart 판독부터 파일 저장과 비공개 Drop 생성까지 수행하고 완성된 Drop을 반환한다. `ReceiveWebAsync`와 `ReceiveApiAsync`는 공통 판독 루프를 사용하며, 각 handler는 인증과 HTTP 응답을 맡는다.

- 웹 `/upload`는 Owner Session을 요구한다. 첫 section의 CSRF 검증이 끝나기 전 파일을 열지 않는다. CSRF 값과 대소문자가 정확한 `File` 하나만 허용하며, 제목·내용을 포함한 다른 필드는 위치에 관계없이 400으로 거부한다. 제목·내용은 상세 화면에서 수정한다.
- 단축어 `/api/upload`는 본문 판독 전에 API Key를 확인한다. `file` 하나와 선택적 `title`·`description`을 대소문자 구분 없이 받는다. 빈 메타데이터는 null, 반복된 메타데이터는 마지막 값이 되며 알 수 없는 필드는 400이다. 응답의 `slug`, `url`, `fileName`, `sizeBytes` 형식은 유지한다.
- 입력 형식 오류는 공통 `InvalidUploadException`으로 전달해 handler에서 400으로 응답한다. multipart가 중간에 끝나는 경우도 입력 오류다. 파일 용량 초과는 413이며, 저장 장치·DB 오류와 취소는 입력 오류로 바꾸지 않는다.
- 기존 `FormOptions`, `MAX_UPLOAD_BYTES`, 64 KiB 스트리밍 버퍼, SHA-256 계산을 유지한다. `Request.Form` 버퍼링, 새 저장 형식, 재개·청크 업로드는 도입하지 않는다.

## 저장과 삭제

파일은 `share/` 플랫 디렉터리에 두고, 파일명은 업로드마다 새로 만든 uuid다. DB의 `location`이 그것을 가리킨다. main과 같다. 로컬 개발 데이터는 저장소 루트의 `.local/share/`, 컨테이너 데이터는 `/app/share/`에 둔다.

**`location`을 불투명 포인터로 유지한다.** 나중에 CAS(content-addressable storage)로 갈 때 스키마를 바꾸지 않고 거기 들어가는 값만 바꾸면 된다. 그때 필요한 것은 두 가지뿐이다 — `location`에 해시를 넣는 것, 삭제 시 `SELECT COUNT(*) FROM drops WHERE file_hash = ?`로 다른 드롭이 같은 blob을 쓰는지 확인하는 것. 별도 refcount 테이블은 필요 없다. 지금은 uuid라 파일과 드롭이 1:1이므로 그 확인도 불필요하다.

**삭제는 DB 행을 먼저 지우고 파일을 나중에 지운다.** main은 반대로 되어 있는데(`os.remove` → `delete_by_key`), 중간에 죽으면 행은 남고 파일이 없는 드롭이 생긴다. 목록에 보이는데 누르면 터지고 손으로 고쳐야 한다. 순서를 뒤집으면 중간에 죽었을 때 디스크에 고아 파일이 남을 뿐이고, 이는 보이지도 않고 아무것도 깨뜨리지 않는다. **깨진 상태와 낭비되는 상태 중에서는 낭비가 낫다.**

업로드 파일의 정리 책임은 단계별로 넘긴다.

1. 저장 중 실패하면 `DropFileStore`가 불완전한 파일을 정리한다.
2. 저장 뒤 나머지 multipart 검증이 실패하면 `DropUploadReceiver`가 파일을 정리한다.
3. `DropSlugs.CreatePrivateAsync`에 인계한 뒤 Slug 충돌은 파일을 유지한 채 재시도한다. 후보 소진·취소·다른 저장 오류로 생성이 최종 실패하면 파일을 한 번 정리한다.
4. 생성이 성공하면 파일을 유지한다.

정리 실패는 원래 예외를 가리지 않고 로그에 남긴다. 프로세스 강제 종료 등으로 정리 자체가 실행되지 못한 경우에는 고아 파일이 남을 수 있다.

### Slug 확정과 저장 계약

Core의 `DropSlugs` module이 비공개 Drop 생성과 직접 지정한 Slug 변경을 맡는다. `CreatePrivateAsync`는 저장된 Drop을 반환하고, `ChangeAsync`는 기존 Slug 변경 결과를 반환한다. 후보를 먼저 조회해서 확보되었다고 간주하지 않으며, 실제 저장 성공이 Slug 확정을 뜻한다.

- 자동 생성은 같은 Drop ID·CreatedAt·저장 파일을 유지하며 단어 조합 12개, suffix가 붙은 후보 12개 순서로 저장을 시도한다. Slug 충돌만 다음 후보로 진행하고, 성공하면 즉시 반환한다.
- 직접 변경은 정규화·예약어 검증을 거친다. 같은 Slug는 수정 시각을 바꾸지 않고 성공하며, 이미 사용 중인 Slug는 기존 오류 화면으로 돌려준다.
- 기존 `IDropCommandStore` seam의 `TryAddAsync`와 `TryChangeSlugAsync`는 `Succeeded` 또는 `SlugConflict`를 반환한다. 후자는 tracked Drop과 원하는 Slug·수정 시각을 받아 adapter 안에서 변경을 적용한다. SQLite adapter는 대상 Drop의 Slug 고유성 위반만 충돌 결과로 변환한다. 다른 저장 오류와 취소는 그대로 전파한다.
- 성공한 쓰기는 기존처럼 scope의 모든 대기 변경을 커밋한다. Slug 변경이 실패하면 그 호출 직전의 Slug·수정 시각과 추적 상태만 복원한다. 같은 Drop의 다른 미저장 필드와 다른 tracked Drop은 보존하며, 실패한 신규 Drop은 추적에서 제거한다.
- fake adapter는 예상 변경 전체의 고유성을 검증한 뒤 한 번에 반영한다. SQLite와 같은 command interface로 충돌·실패 후 scope 재사용·변경 필드 보존을 검증한다.

## 스택

- **.NET + Razor Pages (SSR)**, EF Core + SQLite
- 인증은 ASP.NET Core 쿠키 인증
- htmx 4.0.0으로 부분 갱신. 웹 업로드 전송률은 해당 폼의 커스텀 XHR 전송으로 표시한다
- CSS는 Tailwind + daisyUI. **생성 결과물을 저장소에 커밋한다** — Docker에서 node 스테이지를 없애기 위해서다

### 화면 디자인

화면의 기준은 `main`의 로고, Pretendard 글꼴, 640px 단일 열, Flowbite 색상·간격과 밝은/어두운 테마다. 로그인·업로드·미리보기·파일 목록과 수정 모달을 이 기준에 맞춘다. 업로드는 비공개로 시작하며 공개·비밀번호 설정은 상세 화면에서 한다.

소유자의 파일 목록은 공통 View Component로 홈과 상세 화면에 표시한다. 검색과 페이지네이션은 유지하되 검색은 아이콘으로 펼치고, 페이지 이동은 여러 페이지가 있을 때 표시한다. 비인증 화면에는 소유자 목록을 렌더링하지 않는다.

Pretendard 1.3.9 글꼴은 `wwwroot/fonts/`에 라이선스와 함께 포함한다. main에서 사용한 Flowbite 아이콘의 경로는 Razor partial로 재사용하며 `Pages/Shared/FlowbiteIcons.LICENSE.txt`에 라이선스를 둔다. 미리보기는 선택한 로컬 파일의 blob URL을 사용하며 CSP는 이미지·미디어에만 blob을 허용한다.

`_FontFaces` partial은 `ResourceAssetCollection`에서 해시가 붙은 글꼴 URL을 찾아 `@font-face`를 렌더링한다. CSS에 고정 URL을 넣는 대신 ASP.NET Core 정적 자산의 장기 캐시와 파일 변경 시 URL 갱신을 사용한다.

### 저장된 Drop 미리보기

Infrastructure의 순수 `DropPreviewPolicy.Evaluate`가 MIME을 한 번 해석해 표시 종류와 inline 허용 여부를 함께 반환한다. 대소문자와 매개변수는 media type 비교에 영향을 주지 않는다. `_DropPreview`는 그 표시 종류로 기존 HTML을 만들고 다운로드 adapter는 요청의 `inline` 값과 허용 여부를 함께 확인한다.

- SVG를 제외한 image 계열, video·audio 계열, PDF는 해당 미리보기와 inline을 허용한다. 개별 subtype 목록은 만들지 않는다.
- `text/plain`은 화면 미리보기 없이 inline만 허용한다. SVG·HTML과 나머지 타입은 미리보기 없이 attachment로 전달한다. 일반 다운로드는 항상 attachment다.
- 파일 아이콘의 확장자 fallback과 업로드 전 blob 미리보기는 별도 표시 동작이다. 확장자로 저장된 Drop의 미리보기나 inline을 허용하지 않는다.
- 저장된 ContentType은 바꾸지 않고 기존 값 그대로 `PhysicalFile`에 전달한다. 파싱 실패는 미리보기와 inline을 거부하지만, 손상된 MIME의 다운로드를 복구하거나 대체하는 기능은 추가하지 않는다. 접근 판정과 Range 처리는 유지한다.

### 부분 갱신과 화면 수명

Owner의 즐겨찾기·Publish·메타데이터·Drop Password 변경은 관련 HTML만 갱신한다. 미디어 node와 다른 dialog의 미저장 입력은 유지한다. 목록은 변경 뒤 자기 검색·정렬·페이지 조건으로 별도 조회하며, 조건은 현재 문서에서만 유지한다.

Favorite와 Visibility 요청은 반전 명령 대신 원하는 최종 상태를 보낸다. 즐겨찾기만 먼저 표시하고 응답 유실 시 서버 상태를 다시 확인한다. 서로 다른 변경은 동시에 허용하되 같은 상태에 대한 요청은 중복 제출하지 않는다. Slug 변경과 삭제는 진행 중 저장·확인을 기다린 뒤 전체 이동한다. 웹 업로드 성공은 새 Drop 상세로 이동한다.

Owner 변경은 상세 화면의 경로만 지원한다. 이전 Index Favorite·Delete handler와 Core의 반전 작업, `uploaded` 업로드 완료 화면은 제거했다. 인증·CSRF가 유효해도 이전 변경 POST는 Index의 기본 POST에서 404로 끝나며 호환 redirect는 없다. Logout과 목록 fragment는 유지하고, 홈은 업로드 화면과 필요한 `deleted` 안내를 표시한다.

부분 응답은 기능별 Razor partial로 만들고 `X-Drop-Outcome`으로 변경·검증 오류·조회 결과를 구분한다. 기존 일반 폼 응답은 유지한다. `drop-interactions.js`가 변경과 dialog 수명을, `drop-list.js`가 목록의 마지막 요청 조건과 늦은 응답 처리를 맡는다. 새 mutation과 목록 조건 변경은 이전 읽기 세대를 무효화한다. 공유 안내의 결합 상태는 저장이 끝난 뒤 새 요청으로 읽는다.

공유 화면의 잠금 해제는 쿠키 설정 후 GET에서 접근 정책을 다시 판정한다. 실패의 401 HTML은 잠금 해제 폼에만 적용하며 잠긴 Drop의 메타데이터는 포함하지 않는다. fragment에는 inline script나 `hx-on`을 넣지 않는다. 브라우저 회귀 검증은 [testing.md](testing.md)를 따른다.

### htmx 4와 업로드 진행률

목록의 공통 속성은 `:inherited`로 명시적으로 상속한다. 이벤트는 `htmx:config:request`, `htmx:before:swap`, `htmx:finally:request` 등 4.x 이름과 `event.detail.ctx`를 사용한다. 요청 값은 인코딩 전 `ctx.request.body`의 `FormData`에서 수정하며, 완료·실패 뒤 UI 정리는 `htmx:finally:request`에서 수행한다. 4.x는 기본적으로 4xx·5xx 응답도 교체하므로 오류 응답은 `htmx:before:swap`에서 취소하고, 공유 잠금 해제 폼의 401 HTML만 허용한다. [공식 변경사항](https://four.htmx.org/docs/whats-new-in-htmx-4)을 기준으로 한다.

htmx 4의 기본 전송은 Fetch이며 업로드 진행률 이벤트를 제공하지 않는다. 전송률 퍼센트를 유지하기 위해 업로드 폼만 `ctx.fetch`를 XHR 기반 함수로 바꾸고 `Promise<Response>`를 반환한다. XHR의 `upload.progress`로 전송률을 표시하고 htmx의 요청 헤더·취소 신호·`HX-Redirect` 처리를 연결한다. 대용량 업로드에는 htmx 기본 60초 제한이 적용되지 않도록 해당 요청의 timeout을 0으로 둔다. 이는 teledrop의 커스텀 전송 구현이며, `ctx.fetch` 재정의는 [공식 확장 작성 가이드](https://github.com/bigskysoftware/htmx/blob/v4.0.0/dist/skills/htmx-extension-authoring.md#request-context-detailctx)에 설명되어 있다. Fetch의 제한과 별도 업로드 도구에 대한 안내는 [공식 파일 업로드 문서](https://four.htmx.org/patterns/file-upload#upload-progress)를 따른다.

htmx의 SSE·multipart 스트리밍은 서버 응답으로 화면을 연속 갱신하는 기능이다. 서버 수신·저장 진행률을 표시하려면 진행 상태 측정과 전달 경로를 별도로 구현해야 한다. 현재 퍼센트는 브라우저의 전송 진행률이며, 100%만으로 저장 완료를 뜻하지 않는다. Drop 생성이 끝난 뒤 서버가 반환하는 `204`와 `HX-Redirect`로 상세 화면에 이동한다. JS가 없으면 일반 multipart 폼 POST로 업로드한다.

### 개발 명령

```
npm --prefix src/Teledrop.Infrastructure ci               # 최초 1회
npm --prefix src/Teledrop.Infrastructure run build        # CSS 생성 + htmx 복사 → wwwroot/
npm --prefix src/Teledrop.Infrastructure run watch        # CSS만 감시
dotnet run --project src/Teledrop --launch-profile http
```

`src/Teledrop.Infrastructure/wwwroot/css/app.css`와 `src/Teledrop.Infrastructure/wwwroot/js/htmx.min.js`는 **생성물이지만 커밋한다.** npm은 로컬 개발에만 필요하고 Docker 빌드에는 들어가지 않는다. daisyUI가 `@plugin`으로 `node_modules` 해석을 요구하므로 Tailwind standalone 바이너리로는 대체할 수 없다.

CSS 소스는 `src/Teledrop.Infrastructure/Styles/app.css`다. Tailwind 기본 탐색 경로에 `.cshtml`이 없으므로 `@source`로 `Pages/`를 명시해두었다 — 새 뷰 디렉터리를 만들면 여기에 추가해야 클래스가 방출된다.

`MapStaticAssets`가 정적 자산 URL에 해시를 붙이므로 `asp-append-version`은 쓰지 않는다. 다만 해시는 빌드 시점에 계산되므로, `npm run watch`로 CSS만 갱신하면 `dotnet` 쪽 재빌드 전까지 반영되지 않는다.

### 아키텍처 원칙

**프로덕션 프로젝트는 셋이다.**

- `src/Teledrop.Core/` — Drop, 순수 정책, use case, 최소 port
- `src/Teledrop.Infrastructure/` — HTTP·Razor·EF Core·SQLite·파일시스템·보안 implementation을 포함하는 Razor Class Library
- `src/Teledrop/` — 설정 공급과 DI composition root, 초기화·middleware·endpoint 순서, 실행

의존 방향은 `Teledrop → Core`, `Teledrop → Infrastructure → Core`다. Core는 ASP.NET Core, EF Core, SQLite를 참조하지 않으며 Infrastructure는 실행 host를 참조하지 않는다. 프로젝트 이동만으로 module의 depth가 높아지지는 않는다. 저장 계약과 파일 위치 해석의 locality를 함께 개선하는 것이 이번 분리의 목적이다([ADR 0007](adr/0007-infrastructure-and-composition-root.md)).

프로젝트 안에서는 계속 **기능별 폴더(vertical slice)** 로 모은다. Core는 `Drops/`, Infrastructure는 `Features/Auth/`, `Features/Drops/`, `Features/Api/`와 Razor `Pages/`를 쓴다. Infrastructure 내부의 단순 목록·상세 조회는 EF를 직접 사용한다. HTTP와 EF를 별도 프로젝트로 나누거나 이를 위해 Core에 읽기 port를 추가하지 않는다.

use case는 concrete class다. use case마다 interface를 만들지 않고, Core가 외부 능력을 필요로 할 때만 최소 port를 선언한다. 범용 Repository, 별도 Unit of Work, MediatR, Entity/DTO 복제, presenter module은 두지 않는다. HTTP handler는 입력을 검증하고 use case 결과를 HTTP 응답으로 바꾸며 제품 규칙은 Core가 판단한다.

`IDropCommandStore`는 scope를 가진다. 조회한 Drop의 객체 변경은 write를 호출하기 전에는 저장되지 않는다. `UpdateAsync`는 같은 scope에서 이미 저장된 Drop을 추적 중인 경우에만 허용하며, 다른 scope·미추적·삽입 대기·삭제 대기 객체는 `InvalidOperationException`으로 거부한다. EF adapter는 변경 추적을 유지해 바뀐 필드만 저장한다. 테스트의 fake adapter도 작업 중 객체와 저장된 snapshot을 구분한다.

`DropFileStore.FindFilePath`는 Location의 실제 경로와 존재 확인을 담당한다. `DropAccess`가 허용한 뒤 다운로드 adapter는 반환된 경로로 `PhysicalFile`과 Range 응답을 구성한다. 파일이 없으면 404다. 파일 생성 중·입력 검증 중·DB 인계 후의 정리 책임과 Core의 DB 행 우선 삭제 순서는 유지한다.

실행 host는 Core use case를 등록하고 `AddTeledropInfrastructure`, `InitializeTeledropStorageAsync`, `UseTeledropSecurityHeaders`를 호출한다. SQLite 경로·migration 적용, 인증 callback과 nonce 처리는 Infrastructure 안에 있다. host의 assembly 이름과 content root, 실행 설정 파일은 유지한다.

RCL은 `StaticWebAssetBasePath=/`를 사용해 기존 `/css`, `/js`, `/fonts`, `/static`, favicon URL을 보존한다. Pages·Styles·npm 파일·wwwroot를 함께 옮겨 CSS 탐색과 생성 경로도 유지한다. 빌드된 자산은 host의 static web assets manifest에 포함되며 Release publish에서도 확인한다.

## 구현 시 주의

- 큰 파일은 메모리 버퍼링 없이 디스크로 스트리밍한다. ASP.NET Core는 명시적 스트리밍이 필요하다
- 리버스 프록시의 업로드 타임아웃과 최대 바디 크기를 확인한다
- argon2는 .NET 표준에 없다. 서드파티 패키지가 필요하다
- **main은 드롭 비밀번호를 평문으로 저장한다** (`content.password != password` 비교). 새 구현은 argon2 해시로 바꾼다
- README 태그라인 `powered by REST API`를 고친다 — SPA가 API를 호출하던 구조를 설명한 문장이었고, 더 이상 사실이 아니다
