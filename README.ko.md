[한국어](README.ko.md) | [English](README.md)

# teledrop
REST API를 기반으로 하는 개인용 파일 공유 플랫폼

## 소개

> _teledrop은 개인 서버에서 사용할 수 있는 파일 공유 플랫폼입니다. 보안이 취약한 환경에서 Google Drive나 Dropbox와 같은 클라우드 서비스를 이용하기 위해 로그인할 필요 없이 개인 파일에 접근하기 위해 개발하였습니다._

## 설치

### 1. 사전 준비

* Docker

### 2. 사용자 비밀번호 해시 생성

1. 이미지의 `hash-password` 명령으로 Argon2id 해시를 생성합니다.

```bash
docker run --rm -it ghcr.io/onejajae/teledrop:latest hash-password
```

비밀번호를 두 번 숨김 입력하면 해시를 출력하고 종료합니다. 서버 설정이나 볼륨은 필요하지 않습니다. 배포 이미지에 명령이 아직 없다면 아래의 [직접 Docker 이미지 빌드](#직접-docker-이미지-빌드)를 사용하세요.

> **주의사항:** `compose.yml`에 해시를 직접 작성할 때 모든 `$`를 `$$`로 바꿔야 합니다.
>
> ```yaml
> WEB_PASSWORD: '$$argon2id$$v=19$$m=65536,t=3,p=1$$<salt>$$<hash>'
> ```
>
> 위 값은 형식 예시입니다. 생성한 전체 해시를 사용하세요. `docker run --env`에서는 `$`를 바꾸지 않고 값을 작은따옴표로 감쌉니다.

2. `WEB_USERNAME`과 `WEB_PASSWORD`는 필수입니다. 설정하지 않으면 서버가 시작되지 않습니다. 사용자 ID는 대소문자를 구분합니다.

### 3. teledrop 실행

* `compose.yml` 작성 (권장)

```yaml
services:
  teledrop:
    image: ghcr.io/onejajae/teledrop:latest
    container_name: teledrop
    restart: unless-stopped
    ports:
      - 80:8080/tcp
    volumes:
      - <공유할_볼륨_또는_디렉토리>:/app/share
    environment:
      - TZ=Asia/Seoul
      - WEB_USERNAME=<로그인_ID>
      - WEB_PASSWORD=<해시된_로그인_비밀번호>  # $ 대신 $$ 사용
      - SHARE_DIRECTORY=/app/share
```

```bash
docker compose up -d
```

* 명령줄에서 실행

```bash
docker run --detach \
   --name teledrop \
   -p 80:8080 \
   --env WEB_USERNAME='<로그인_ID>' \
   --env WEB_PASSWORD='<해시된_로그인_비밀번호>' \
   --env SHARE_DIRECTORY='/app/share' \
   --restart unless-stopped \
   --volume '<공유할_볼륨_또는_디렉토리>:/app/share' \
   ghcr.io/onejajae/teledrop:latest
```

### 4. 옵션

* 리버스 프록시 뒤에서 실행

> 실제 클라이언트 IP와 원래 요청 스킴을 반영하려면 `compose.yml`의 기존 환경변수 목록에 추가합니다.
>
> ```yaml
> environment:
>   - ASPNETCORE_FORWARDEDHEADERS_ENABLED=true
> ```
>
> 기본값은 비활성화입니다. 활성화하면 모든 프록시의 `X-Forwarded-For`·`X-Forwarded-Proto`를 신뢰하므로 앱에는 프록시를 통해서만 접근하도록 구성하세요. 프록시가 전달 헤더를 올바르게 설정해야 합니다.

* API 업로드 사용

> API 업로드를 사용할 때 인증 키를 설정합니다.
>
> ```yaml
> environment:
>   - TELEDROP_API_KEY=<API_키>
> ```
>
> `/api/upload` 요청의 `X-API-Key` 헤더에 같은 키를 전달합니다. 미설정 시 API 업로드는 401을 반환하며 웹 업로드는 계속 사용할 수 있습니다.

* 업로드 크기 제한 변경

> 기본값은 `1073741824`바이트(1 GiB)입니다. 양수 바이트 값으로 지정합니다.
>
> ```yaml
> environment:
>   - MAX_UPLOAD_BYTES=1073741824
> ```
>
> 파일 크기와 전체 요청 본문에 적용됩니다. multipart 부가 데이터도 포함되므로 실제 업로드 가능한 파일 크기는 이보다 작습니다.

* 비밀번호 해시 생성 자동화

> `--stdin`은 표준 입력의 첫 줄을 읽어 확인 입력 없이 해시만 출력합니다. 비밀번호를 명령 인자로 전달하지 마세요.
>
> ```bash
> docker run --rm -i ghcr.io/onejajae/teledrop:latest hash-password --stdin < /path/to/password.txt
> ```
>
> Compose 설정 후에는 `docker compose run --rm --no-deps teledrop hash-password`로 숨김 입력 방식도 사용할 수 있습니다.

환경변수 변경 후 `docker compose up -d`로 컨테이너를 재생성해 적용합니다.

## 직접 Docker 이미지 빌드

현재 소스로 이미지를 빌드할 수 있습니다.

```bash
docker build -t teledrop:local .
docker run --rm -it teledrop:local hash-password
```

실행 예시의 이미지 이름을 `teledrop:local`로 바꾸어 사용하세요.
