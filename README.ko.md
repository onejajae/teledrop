[한국어](README.ko.md) | [English](README.md)

# teledrop
REST API를 기반으로 하는 개인용 파일 공유 플랫폼

## 소개
> _teledrop은 개인 서버에서 사용할 수 있는 파일 공유 플랫폼입니다. 보안이 취약한 환경에서 Google Drive나 Dropbox와 같은 클라우드 서비스를 이용하기 위해 로그인할 필요 없이 개인 파일에 접근하기 위해 개발하였습니다._

## 설치
### 1. 사전 준비
* Docker

### 2. 사용자 비밀번호 해시 생성
1. 비밀번호는 Argon2 알고리즘을 사용하여 해시해야 합니다.
> **주의사항:** `docker-compose.yml` 파일에서 환경 변수를 설정할 때 `$` 기호를 `$$` 로 변경해야 합니다.   
> ```yaml
> WEB_PASSWORD: $$argon2id$$v=19$$m=65536,t=3,p=4$$0123456789ABCDEF$$abcdefghijklmnopqrstuvwxyz0123456789
> ```
> 이렇게 해야 `$` 기호를 올바르게 입력할 수 있습니다.

2. 사용자 계정을 설정하지 않으면 기본 계정이 `admin/password`로 설정됩니다. 
**보안을 위해 반드시 사용자 계정을 설정하십시오.**

### 3. teledrop 실행
* `docker-compose.yml` 작성 (권장)
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
      - TZ=Asia/Seoul
      - WEB_USERNAME=<로그인_ID>
      - WEB_PASSWORD=<해시된_로그인_비밀번호>  # $ 대신 $$ 사용
```
```bash
docker compose up -d
```

* 명령줄에서 실행
```bash
docker run --detach \
   --name teledrop \
   -p 80:8000 \
   --env WEB_USERNAME=<로그인_ID> \
   --env WEB_PASSWORD=<해시된_로그인_비밀번호> \
   --restart unless-stopped \
   --volume <공유할_볼륨_또는_디렉토리>:/teledrop/share \
   ghcr.io/onejajae/teledrop:latest
```

### 4. 옵션 
* 리버스 프록시 뒤에서 실행
> teledrop을 리버스 프록시 뒤에서 실행하는 경우 실제 클라이언트 IP 주소를 얻기 위해 다음 옵션을 추가할 수 있습니다.
> ```yaml
> # docker-compose.yml
> services:
>   teledrop:
>     ...
>     command: "--proxy-headers --forwarded-allow-ips *"
>     ...
> ``` 

* 여러 개의 워커 프로세스 실행
> 성능 향상을 위해 `--workers` 옵션을 사용하여 워커 프로세스 개수를 지정할 수 있습니다.
> ```yaml
> # docker-compose.yml
> services:
>   teledrop:
>     ...
>     command: "--workers <프로세스_개수>"
>     ...
> ```
> 이 경우 각 프로세스가 동일한 비밀 키를 사용하여 JWT 토큰을 검증해야 하기 때문에 `JWT_SECRET` 환경 변수를 설정해야 합니다.  
> ```yaml
> environment:
>   - JWT_SECRET=<비밀키>
> ```
> OpenSSL을 사용하여 비밀 키를 생성할 수 있습니다.
> ```bash
> openssl rand -hex 32
> ```
> ***최소 32바이트 (256비트) 이상의 비밀 키를 사용하는 것이 권장되며, 보안 강화를 위해 더 긴 길이의 키를 사용할 수 있습니다.***

## 직접 Docker 이미지 빌드
기본 제공되는 Docker 이미지를 사용하지 않고 직접 빌드할 수 있습니다.
```bash
docker build -t teledrop .
```
