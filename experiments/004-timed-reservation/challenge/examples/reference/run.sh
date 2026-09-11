#!/bin/sh
# python3 where present; this cell (FreeBSD 15.1) ships only python3.12
PY=$(command -v python3 || command -v python3.12) || { echo "FATAL: no python3" >&2; exit 2; }
exec "$PY" "$(dirname "$0")/reservation.py" "$@"
