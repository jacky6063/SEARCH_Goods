#!/bin/bash
cd /Users/huangchangchi/Documents/SEARCH_Goods/backend
export PYTHONPATH=/Users/huangchangchi/Documents/SEARCH_Goods/backend:$PYTHONPATH
python3 -m uvicorn app:app --host 127.0.0.1 --port 8000
