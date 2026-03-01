# 인증 및 API

## 인증
* 비밀번호 로그인만 사용
* `WEB_USERNAME`, `WEB_PASSWORD`로 계정 정보를 설정

기본 동작 및 확장 환경 참고:
* `APP_MODE` 기본값은 `prod`
* `prod`에서 `SESSION_COOKIE_SECURE`를 명시하지 않으면 기본적으로 `true`
* `SESSION_COOKIE_SAMESITE=none`를 사용하면 `SESSION_COOKIE_SECURE=true`가 필수
* `CSRF_SECRET_KEY` 기본값은 프로세스별 랜덤 값
* 멀티 워커/인스턴스에서는 공유 `CSRF_SECRET_KEY`를 설정해야 함

드롭 링크 비밀번호 정책:
* `drop_password`는 현재 평문으로 저장/비교됩니다.
* 계정 비밀번호 수준의 보안 기능이 아니라, 공유 링크 보호용 경량 장치로 사용해야 합니다.
* 계정 비밀번호를 드롭 비밀번호로 재사용하지 마세요.

주요 인증 엔드포인트:
* `POST /api/auth/login`
* `GET /api/auth/me`
* `POST /api/auth/logout` (권장)
* `GET /api/auth/logout` (호환)

## 개편된 드롭 API (Breaking)
* `GET /api/drop?page=1&page_size=50&sort=created_at|title|size_bytes&order=asc|desc`
* `POST /api/drop` (multipart: `file`, `slug?`, `title?`, `description?`, `access_scope`, `drop_password?`)
* `GET /api/drop/{slug}/meta?drop_password=...`
* `GET /api/drop/{slug}?disposition=attachment|inline&drop_password=...` (Range 지원)
* `PATCH /api/drop/{slug}` (JSON: `title?`, `description?`, `access_scope?`, `is_favorite?`, `new_password?`, `current_password?`)
* `DELETE /api/drop/{slug}?current_password=...`
* `GET /api/drop/availability/{slug}`

## 웹 액션 경로(HTMX 폼)
* `POST /actions/auth/login`
* `POST /actions/auth/logout`
* `POST /actions/drop/upload`
* `POST /actions/drop/{slug}/open`
* `POST /actions/drop/{slug}/detail`
* `POST /actions/drop/{slug}/favorite`
* `POST /actions/drop/{slug}/access`
* `POST /actions/drop/{slug}/password`
* `POST /actions/drop/{slug}/delete`

## HTMX SSR 미리보기 UI
* `GET /` (로그인 + 업로드/목록/상세 관리 패널)
* `GET /<파일_SLUG>` (대시보드 미리보기 뷰)
* UI의 상태 변경 요청은 CSRF 보호가 적용됩니다.
* `CSRF_SECRET_KEY`를 변경해 배포하면, 기존에 렌더된 폼 토큰은 403으로 거부되는 것이 정상입니다.
