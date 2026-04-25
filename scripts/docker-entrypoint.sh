#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APP_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

# docker compose command can be provided as a single string (e.g. "--workers 2")
# Split that form so uvicorn receives proper argv tokens.
if [ "$#" -eq 1 ]; then
  case "$1" in
    -*" "*)
      # shellcheck disable=SC2086
      set -- $1
      ;;
  esac
fi

if [ "$#" -eq 0 ] || [ "${1#-}" != "$1" ]; then
  set -- uvicorn main:app --host 0.0.0.0 --no-server-header "$@"
fi

prepare_runtime_dirs() {
  python - <<'PY'
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

if [ "$1" = "uvicorn" ]; then
  echo "Preparing runtime directories..."
  prepare_runtime_dirs
fi

exec "$@"
