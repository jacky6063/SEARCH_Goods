#!/bin/bash
# SEARCH_Goods 地端部署狀態檢查腳本
# 用於快速確認本地部署是否正常運作

echo "🔍 SEARCH_Goods 地端部署狀態檢查"
echo "=========================================="
echo ""

# 檢查後端服務
echo "1️⃣  檢查後端服務 (Port 8000)"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    health=$(curl -s http://localhost:8000/health)
    echo "   ✅ 後端服務運行中"
    echo "   狀態: $health"
else
    echo "   ❌ 後端服務未運行"
fi
echo ""

# 檢查前端服務
echo "2️⃣  檢查前端服務 (Port 5173)"
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "   ✅ 前端服務運行中"
    echo "   訪問: http://localhost:5173"
else
    echo "   ❌ 前端服務未運行"
fi
echo ""

# 檢查資料檔案
echo "3️⃣  檢查資料檔案"
if [ -f "data/VIEW_GOODS_enhanced.csv" ]; then
    lines=$(wc -l < data/VIEW_GOODS_enhanced.csv)
    size=$(du -h data/VIEW_GOODS_enhanced.csv | cut -f1)
    echo "   ✅ 商品資料檔案存在"
    echo "   大小: $size, 行數: $lines"
else
    echo "   ❌ 商品資料檔案不存在"
fi
echo ""

# 檢查環境變數
echo "4️⃣  檢查環境配置"
if [ -f "backend/.env" ] || [ -f ".env" ]; then
    echo "   ✅ 環境變數檔案存在"
    if grep -q "OPENAI_API_KEY" backend/.env 2>/dev/null || grep -q "OPENAI_API_KEY" .env 2>/dev/null; then
        echo "   ✅ OpenAI API Key 已配置"
    else
        echo "   ⚠️  OpenAI API Key 未配置（LLM 功能將無法使用）"
    fi
else
    echo "   ❌ 環境變數檔案不存在"
fi
echo ""

# 檢查進程
echo "5️⃣  檢查服務進程"
backend_pid=$(ps aux | grep -E "uvicorn.*app:app" | grep -v grep | awk '{print $2}' | head -1)
frontend_pid=$(ps aux | grep -E "http.server.*5173" | grep -v grep | awk '{print $2}' | head -1)

if [ -n "$backend_pid" ]; then
    echo "   ✅ 後端進程 (PID: $backend_pid)"
else
    echo "   ❌ 後端進程未找到"
fi

if [ -n "$frontend_pid" ]; then
    echo "   ✅ 前端進程 (PID: $frontend_pid)"
else
    echo "   ❌ 前端進程未找到"
fi
echo ""

# 測試搜尋功能
echo "6️⃣  測試搜尋功能"
search_result=$(curl -s -X POST http://localhost:8000/api/search \
    -H "Content-Type: application/json" \
    -d '{"query":"米","mode":"search"}' 2>/dev/null)

if [ $? -eq 0 ]; then
    product_count=$(echo "$search_result" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data.get('items',[])))" 2>/dev/null)
    if [ -n "$product_count" ]; then
        echo "   ✅ 搜尋功能正常 (找到 $product_count 個產品)"
    else
        echo "   ⚠️  搜尋功能回應異常"
    fi
else
    echo "   ❌ 搜尋功能測試失敗"
fi
echo ""

echo "=========================================="
echo "🎉 檢查完成！"
echo ""
echo "📝 快速操作指令："
echo "   - 查看後端日誌: tail -f backend/backend.log"
echo "   - 查看前端日誌: tail -f frontend/frontend.log"
echo "   - 停止服務: kill $backend_pid $frontend_pid"
echo "   - 重啟服務: ./start_local_dev.sh"
echo ""
