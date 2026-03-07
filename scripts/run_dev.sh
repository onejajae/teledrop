#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

echo "Setting up Teledrop for manual execution..."

# 1. Python Environment
if ! command -v uv &> /dev/null; then
    echo "❌ uv is required. Install uv and retry."
    exit 1
fi

echo "Syncing Python dependencies with uv..."
uv sync

prepare_runtime_dirs() {
    uv run python - <<'PY'
from pathlib import Path

from app.bootstrap.runtime_paths import sqlite_parent_dir_from_url
from app.core.config import get_settings

settings = get_settings()
Path(settings.SHARE_DIRECTORY).mkdir(parents=True, exist_ok=True)
sqlite_dir = sqlite_parent_dir_from_url(settings.SQLITE_HOST)
if sqlite_dir is not None:
    sqlite_dir.mkdir(parents=True, exist_ok=True)
PY
}

# 2. Database migrations
echo "Preparing runtime directories..."
prepare_runtime_dirs
echo "Applying Alembic migrations..."
uv run alembic -c alembic.ini upgrade head

# 3. Tailwind CSS
echo "Building Tailwind CSS..."
if [ ! -d "ui-build/node_modules" ]; then
    echo "Installing Node dependencies..."
    (cd ui-build && npm install)
fi
(cd ui-build && npm run build:css)

# 4. Running Server
echo "Starting server..."
echo "Open http://localhost:8000 in your browser"
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
