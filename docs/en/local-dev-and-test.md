# Manual Execution (No Docker)

If you prefer running without Docker, follow these steps:

## Prerequisites
* Python 3.12+ (and `venv`)
* Node.js 20+ (for building CSS)

## Quick Start
You can use the provided script to set up the environment, build CSS, and run the server:
```bash
./scripts/run_dev.sh
```

## Manual Steps
1. **Set up Python Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install fastapi uvicorn Jinja2 "python-multipart" argon2-cffi pytest pytest-asyncio
   # or if using uv:
   # uv pip install fastapi uvicorn Jinja2 "python-multipart" argon2-cffi pytest pytest-asyncio
   ```

2. **Build Tailwind CSS**:
   ```bash
   cd ui-build
   npm install
   npm run build:css
   cd ..
   ```

3. **Run Server**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Run Tests
Test suites are organized by scope:
* `tests/unit`: fast isolated tests
* `tests/integration`: cross-layer tests
* `tests/smoke`: high-level API/web smoke tests

```bash
# all tests
uv run pytest -q

# by directory
uv run pytest tests/unit -q
uv run pytest tests/integration -q
uv run pytest tests/smoke -q

# by marker
uv run pytest -m unit -q
uv run pytest -m "integration or smoke" -q
```
