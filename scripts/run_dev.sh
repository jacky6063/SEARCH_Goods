#!/usr/bin/env bash
set -euo pipefail
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
fi
if [ -f "requirements_hotfix.txt" ]; then
  pip install -r requirements_hotfix.txt
fi
cd backend
export DATA_PATH="${DATA_PATH:-../data/VIEW_GOODS_enhanced.csv}"
export USE_LLM_RERANK="${USE_LLM_RERANK:-false}"
export USE_LLM_PROMO="${USE_LLM_PROMO:-false}"
uvicorn app:app --reload --port 8000
