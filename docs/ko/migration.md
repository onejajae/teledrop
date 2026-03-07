# 마이그레이션 안내

드롭 스키마가 기존 `content`/`contents` 테이블에서 `drops`로 변경되었습니다.

운영 환경 업그레이드 전 DB 백업을 권장합니다:
```bash
cp share/database.db share/database.db.bak
```

`migrations/`에 Alembic 리비전이 포함되어 있습니다.
공식 Docker 이미지는 컨테이너 시작 시 아래 명령을 자동 실행합니다:
```bash
alembic -c alembic.ini upgrade head
```

`./scripts/run_dev.sh`도 서버 시작 전에 `head`까지 자동 적용합니다.
앱 시작 시에는 데이터베이스가 이미 Alembic `head`인지 검증만 하며, 테이블을 자동 생성하지 않습니다.

Docker 엔트리포인트를 사용하지 않고 실행한다면, 앱 시작 전에 수동으로 실행하세요:
```bash
uv run alembic -c alembic.ini upgrade head
```
