#!/usr/bin/env bash
# 快速參考: 執行路徑追蹤

cat << 'EOF'

╔════════════════════════════════════════════════════════════════════════════╗
║                    SEARCH_Goods 執行路徑追蹤快速參考                         ║
╚════════════════════════════════════════════════════════════════════════════╝

📚 三層執行路徑
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ⚡⚡ 超快速路徑 (5-10ms)
  ├─ 來自熱門分類 UI 的 L3 點擊
  ├─ from_hot_category: true
  ├─ L1、L2、L3 全指定
  └─ 直接過濾 L3，信任前端驗證

  ⚡ 快速路徑 (10-20ms)
  ├─ L3 Only 查詢
  ├─ 只有 L3，無 L1、L2
  ├─ from_hot_category: false
  └─ 直接過濾 L3

  🔍 完整路徑 (30-50ms+)
  ├─ 部分或全層級查詢 (L1/L1+L2/L1+L2+L3)
  ├─ 普通文字搜尋（可能觸發 LLM）
  └─ 逐層驗證層級關係

🚀 快速開始
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # 終端 1: 啟動後端
  cd backend
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  LOG_LEVEL=INFO python3 -m uvicorn app:app --reload --port 8000

  # 終端 2: 運行測試
  cd ..
  python3 test_execution_paths.py

🔍 關鍵日誌標誌
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🚀  程式啟動、初始化
  🔍  搜尋相關操作
  📊  配置、統計訊息
  📝  LLM 相關操作
  📦  函式呼叫
  🎯  層級過濾操作
  ⚡⚡  超快速路徑
  ⚡   快速路徑
  🔍  完整路徑
  ✅  成功
  ❌  失敗

📋 測試場景說明
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  測試 1: 熱門分類 UI L3 點擊
  ├─ from_hot_category: true
  ├─ L1=食品, L2=米麞, L3=米類
  └─ 預期: ⚡⚡ 超快速路徑

  測試 2: L3 Only 查詢
  ├─ from_hot_category: false
  ├─ L1="", L2="", L3=米類
  └─ 預期: ⚡ 快速路徑

  測試 3: 普通文字搜尋
  ├─ query: 有機米
  ├─ 無 category_hierarchy
  └─ 預期: 🔍 完整路徑 + LLM 意圖分析

  測試 4: 多層級查詢
  ├─ L1=食品, L2=穀類, L3=""
  ├─ from_hot_category: false
  └─ 預期: 🔍 完整路徑 + 逐層驗證

✅ 檢查清單
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  [ ] 後端啟動時看到模型配置日誌
  [ ] 看到「🚀 SEARCH_Goods 系統啟動」訊息
  [ ] 看到 SEARCH 和 CHAT 模型配置
  [ ] 運行測試腳本，看到 4 個不同的執行路徑
  [ ] 測試 1 顯示 ⚡⚡ 超快速路徑
  [ ] 測試 2 顯示 ⚡ 快速路徑
  [ ] 測試 3 看到 LLM 調用日誌
  [ ] 測試 4 看到逐層驗證日誌

🔧 環境變數控制
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # 日誌詳細程度
  LOG_LEVEL=DEBUG    # 最詳細（包含 DEBUG）
  LOG_LEVEL=INFO     # 標準（推薦）
  LOG_LEVEL=WARNING  # 最少

  # LLM 功能控制 (搜尋模型)
  SEARCH_USE_LLM_EXPAND=True    # 查詢擴展
  SEARCH_USE_LLM_INTENT=True    # 意圖分析
  SEARCH_USE_LLM_RERANK=False   # 結果重排

  # LLM 功能控制 (聊天模型)
  CHAT_USE_LLM_EXPAND=True      # 預設啟用
  CHAT_USE_LLM_INTENT=True      # 預設啟用
  CHAT_USE_LLM_PROMO=True       # 預設啟用

📁 相關檔案
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  EXECUTION_PATH_TRACKING_GUIDE.md  完整指南（詳細）
  test_execution_paths.py           測試腳本（自動化）
  backend/app.py                    主應用程式
  backend/llm_service.py            LLM 服務
  backend/goods_search_service.py   搜尋服務

💡 常見問題
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Q: 看不到日誌？
  A: 確認 LOG_LEVEL=INFO 或更低

  Q: 為什麼沒有 LLM 調用日誌？
  A: 檢查 OPENAI_API_KEY 和 SEARCH_USE_LLM_* 環境變數

  Q: 超快速路徑沒有觸發？
  A: 確認 from_hot_category: true 且 L1、L2、L3 全指定

  Q: 性能慢於預期？
  A: 可能是完整路徑 + LLM 調用，計算時間戳差異

🎯 路徑流程圖
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  API 請求
    │
    ├─ from_hot_category=true && L1 && L2 && L3?
    │  └─ YES → ⚡⚡ 超快速路徑 (直接 L3 過濾)
    │
    ├─ L3 && !L1 && !L2?
    │  └─ YES → ⚡ 快速路徑 (直接 L3 過濾)
    │
    └─ 其他
       └─ 🔍 完整路徑
          ├─ 調用 LLM 意圖分析（可選）
          ├─ 調用 LLM 查詢擴展（可選）
          ├─ 執行 search_products()
          └─ 逐層驗證 L1/L2/L3

═══════════════════════════════════════════════════════════════════════════════

更多細節見: EXECUTION_PATH_TRACKING_GUIDE.md

EOF
