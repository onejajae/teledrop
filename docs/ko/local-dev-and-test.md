# 로컬 개발 및 테스트

Docker 없이 직접 실행하려면 아래 순서로 진행하면 됩니다.

## 사전 준비
* Python 3.14+
* `uv`
* Node.js 20+ (CSS 빌드용)

## 빠른 시작
환경 구성, CSS 빌드, 서버 실행을 한 번에 처리하려면:
```bash
./scripts/run_dev.sh
```

## 로컬 개발용 `.env` 값
HTTP 기반 로컬 개발에서는 다음 값을 사용하는 것을 권장합니다:

```dotenv
WEB_USERNAME=admin
WEB_PASSWORD=$argon2id$...
BOOTSTRAP_ALLOW_INSECURE_DEFAULTS=true
SESSION_COOKIE_SECURE=false
API_DOCS_ENABLED=true
CORS_ALLOW_ALL=true
```

`WEB_USERNAME`, `WEB_PASSWORD`는 빈 데이터베이스에 첫 사용자를 넣을 때만 사용됩니다.

## 수동 실행 절차
1. **Python 의존성 동기화**
   ```bash
   uv sync
   ```

2. **UI asset 빌드**
   ```bash
   cd ui-build
   npm ci
   npm run build
   cd ..
   ```
   `./scripts/run_dev.sh`를 사용하면 `ui-build/node_modules`가 이미 있을 때 `npm ci`를 자동으로 건너뜁니다.

3. **서버 실행**
   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8000
   ```

앱은 빈 데이터베이스에서 시작할 때 현재 스키마를 자동 생성합니다. 기존 Alembic/레거시 데이터베이스는 거부되므로, 이 버전을 시작하기 전에 `share/database.db`를 백업한 뒤 삭제하세요.

## 테스트 실행
테스트는 범위에 따라 다음과 같이 나뉩니다.
* `tests/unit`: 빠른 단위 테스트
* `tests/integration`: 레이어 간 통합 테스트
* `tests/smoke`: API/웹 상위 흐름 스모크 테스트

```bash
# 전체 테스트
uv run pytest -q

# 디렉토리별 실행
uv run pytest tests/unit -q
uv run pytest tests/integration -q
uv run pytest tests/smoke -q
```

## 품질 점검
GitHub Actions 품질 워크플로는 다음 점검을 실행합니다.

```bash
uv sync --frozen
uv run pytest -q
uvx --from ruff==0.15.12 ruff check .

# 정보성 Python 의존성 감사
uv export --format requirements.txt --no-dev --no-emit-project --no-hashes --frozen --output-file /tmp/teledrop-requirements.txt
uvx --from pip-audit==2.10.0 pip-audit --requirement /tmp/teledrop-requirements.txt --strict --no-deps --disable-pip --progress-spinner off

cd ui-build
npm ci
npm run build
npm audit --audit-level=high
```

Docker 빌드는 CSS 빌드 단계에서 `npm ci`를 사용하고 uv 이미지를 `0.11.7`로 고정합니다.
