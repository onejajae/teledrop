# 마이그레이션 안내

드롭 스키마가 기존 `content`/`contents` 테이블에서 `drops`로 변경되었습니다.

운영 환경 업그레이드 전 DB 백업을 권장합니다:
```bash
cp share/database.db share/database.db.bak
```

`migrations/`에 Alembic 리비전이 포함되어 있으며, 앱 시작 시에도 레거시 `content`/`contents` -> `drops` 이전을 수행합니다.
Alembic을 수동으로 실행하려면 실행 환경에 먼저 설치하세요 (`pip install alembic`).
