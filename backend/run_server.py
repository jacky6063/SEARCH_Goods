#!/usr/bin/env python3
import uvicorn
import sys
import os

# 確保當前目錄在路徑中
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
