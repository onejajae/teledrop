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

# 2. Tailwind CSS
echo "Building Tailwind CSS..."
if [ ! -d "ui-build/node_modules" ]; then
    echo "Installing Node dependencies..."
    (cd ui-build && npm install)
fi
(cd ui-build && npm run build:css)

# 3. Running Server
echo "Starting server..."
echo "Open http://localhost:8000 in your browser"
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
