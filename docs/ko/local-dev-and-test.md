# 로컬 개발 및 테스트

Docker 없이 직접 실행하려면 아래 순서로 진행하면 됩니다.

## 사전 준비
* Python 3.14+
* `uv`
* Node.js 20+ (CSS 빌드용)

## 빠른 시작
환경 구성, Alembic 마이그레이션, CSS 빌드, 서버 실행을 한 번에 처리하려면:
```bash
./scripts/run_dev.sh
```

## 로컬 개발용 `.env` 값
HTTP 기반 로컬 개발에서는 다음 값을 사용하는 것을 권장합니다:

```dotenv
SESSION_COOKIE_SECURE=false
API_DOCS_ENABLED=true
CORS_ALLOW_ALL=true
```

## 수동 실행 절차
1. **Python 의존성 동기화**
   ```bash
   uv sync
   ```

2. **데이터베이스 마이그레이션 적용**
   ```bash
   uv run alembic -c alembic.ini upgrade head
   ```

3. **Tailwind CSS 빌드**
   ```bash
   cd ui-build
   npm install
   npm run build:css
   cd ..
   ```
   `./scripts/run_dev.sh`를 사용하면 `ui-build/node_modules`가 이미 있을 때 `npm install`을 자동으로 건너뜁니다.

4. **서버 실행**
   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8000
   ```

마이그레이션을 건너뛰면 앱 시작 시 테이블을 자동 생성하지 않고 즉시 실패합니다.

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

# 마커 기반 실행
uv run pytest -m unit -q
uv run pytest -m "integration or smoke" -q
```
