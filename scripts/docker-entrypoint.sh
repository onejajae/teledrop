#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APP_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
ALEMBIC_INI="$APP_ROOT/alembic.ini"

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

if [ "$1" = "uvicorn" ]; then
  echo "Running Alembic migrations..."
  alembic -c "$ALEMBIC_INI" upgrade head
fi

exec "$@"
