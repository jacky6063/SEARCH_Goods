#!/usr/bin/env bash
# helper to start backend gunicorn with ADMIN_TOKEN set
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV" ]; then
  echo "Virtualenv not found at $VENV. Create it with: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi
if [ -z "${1:-}" ]; then
  echo "Usage: $0 <ADMIN_TOKEN>"
  exit 2
fi
ADMIN_TOKEN="$1"
export ADMIN_TOKEN
source "$VENV/bin/activate"
if ! command -v gunicorn >/dev/null 2>&1; then
  echo "Installing gunicorn..."
  pip install 'gunicorn[uvicorn]' --upgrade
fi
exec gunicorn -c "$SCRIPT_DIR/gunicorn_conf.py" "app:app"
