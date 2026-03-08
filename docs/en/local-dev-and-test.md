# Manual Execution (No Docker)

If you prefer running without Docker, follow these steps:

## Prerequisites
* Python 3.14+
* `uv`
* Node.js 20+ (for building CSS)

## Quick Start
You can use the provided script to set up the environment, apply Alembic migrations, build CSS, and run the server:
```bash
./scripts/run_dev.sh
```

## Local Development Environment Values
For HTTP local development, set these values in `.env`:

```dotenv
SESSION_COOKIE_SECURE=false
API_DOCS_ENABLED=true
CORS_ALLOW_ALL=true
```

## Manual Steps
1. **Set up Python Environment**:
   ```bash
   uv sync
   ```

2. **Apply Database Migrations**:
   ```bash
   uv run alembic -c alembic.ini upgrade head
   ```

3. **Build Tailwind CSS**:
   ```bash
   cd ui-build
   npm install
   npm run build:css
   cd ..
   ```
   `./scripts/run_dev.sh` automatically skips `npm install` when `ui-build/node_modules` already exists.

4. **Run Server**:
   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8000
   ```

If you skip the migration step, app startup fails fast with a command hint instead of creating tables automatically.

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
