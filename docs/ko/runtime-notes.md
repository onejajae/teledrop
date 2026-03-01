# 런타임 참고사항

## CSRF 비밀키
`CSRF_SECRET_KEY`를 설정하세요.

`docker-compose.yml` 예시:
```yaml
services:
  teledrop:
    environment:
      - CSRF_SECRET_KEY=<CSRF_비밀키>
```

명령줄 실행 예시:
```bash
docker run --detach \
   --name teledrop \
   -p 80:8000 \
   --env WEB_USERNAME=<로그인_ID> \
   --env WEB_PASSWORD=<해시된_로그인_비밀번호> \
   --env CSRF_SECRET_KEY=<CSRF_비밀키> \
   --restart unless-stopped \
   --volume <공유할_볼륨_또는_디렉토리>:/teledrop/share \
   ghcr.io/onejajae/teledrop:latest
```

## 여러 워커 프로세스 운영
세션 인증 정보는 데이터베이스에 저장됩니다.  
여러 인스턴스/워커로 운영할 때는 모든 인스턴스가 동일한 DB와 파일 스토리지를 공유해야 합니다.
