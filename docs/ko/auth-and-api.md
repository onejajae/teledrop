# 인증 및 API

## 인증
* 웹 UI 접근은 비밀번호 로그인이 필요
* `WEB_USERNAME`, `WEB_PASSWORD`는 빈 데이터베이스에서 첫 웹 사용자를 만드는 부트스트랩 값으로만 사용됩니다
* REST API 읽기 엔드포인트는 다음 인증을 허용:
  * 세션 쿠키 인증
  * `X-API-Key: tdpk_<public_id>_<secret>`
* REST API 변경 엔드포인트(`POST/PATCH/DELETE /api/drop...`)는 `X-API-Key`만 허용하며 세션 쿠키만으로는 호출할 수 없습니다
* API key 관리 기능은 웹 로그인 후 `/settings/api-keys`에서만 사용 가능
* API key 관리 페이지는 현재 사용자의 키만 보여줍니다
* 보호된 REST API 인증 실패는 `401`과 함께 다음 헤더를 반환:
  * `WWW-Authenticate: Session, ApiKey`

기본 동작 및 확장 환경 참고:
* `SESSION_COOKIE_SECURE` 기본값은 `true`
* `SESSION_COOKIE_SAMESITE=none`를 사용하면 `SESSION_COOKIE_SECURE=true`가 필수
* `APP_MODE`는 지원하지 않으며 `.env`에 있으면 시작 시 실패
* HTTP는 로컬/내부망 용도로만 사용 (`SESSION_COOKIE_SECURE=false`), 운영 환경은 HTTPS 권장
* `API_DOCS_ENABLED` 기본값은 `false` (로컬/개발 환경에서만 활성화 권장)
* `CORS_ALLOW_ALL` 기본값은 `false` (로컬/개발 환경에서만 활성화 권장)
* `MAX_UPLOAD_BYTES` 기본값은 `1073741824`(1 GiB)이며 업로드 시작 전과 실제 파일 쓰기 중 모두 적용됩니다
* `BOOTSTRAP_ALLOW_INSECURE_DEFAULTS` 기본값은 로컬 개발 편의를 위해 `true`
* 운영 배포는 `BOOTSTRAP_ALLOW_INSECURE_DEFAULTS=false`를 설정해야 합니다. 이때 빈 데이터베이스에서 `WEB_USERNAME`/`WEB_PASSWORD`가 누락되었거나, `WEB_PASSWORD`가 유효한 Argon2 해시가 아니거나, 여전히 `admin/password`이면 시작이 실패합니다
* `CSRF_SECRET_KEY` 기본값은 프로세스별 랜덤 값
* 멀티 워커/인스턴스에서는 공유 `CSRF_SECRET_KEY`를 설정해야 함
* 이 공유 시크릿은 비밀번호 보호 링크의 drop unlock grant 쿠키 서명에도 함께 사용됨

드롭 링크 비밀번호 정책:
* `drop_password`는 Argon2id 해시로 저장됩니다.
* 계정 비밀번호 수준의 보안 기능이 아니라, 공유 링크 보호용 경량 장치로 사용해야 합니다.
* 계정 비밀번호를 드롭 비밀번호로 재사용하지 마세요.
* 웹 UI는 더 이상 드롭 비밀번호를 URL에 실어 나르지 않으며, 잠금 해제 성공 시 서명된 HttpOnly grant 쿠키를 사용합니다.
* grant 쿠키는 raw password가 아니라 저장된 password hash material을 기준으로 서명됩니다.
* 기존 평문 protected drop은 의도적으로 호환하지 않습니다. 이 버전 사용 전 데이터베이스를 백업하고 재생성하세요.

주요 인증 엔드포인트:
* `POST /api/auth/login`
* `GET /api/auth/me` (세션 또는 API key)
* `POST /api/auth/logout` (권장)
* `GET /api/auth/logout` (호환)

## 개편된 드롭 API (Breaking)
* `GET /api/drop?page=1&page_size=50&sort=created_at|title|size_bytes&order=asc|desc`
* `POST /api/drop` (API key 전용, multipart: `file`, `slug?`, `title?`, `description?`, `access_scope`, `drop_password?`)
* `GET /api/drop/{slug}/meta` (보호된 드롭은 `X-Drop-Password` 헤더 사용)
* `GET /api/drop/{slug}?disposition=attachment|inline` (`disposition=inline`은 호환성 때문에 받지만 항상 `Content-Disposition: attachment`로 응답합니다. 보호된 드롭은 `X-Drop-Password` 헤더 사용, Range 지원)
* `PATCH /api/drop/{slug}` (API key 전용, JSON: `title?`, `description?`, `access_scope?`, `is_favorite?`, `new_password?`, `current_password?`)
* `DELETE /api/drop/{slug}` (API key 전용, 보호된 드롭은 `X-Drop-Password` 헤더 사용)
* `GET /api/drop/availability/{slug}`

소유권 및 마스킹 규칙:
* 새 드롭은 현재 인증된 사용자 소유로 생성됩니다
* private 드롭은 소유자만 볼 수 있습니다
* private 드롭에 대한 비소유자 접근은 API와 웹 UI 모두에서 `404`로 마스킹됩니다

알려진 잔여 리스크:
* 다운로드와 삭제가 동시에 발생하는 race는 이번 wave에서 동작을 변경하지 않습니다. 삭제가 파일을 먼저 staged 상태로 옮긴 뒤 동시 다운로드 스트림이 파일을 열려고 하면 해당 다운로드가 실패할 수 있으며, 이후 저장소 동시성 설계가 들어가기 전까지 strict xfail 테스트로 고정합니다.

## 웹 액션 경로(HTMX 폼)
* `POST /actions/auth/login`
* `POST /actions/auth/logout`
* `POST /actions/auth/api-keys/create`
* `POST /actions/auth/api-keys/{public_id}/revoke`
* `POST /actions/auth/api-keys/{public_id}/delete`
* `POST /actions/drop/upload`
* `POST /actions/drop/{slug}/open`
* `POST /actions/drop/{slug}/detail`
* `POST /actions/drop/{slug}/unlock`
* `POST /actions/drop/{slug}/favorite`
* `POST /actions/drop/{slug}/access`
* `POST /actions/drop/{slug}/password`
* `POST /actions/drop/{slug}/delete`

## HTMX SSR 웹 UI
* `GET /` (로그인 + 업로드/목록/상세 관리 패널)
* `GET /<파일_SLUG>` (공유 다운로드 뷰)
* `GET /settings/api-keys` (웹 API key 관리 페이지, 로그인 필요, 현재 사용자의 키만 표시)
* UI의 상태 변경 요청은 CSRF 보호가 적용됩니다.
* 비밀번호 보호 드롭 잠금 해제 후에는 쿼리스트링 없이 clean URL로 다시 이동합니다.
* `CSRF_SECRET_KEY`를 변경해 배포하면, 기존에 렌더된 폼 토큰은 403으로 거부되는 것이 정상입니다.
