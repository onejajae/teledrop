[한국어](README.md) | [English](../en/README.md)

# teledrop
REST API를 기반으로 하는 개인용 파일 공유 플랫폼

## 소개
> _teledrop은 개인 서버에서 사용할 수 있는 파일 공유 플랫폼입니다. 보안이 취약한 환경에서 Google Drive나 Dropbox와 같은 클라우드 서비스를 이용하기 위해 로그인할 필요 없이 개인 파일에 접근하기 위해 개발하였습니다._

## 설치
### 1. 사전 준비
* Docker

### 2. 사용자 비밀번호 해시 생성
1. 비밀번호는 Argon2 알고리즘을 사용하여 해시해야 합니다.
> **주의사항:** `compose.yml` 파일에서 환경 변수를 설정할 때 `$` 기호를 `$$` 로 변경해야 합니다.
> ```yaml
> WEB_PASSWORD: $$argon2id$$v=19$$m=65536,t=3,p=4$$0123456789ABCDEF$$abcdefghijklmnopqrstuvwxyz0123456789
> ```
> 이렇게 해야 `$` 기호를 올바르게 입력할 수 있습니다.

2. `WEB_USERNAME`, `WEB_PASSWORD`는 부트스트랩 전용 값입니다. 빈 데이터베이스로 처음 실행할 때 초기 웹 사용자를 생성하는 데만 사용됩니다. `WEB_PASSWORD`는 유효한 Argon2 해시여야 합니다.
3. 빈 데이터베이스에서 부트스트랩 값을 지정하지 않으면 `BOOTSTRAP_ALLOW_INSECURE_DEFAULTS=true`일 때만 기본 계정이 `admin/password`로 생성됩니다.
외부 사용자에게 노출되는 환경에서는 실행 전에 반드시 변경하고 `BOOTSTRAP_ALLOW_INSECURE_DEFAULTS=false`를 설정하세요. 이 값이 꺼져 있으면 빈 데이터베이스에서 credentials가 누락되었거나, 유효하지 않거나, 여전히 `admin/password`이면 시작이 실패합니다.

### 3. teledrop 실행
* `compose.yml` 작성 (권장)
`compose.yml` 옆에 `.env`를 만들거나 Compose 실행 전에 이 변수를 export 하세요:
```dotenv
WEB_USERNAME=<로그인_ID>
WEB_PASSWORD='$argon2id$v=19$m=65536,t=3,p=4$...'
```

```yaml
services:
  teledrop:
    image: ghcr.io/onejajae/teledrop:latest
    container_name: teledrop
    restart: unless-stopped
    ports:
      - 80:8000/tcp
    volumes:
      - <공유할_볼륨_또는_디렉토리>:/teledrop/share
    environment:
      TZ: Asia/Seoul
      WEB_USERNAME: ${WEB_USERNAME:?Set WEB_USERNAME before running docker compose}
      WEB_PASSWORD: ${WEB_PASSWORD:?Set WEB_PASSWORD to a valid Argon2 hash}
      BOOTSTRAP_ALLOW_INSECURE_DEFAULTS: "false"
```
```bash
docker compose up -d
```

* 명령줄에서 실행
```bash
docker run --detach \
   --name teledrop \
   -p 80:8000 \
   --env WEB_USERNAME \
   --env WEB_PASSWORD \
   --env BOOTSTRAP_ALLOW_INSECURE_DEFAULTS=false \
   --restart unless-stopped \
   --volume <공유할_볼륨_또는_디렉토리>:/teledrop/share \
   ghcr.io/onejajae/teledrop:latest
```

### 4. 옵션
* 리버스 프록시 뒤에서 실행
> teledrop을 리버스 프록시 뒤에서 실행하는 경우 실제 클라이언트 IP 주소를 얻기 위해 다음 옵션을 추가할 수 있습니다.
> ```yaml
> # compose.yml
> services:
>   teledrop:
>     ...
>     command: "--proxy-headers --forwarded-allow-ips *"
>     ...
	> ```

* 멀티 워커/인스턴스 환경의 `CSRF_SECRET_KEY` 공유
> `CSRF_SECRET_KEY`는 기본적으로 프로세스마다 랜덤 값이 생성됩니다.
> 여러 워커/인스턴스를 실행하면 CSRF 검증 일관성을 위해 공유 값을 설정하세요.
> ```yaml
> # compose.yml
> services:
>   teledrop:
>     environment:
>       - CSRF_SECRET_KEY=<CSRF_비밀키>
> ```
> `docker run`으로 실행하면 아래 옵션을 추가하세요:
> ```bash
> --env CSRF_SECRET_KEY=<CSRF_비밀키> \
> ```

* 쿠키 보안 기본 동작
> `SESSION_COOKIE_SECURE` 기본값은 `true`입니다.
> `SESSION_COOKIE_SAMESITE=none`를 쓰면 `SESSION_COOKIE_SECURE=true`가 필수입니다.
> `APP_MODE`는 지원하지 않습니다. `.env`에 있으면 시작 시 실패합니다.
> 외부 사용자에게 노출되는 배포 환경은 HTTPS 사용을 권장합니다.
> 로컬 개발 또는 신뢰 가능한 내부망에서 HTTP를 사용하려면 다음과 같이 설정하세요:
> ```yaml
> environment:
>   - SESSION_COOKIE_SECURE=false
>   - API_DOCS_ENABLED=true
>   - CORS_ALLOW_ALL=true
> ```

* 외부 클라이언트용 API key 인증
> REST API 읽기 엔드포인트는 세션 쿠키 또는 `X-API-Key` 인증을 허용합니다.
> REST API 변경 엔드포인트(`POST/PATCH/DELETE /api/drop...`)는 `X-API-Key`가 필요합니다.
> API key 생성/폐기/삭제 관리는 로그인된 웹 UI에서만 가능합니다:
> `/settings/api-keys`
> 요청 예시:
> ```bash
> curl -H "X-API-Key: tdpk_<public_id>_<secret>" http://localhost:8000/api/drop
> ```
> API key 원문은 생성 시점에만 1회 표시되며 이후 재조회할 수 없습니다.
> API key 페이지에는 현재 로그인한 사용자의 키만 표시됩니다.

* 업로드 및 다운로드 보안
> `MAX_UPLOAD_BYTES` 기본값은 1073741824 bytes(1 GiB)이며 업로드 시작 전과 실제 파일 쓰기 중 모두 적용됩니다.
> 파일 다운로드는 항상 `Content-Disposition: attachment`를 사용합니다. `disposition=inline`은 호환성 때문에 받지만 무시됩니다.
> 드롭 링크 비밀번호는 Argon2id 해시로 저장됩니다. 기존 평문 protected drop은 호환하지 않으므로 이 버전 사용 전 데이터베이스를 백업하고 재생성하세요.

* 여러 개의 워커 프로세스 실행
> 성능 향상을 위해 `--workers` 옵션을 사용하여 워커 프로세스 개수를 지정할 수 있습니다.
> ```yaml
> # compose.yml
> services:
>   teledrop:
>     ...
>     command: "--workers <프로세스_개수>"
>     ...
> ```
> 사용자, 세션, API key, drop 소유권은 데이터베이스에 저장됩니다.
> 여러 인스턴스/워커를 실행하면 모든 인스턴스가 동일한 데이터베이스와 파일 저장소를 공유해야 합니다.

* Docker 엔트리포인트 없이 직접 앱 시작
> teledrop은 빈 데이터베이스에서 시작할 때 현재 스키마를 자동 생성합니다.
> 기존 Alembic/레거시 데이터베이스는 자동 변환하지 않으므로, 이 버전을 시작하기 전에 `share/database.db`를 백업한 뒤 삭제하세요.

## 문서
* [인증 및 API](auth-and-api.md)
* [다중 사용자 전환 스펙](multi-user-spec.md)
* [마이그레이션 안내](migration.md)
* [로컬 개발 및 테스트](local-dev-and-test.md)
* [테스트 실행](testing.md)

## 직접 Docker 이미지 빌드
기본 제공되는 Docker 이미지를 사용하지 않고 직접 빌드할 수 있습니다.
```bash
docker build -t teledrop .
```
