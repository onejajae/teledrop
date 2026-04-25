# 마이그레이션 안내

이 버전은 기존 데이터베이스 스키마와의 호환을 의도적으로 끊습니다. 더 이상 Alembic 마이그레이션을 제공하지 않으며, 기존 `content`/`contents` 테이블이나 예전 `drops`, `auth_sessions`, `auth_api_keys` 구조를 자동 변환하지 않습니다.

운영 환경에서 업그레이드하기 전에 데이터베이스 파일을 백업하세요:
```bash
cp share/database.db share/database.db.bak
```

그 다음 이 버전을 시작하기 전에 기존 데이터베이스 파일을 삭제하세요:
```bash
rm share/database.db
```

시작 시 teledrop은 현재 스키마를 자동 생성하고 `WEB_USERNAME`, `WEB_PASSWORD`로 첫 웹 사용자를 부트스트랩합니다. `share/` 아래의 기존 업로드 파일은 새 데이터베이스에 자동으로 다시 연결되지 않습니다.
