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

# 마커 기반 실행
uv run pytest -m unit -q
uv run pytest -m "integration or smoke" -q
```
