# 테스트 실행

테스트는 성격에 따라 다음 디렉토리로 분리되어 있습니다.
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
CI 품질 워크플로는 다음을 실행합니다.

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
