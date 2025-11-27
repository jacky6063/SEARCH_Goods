#!/bin/bash
################################################################################
# CompanyResponseFormatter 網頁測試環境啟動腳本
################################################################################
# 執行方式: ./start_web_test.sh
################################################################################

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 切換到 script 所在目錄
cd "$(dirname "$0")"

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  🚀 CompanyResponseFormatter 網頁測試環境${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

# 檢查必要檔案
echo -e "\n${YELLOW}▶ 檢查必要檔案...${NC}"

FILES=(
    "company_response_formatter.py"
    "test_formatter_api.py"
    "test_formatter_web.html"
)

ALL_EXISTS=true
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}  ✓ $file${NC}"
    else
        echo -e "${RED}  ✗ $file (缺少)${NC}"
        ALL_EXISTS=false
    fi
done

if [ "$ALL_EXISTS" = false ]; then
    echo -e "\n${RED}錯誤: 缺少必要檔案，請確認檔案完整性${NC}"
    exit 1
fi

# 檢查 Python 套件
echo -e "\n${YELLOW}▶ 檢查 Python 環境...${NC}"

if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}  ⚠ FastAPI 未安裝，正在安裝...${NC}"
    pip3 install fastapi uvicorn
fi

if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo -e "${YELLOW}  ⚠ Uvicorn 未安裝，正在安裝...${NC}"
    pip3 install uvicorn
fi

echo -e "${GREEN}  ✓ Python 環境準備完成${NC}"

# 檢查 port 8000 是否被佔用
echo -e "\n${YELLOW}▶ 檢查端口可用性...${NC}"

if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}  ⚠ Port 8000 已被使用，嘗試關閉...${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 1
fi

echo -e "${GREEN}  ✓ Port 8000 可用${NC}"

# 啟動 API 伺服器 (背景執行)
echo -e "\n${YELLOW}▶ 啟動測試 API 伺服器...${NC}"

python3 test_formatter_api.py > /tmp/formatter_api.log 2>&1 &
API_PID=$!

# 等待 API 啟動
sleep 2

# 檢查 API 是否啟動成功
if kill -0 $API_PID 2>/dev/null; then
    echo -e "${GREEN}  ✓ API 伺服器啟動成功 (PID: $API_PID)${NC}"
else
    echo -e "${RED}  ✗ API 伺服器啟動失敗${NC}"
    echo -e "${YELLOW}  查看錯誤日誌: cat /tmp/formatter_api.log${NC}"
    exit 1
fi

# 等待 API 完全啟動
echo -e "\n${YELLOW}▶ 等待 API 服務就緒...${NC}"
for i in {1..10}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}  ✓ API 服務已就緒${NC}"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}  ✗ API 服務啟動超時${NC}"
        kill $API_PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

# 取得本機 IP
if command -v ipconfig >/dev/null 2>&1; then
    # macOS
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "127.0.0.1")
else
    # Linux
    LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "127.0.0.1")
fi

# 開啟瀏覽器
echo -e "\n${YELLOW}▶ 開啟測試網頁...${NC}"

HTML_PATH="$(pwd)/test_formatter_web.html"

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "$HTML_PATH"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$HTML_PATH"
    else
        echo -e "${YELLOW}  請手動開啟: $HTML_PATH${NC}"
    fi
else
    echo -e "${YELLOW}  請手動開啟: $HTML_PATH${NC}"
fi

# 顯示資訊
echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ 測試環境已啟動！${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "\n${YELLOW}📡 服務資訊:${NC}"
echo -e "  本機端: ${GREEN}http://localhost:8000${NC}"
echo -e "  區域網: ${GREEN}http://$LOCAL_IP:8000${NC}"
echo -e "  API 文檔: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  網頁介面: ${GREEN}file://$HTML_PATH${NC}"
echo -e "\n${YELLOW}🔧 管理指令:${NC}"
echo -e "  查看日誌: ${GREEN}tail -f /tmp/formatter_api.log${NC}"
echo -e "  停止服務: ${GREEN}kill $API_PID${NC}"
echo -e "\n${YELLOW}📝 使用說明:${NC}"
echo -e "  1. 瀏覽器會自動開啟測試網頁"
echo -e "  2. 點擊測試按鈕執行各項功能測試"
echo -e "  3. 查看格式化結果和 Rich Content 預覽"
echo -e "  4. 可使用 '全部測試' 按鈕執行完整測試套件"
echo -e "\n${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}按 Ctrl+C 停止服務${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}\n"

# 儲存 PID 以便後續清理
echo $API_PID > /tmp/formatter_api.pid

# 等待使用者中斷
trap "echo -e '\n${YELLOW}正在停止服務...${NC}'; kill $API_PID 2>/dev/null; rm -f /tmp/formatter_api.pid; echo -e '${GREEN}✓ 服務已停止${NC}'; exit 0" INT TERM

# 保持腳本運行
wait $API_PID
