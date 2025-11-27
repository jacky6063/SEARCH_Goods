# 🎯 程式執行路徑追蹤

**現在你可以清晰看到程式實際執行的路徑！**

## 📖 文檔結構

| 文檔 | 用途 | 讀者 |
|------|------|------|
| **QUICK_REFERENCE.sh** | 視覺化快速參考卡片 | 快速查找（運行 `./QUICK_REFERENCE.sh`） |
| **EXECUTION_PATH_TRACKING_GUIDE.md** | 完整詳細指南 | 想深入理解的人 |
| **test_execution_paths.py** | 自動化測試腳本 | 想驗證不同路徑的人 |

## 🚀 30 秒快速開始

```bash
# 終端 1: 啟動後端（帶日誌）
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
LOG_LEVEL=INFO python3 -m uvicorn app:app --reload --port 8000

# 終端 2: 運行測試
cd ..
python3 test_execution_paths.py
```

**觀看後端終端機，你會看到 4 種不同的執行路徑！**

## 🎯 三層執行路徑

| 路徑 | 速度 | 場景 | 特徵 |
|------|------|------|------|
| ⚡⚡ 超快速 | 5-10ms | 熱門分類 UI L3 點擊 | `from_hot_category: true` + L1/L2/L3 全指定 |
| ⚡ 快速 | 10-20ms | L3 Only 查詢 | 只指定 L3，無 L1/L2 |
| 🔍 完整 | 30-50ms+ | 其他查詢 | 部分/全層級 + LLM（可選） |

## 📊 日誌亮點

程式啟動時：
```
🚀 SEARCH_Goods 系統啟動
📊 搜尋模型配置:
  - 模型: gpt-4o-mini
  - 查詢擴展: True/False
  - 意圖分析: True/False
💬 聊天模型配置:
  - 模型: gpt-4o-mini
  - 查詢擴展: True
  - 意圖分析: True
```

搜尋時：
```
🔍 /api/search 端點被觸發
  查詢: '...'
  來自熱門分類 UI: True/False

📦 調用 search_products() 進行基礎搜尋
  ✅ 搜尋到 150 筆記錄

🎯 套用層級分類過濾
  ⚡⚡ 執行超快速路徑（熱門分類 UI L3 直接過濾）
    ✅ 超快速路徑結果: 23 筆
```

## 🧪 測試場景

`test_execution_paths.py` 發送 4 個測試請求：

1. **熱門分類 UI L3 點擊** → ⚡⚡ 超快速路徑 (5-10ms)
2. **L3 Only 查詢** → ⚡ 快速路徑 (10-20ms)
3. **普通文字搜尋** → 🔍 完整路徑 + LLM (30-50ms+)
4. **多層級階層查詢** → 🔍 完整路徑 + 逐層驗證 (30-50ms+)

## 💡 核心概念

### 兩個模型系統

| 模型 | 配置前綴 | 啟用場景 | 用途 |
|------|--------|--------|------|
| **搜尋模型** | `SEARCH_USE_*` | 環境變數可控 | 產品搜尋時的 AI 功能 |
| **聊天模型** | `CHAT_USE_*` | 預設全啟用 | 聊天介面的 AI 對話 |

### 三層策略邏輯

```
請求進來
  ↓
檢查 from_hot_category && L1 && L2 && L3 全存在？
  ├─ YES → ⚡⚡ 直接過濾 L3（信任前端驗證）
  └─ NO
      ↓
  檢查 L3 && 無 L1 && 無 L2？
    ├─ YES → ⚡ 直接過濾 L3
    └─ NO
        ↓
    🔍 完整路徑（可能 LLM + 逐層驗證）
```

## 📝 環境變數參考

```bash
# 日誌詳細程度（重要！）
LOG_LEVEL=INFO          # 標準（推薦）
LOG_LEVEL=DEBUG         # 最詳細
LOG_LEVEL=WARNING       # 最少

# 搜尋模型 LLM 功能（可選）
SEARCH_USE_LLM_EXPAND=False    # 查詢擴展
SEARCH_USE_LLM_INTENT=False    # 意圖分析
SEARCH_USE_LLM_RERANK=False    # 結果重排

# 聊天模型 LLM 功能（預設啟用）
CHAT_USE_LLM_EXPAND=True
CHAT_USE_LLM_INTENT=True
CHAT_USE_LLM_PROMO=True

# OpenAI 配置
OPENAI_API_KEY=sk-...          # 若要使用 LLM
SEARCH_OPENAI_MODEL=gpt-4o-mini
CHAT_OPENAI_MODEL=gpt-4o-mini
```

## ✅ 檢查清單

執行測試後，確認你看到：

- [ ] 後端啟動時有 `🚀 SEARCH_Goods 系統啟動` 訊息
- [ ] 看到 SEARCH 和 CHAT 模型配置
- [ ] 測試 1 看到 `⚡⚡ 超快速路徑`
- [ ] 測試 2 看到 `⚡ 快速路徑`
- [ ] 測試 3 看到 LLM 調用日誌（如果啟用）
- [ ] 測試 4 看到 `🔍 完整路徑` 和逐層驗證

## 🔍 關鍵檔案說明

| 檔案 | 日誌點 |
|------|-------|
| `backend/app.py` | 啟動、API 端點、LLM 調用、層級過濾 |
| `backend/llm_service.py` | 意圖分析、查詢擴展 |
| `backend/goods_search_service.py` | 基礎搜尋 |

## 🐛 故障排查

**Q: 看不到日誌？**
```bash
LOG_LEVEL=INFO python3 -m uvicorn app:app --reload
```

**Q: 為什麼沒有 LLM 日誌？**
```bash
SEARCH_USE_LLM_EXPAND=True SEARCH_USE_LLM_INTENT=True \
  python3 -m uvicorn app:app --reload
```

**Q: 超快速路徑沒有觸發？**
確認請求中有 `from_hot_category: true` 且 L1、L2、L3 都指定。

## 📚 深入學習

想了解更多？查看：
- `EXECUTION_PATH_TRACKING_GUIDE.md` - 完整詳細指南
- `test_execution_paths.py` - 測試程式碼（可自訂）
- `backend/app.py` 第 430-690 行 - 日誌代碼位置

## 🎓 學習路徑

1. **新手** → 運行 `test_execution_paths.py`，觀察日誌
2. **進階** → 讀 `EXECUTION_PATH_TRACKING_GUIDE.md`
3. **開發者** → 修改 `test_execution_paths.py` 或加自己的日誌

---

**祝你追蹤愉快！** 🎯

有任何問題，檢查 `EXECUTION_PATH_TRACKING_GUIDE.md` 的故障排查章節。
