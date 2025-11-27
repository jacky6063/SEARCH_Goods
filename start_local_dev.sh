#!/bin/bash
# 本地開發環境一鍵啟動腳本
# 解決常見的地端設定問題

set -e  # 遇到錯誤立即退出

echo "🔧 SEARCH_Goods 本地開發環境啟動"
echo "=================================="

# 檢查當前目錄
if [ ! -f "backend/app.py" ]; then
    echo "❌ 錯誤: 請在專案根目錄執行此腳本"
    exit 1
fi

# 1. 清理舊進程
echo ""
echo "🧹 步驟 1/5: 清理舊進程..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || echo "   ✓ Port 8000 已清空"
lsof -ti:5173 | xargs kill -9 2>/dev/null || echo "   ✓ Port 5173 已清空"

# 2. 檢查並啟動虛擬環境
echo ""
echo "🐍 步驟 2/5: 檢查 Python 虛擬環境..."
if [ ! -d "backend/.venv" ]; then
    echo "   創建虛擬環境..."
    cd backend
    python3 -m venv .venv
    cd ..
fi

# 3. 檢查必要套件
echo ""
echo "📦 步驟 3/5: 檢查必要套件..."
source backend/.venv/bin/activate

# 檢查 supabase 套件
if ! python -c "import supabase" 2>/dev/null; then
    echo "   ⚠️  缺少 supabase 套件,正在安裝..."
    pip install supabase==2.24.0 -q
    echo "   ✓ supabase 套件已安裝"
else
    echo "   ✓ supabase 套件已存在"
fi

# 檢查其他必要套件
if ! python -c "import fastapi" 2>/dev/null; then
    echo "   ⚠️  缺少依賴套件,正在完整安裝..."
    cd backend
    pip install -r requirements.txt -q
    cd ..
    echo "   ✓ 所有依賴套件已安裝"
else
    echo "   ✓ FastAPI 套件已存在"
fi

# 4. 檢查環境變數
echo ""
echo "🔐 步驟 4/5: 檢查環境變數..."
if [ ! -f ".env" ]; then
    echo "   ⚠️  .env 檔案不存在!"
    if [ -f ".env.example" ]; then
        echo "   請複製 .env.example 並填入真實憑證:"
        echo "   cp .env.example .env"
        echo "   然後編輯 .env 檔案"
        exit 1
    else
        echo "   ❌ 錯誤: 找不到 .env.example 範本"
        exit 1
    fi
else
    echo "   ✓ .env 檔案存在"
fi

# 5. 啟動服務
echo ""
echo "🚀 步驟 5/5: 啟動服務..."
echo ""
echo "   後端服務: http://localhost:8000"
echo "   前端服務: http://localhost:5173"
echo ""
echo "   按 Ctrl+C 停止服務"
echo "=================================="
echo ""

# 啟動後端
cd backend
nohup uvicorn app:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "✓ 後端服務已啟動 (PID: $BACKEND_PID)"

# 等待後端完全啟動
echo "   等待後端服務啟動..."
for i in {1..15}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo "   ✓ 後端服務健康檢查通過"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "   ⚠️  後端啟動超時,請檢查 backend/backend.log"
        tail -20 backend.log
        exit 1
    fi
    sleep 1
done

cd ..

# 啟動前端
cd frontend
nohup python3 -m http.server 5173 > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✓ 前端服務已啟動 (PID: $FRONTEND_PID)"
cd ..

echo ""
echo "🎉 啟動完成!"
echo ""
echo "📝 查看日誌:"
echo "   後端: tail -f backend/backend.log"
echo "   前端: tail -f frontend/frontend.log"
echo ""
echo "🛑 停止服務:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""

# 持續顯示後端日誌
tail -f backend/backend.log
