#!/bin/bash
# 真人客服彈窗功能 - 快速測試腳本

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     真人客服彈窗功能 - 快速測試                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 1. 建立新的維修對話
echo "📝 步驟 1: 建立新的維修對話..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/repair/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "測試彈窗：餐桌的插座發熱怎麼辦",
    "history": [],
    "topn": 5
  }')

SESSION_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', ''))")

if [ -z "$SESSION_ID" ]; then
  echo "❌ 建立對話失敗"
  exit 1
fi

echo "✅ Session 建立成功: $SESSION_ID"
echo ""

# 2. 查詢初始狀態
echo "📝 步驟 2: 查詢初始狀態..."
curl -s "http://localhost:8000/api/repair/session/$SESSION_ID/status" | python3 -m json.tool
echo ""

# 3. 等待 2 秒
echo "⏳ 等待 2 秒..."
sleep 2

# 4. 切換為真人接手
echo "📝 步驟 3: 切換為真人接手..."
curl -s -X POST http://localhost:8000/api/repair/manual_mode \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"manual_mode\": true,
    \"operator_id\": \"TEST_OP\",
    \"operator_name\": \"測試客服小李\"
  }" | python3 -m json.tool
echo ""

# 5. 再次查詢狀態
echo "📝 步驟 4: 驗證狀態變更..."
curl -s "http://localhost:8000/api/repair/session/$SESSION_ID/status" | python3 -m json.tool
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ 測試完成！                                              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📱 現在請在瀏覽器中測試前端彈窗："
echo ""
echo "1️⃣  開啟首頁: http://localhost:8000/frontend/index.html"
echo "2️⃣  輸入維修問題並送出"
echo "3️⃣  開啟瀏覽器 Console (F12)，查看是否有以下日誌："
echo "    [Operator] 啟動輪詢 for session: ..."
echo "    [Operator] 開始輪詢 session: ..."
echo "    [Operator] 檢測到真人客服接手!"
echo ""
echo "4️⃣  3-5 秒內應看到右下角彈窗"
echo ""
echo "🔍 如果沒有彈窗，請檢查 Console 是否有錯誤訊息"
