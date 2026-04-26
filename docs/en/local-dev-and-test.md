# Manual Execution (No Docker)

If you prefer running without Docker, follow these steps:

## Prerequisites
* Python 3.14+
* `uv`
* Node.js 20+ (for building CSS)

## Quick Start
You can use the provided script to set up the environment, build CSS, and run the server:
```bash
./scripts/run_dev.sh
```

## Local Development Environment Values
For HTTP local development, set these values in `.env`:

```dotenv
WEB_USERNAME=admin
WEB_PASSWORD=$argon2id$...
BOOTSTRAP_ALLOW_INSECURE_DEFAULTS=true
SESSION_COOKIE_SECURE=false
API_DOCS_ENABLED=true
CORS_ALLOW_ALL=true
```

`WEB_USERNAME` and `WEB_PASSWORD` are only used when bootstrapping the first user into an empty database.

## Manual Steps
1. **Set up Python Environment**:
   ```bash
   uv sync
   ```

2. **Build UI Assets**:
   ```bash
   cd ui-build
   npm ci
   npm run build
   cd ..
   ```
   `./scripts/run_dev.sh` automatically skips `npm ci` when `ui-build/node_modules` already exists.

3. **Run Server**:
   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8000
   ```

App startup creates the current database schema automatically when the database is empty. Existing Alembic/legacy databases are rejected; back up and remove `share/database.db` before starting this version.

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
```

## Quality Checks
The GitHub Actions quality workflow runs these checks:

```bash
uv sync --frozen
uv run pytest -q
uvx --from ruff==0.15.12 ruff check .

# informational Python dependency audit
uv export --format requirements.txt --no-dev --no-emit-project --no-hashes --frozen --output-file /tmp/teledrop-requirements.txt
uvx --from pip-audit==2.10.0 pip-audit --requirement /tmp/teledrop-requirements.txt --strict --no-deps --disable-pip --progress-spinner off

cd ui-build
npm ci
npm run build
npm audit --audit-level=high
```

Docker builds use `npm ci` for the CSS build stage and pin the uv image to `0.11.7`.
