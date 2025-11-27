#!/bin/bash

# SEARCH_Goods 開發環境停止腳本
# 使用方法: ./stop_dev.sh

# 顏色輸出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}停止開發服務...${NC}"

# 停止後端服務
pkill -f "uvicorn app:app"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 後端服務已停止${NC}"
else
    echo -e "  後端服務未運行"
fi

# 停止前端服務
pkill -f "python -m http.server 5173"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 前端服務已停止${NC}"
else
    echo -e "  前端服務未運行"
fi

echo ""
echo -e "${GREEN}開發環境已清理完成${NC}"
