#!/bin/bash
# =====================================================
# 本地測試環境啟動腳本
# =====================================================
# 用途：啟動後端和前端服務，執行完整測試套件
# 使用：./scripts/test_local.sh
# =====================================================

set -e  # 遇到錯誤立即停止

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日誌函數
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# 清理函數
cleanup() {
    log_info "清理測試環境..."
    
    # 停止後端
    if [ ! -z "$BACKEND_PID" ] && kill -0 $BACKEND_PID 2>/dev/null; then
        log_info "停止後端服務 (PID: $BACKEND_PID)"
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    # 停止前端
    if [ ! -z "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
        log_info "停止前端服務 (PID: $FRONTEND_PID)"
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    log_success "清理完成"
}

# 設定 trap 以確保清理
trap cleanup EXIT INT TERM

# 檢查必要文件
log_info "檢查必要文件..."

if [ ! -f "backend/app.py" ]; then
    log_error "找不到 backend/app.py"
    exit 1
fi

if [ ! -f "frontend/index.html" ]; then
    log_error "找不到 frontend/index.html"
    exit 1
fi

if [ ! -f "data/VIEW_GOODS_enhanced.csv" ]; then
    log_error "找不到資料檔案 data/VIEW_GOODS_enhanced.csv"
    exit 1
fi

log_success "所有必要文件都存在"

# 檢查 Python 虛擬環境
log_info "檢查 Python 環境..."

if [ ! -d "backend/.venv" ]; then
    log_warning "虛擬環境不存在，正在創建..."
    cd backend
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cd ..
    log_success "虛擬環境創建完成"
fi

# 啟動後端服務
log_info "啟動後端服務 (Port 8000)..."
cd backend
source .venv/bin/activate
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --log-level info > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

log_info "後端 PID: $BACKEND_PID"

# 等待後端啟動
log_info "等待後端服務啟動..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_success "後端服務已就緒"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "後端服務啟動超時"
        exit 1
    fi
    sleep 1
done

# 啟動前端服務
log_info "啟動前端服務 (Port 5173)..."
cd frontend
python3 -m http.server 5173 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

log_info "前端 PID: $FRONTEND_PID"

# 等待前端啟動
log_info "等待前端服務啟動..."
sleep 3
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    log_success "前端服務已就緒"
else
    log_error "前端服務啟動失敗"
    exit 1
fi

# 顯示服務狀態
echo ""
log_success "=========================================="
log_success "✨ 測試環境已就緒"
log_success "=========================================="
echo ""
log_info "後端: http://localhost:8000"
log_info "前端: http://localhost:5173"
log_info "API 文檔: http://localhost:8000/docs"
echo ""

# 執行測試（可選）
if [ "$1" = "--test" ]; then
    log_info "執行測試套件..."
    
    # E2E 測試
    log_info "執行 E2E 測試..."
    npm run test:e2e
    
    # Backend 測試
    log_info "執行後端測試..."
    cd backend
    source .venv/bin/activate
    pytest -v
    cd ..
    
    log_success "所有測試完成"
    exit 0
fi

# 互動模式
log_info "測試環境運行中..."
echo ""
log_warning "按 Ctrl+C 停止服務"
echo ""
log_info "可用指令："
echo "  - 查看後端日誌: tail -f logs/backend.log"
echo "  - 查看前端日誌: tail -f logs/frontend.log"
echo "  - 執行 E2E 測試: npm run test:e2e"
echo "  - 執行後端測試: cd backend && pytest"
echo ""

# 保持腳本運行
wait $BACKEND_PID $FRONTEND_PID
