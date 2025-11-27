#!/bin/bash

# SEARCH_Goods 開發環境啟動腳本
# 使用方法: ./start_dev.sh

# 顏色輸出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 檢查是否在正確的目錄
if [ ! -f "backend/app.py" ]; then
    echo -e "${RED}錯誤: 請在 SEARCH_Goods 根目錄執行此腳本${NC}"
    exit 1
fi

# 停止現有的服務
echo -e "${YELLOW}停止現有服務...${NC}"
pkill -f "uvicorn app:app" 2>/dev/null
pkill -f "python -m http.server 5173" 2>/dev/null
sleep 2

# 檢查 Python 虛擬環境
if [ ! -d "backend/.venv" ]; then
    echo -e "${RED}錯誤: 找不到虛擬環境，請先執行: cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi

# 啟動後端服務
echo -e "${GREEN}啟動後端服務 (Port 8000)...${NC}"
cd backend
source .venv/bin/activate

# 排除 .venv 目錄避免不必要的重載
uvicorn app:app --reload --reload-exclude '.venv/*' --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# 等待後端啟動
sleep 3

# 檢查後端是否成功啟動
if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN}✓ 後端服務啟動成功 (PID: $BACKEND_PID)${NC}"
    echo -e "  URL: http://localhost:8000"
    echo -e "  健康檢查: http://localhost:8000/health"
else
    echo -e "${RED}✗ 後端服務啟動失敗，請檢查 backend.log${NC}"
    tail -20 backend.log
    exit 1
fi

# 啟動前端服務
echo -e "${GREEN}啟動前端服務 (Port 5173)...${NC}"
cd frontend
python3 -m http.server 5173 > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# 等待前端啟動
sleep 2

# 檢查前端是否成功啟動
if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN}✓ 前端服務啟動成功 (PID: $FRONTEND_PID)${NC}"
    echo -e "  URL: http://localhost:5173"
else
    echo -e "${RED}✗ 前端服務啟動失敗，請檢查 frontend.log${NC}"
    exit 1
fi

# 顯示狀態摘要
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   開發環境啟動完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "📱 前端: ${YELLOW}http://localhost:5173${NC}"
echo -e "🔧 後端: ${YELLOW}http://localhost:8000${NC}"
echo -e "❤️  健康檢查: ${YELLOW}http://localhost:8000/health${NC}"
echo ""
echo -e "後端 PID: $BACKEND_PID (自動重載已啟用)"
echo -e "前端 PID: $FRONTEND_PID"
echo ""
echo -e "${YELLOW}停止服務:${NC}"
echo -e "  pkill -f 'uvicorn app:app'"
echo -e "  pkill -f 'python -m http.server 5173'"
echo ""
echo -e "${YELLOW}查看日誌:${NC}"
echo -e "  tail -f backend.log"
echo -e "  tail -f frontend.log"
echo ""
