#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV" ]; then
  echo "Virtualenv not found at $VENV. Create it with: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi
source "$VENV/bin/activate"
# ensure gunicorn is installed
if ! command -v gunicorn >/dev/null 2>&1; then
  echo "Installing gunicorn..."
  pip install 'gunicorn[uvicorn]' --upgrade
fi
# run gunicorn with the config file
exec gunicorn -c "$SCRIPT_DIR/gunicorn_conf.py" "app:app"
