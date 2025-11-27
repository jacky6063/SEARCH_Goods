# ✨ 執行路徑追蹤 - 快速入門

## 🎯 你現在擁有什麼？

**程式現在可以清晰展示執行路徑！** 

三種執行路徑會根據查詢類型自動選擇：
- ⚡⚡ 超快速 (5-10ms) - 熱門分類 UI L3 點擊
- ⚡ 快速 (10-20ms) - L3 Only 查詢  
- 🔍 完整 (30-50ms+) - 其他查詢 + LLM

## 🚀 1 分鐘開始

### 步驟 1: 啟動後端（帶日誌）
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
LOG_LEVEL=INFO python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 步驟 2: 運行測試（另一個終端）
```bash
cd /path/to/SEARCH_Goods
python3 test_execution_paths.py
```

**就這樣！** 在後端終端看執行日誌。

## 📚 文檔指南

| 文檔 | 用途 | 何時閱讀 |
|------|------|--------|
| **QUICK_REFERENCE.sh** | 快速參考卡片 | 快速查找 (`./QUICK_REFERENCE.sh`) |
| **EXECUTION_TRACKING_README.md** | 入門指南 | 第一次使用 |
| **EXECUTION_PATH_TRACKING_GUIDE.md** | 完整詳細 | 深入學習 |
| **EXECUTION_TRACKING_DELIVERY.md** | 交付清單 | 了解全貌 |

## 🔍 看到什麼？

程式啟動時：
```
🚀 SEARCH_Goods 系統啟動
📊 搜尋模型配置:
  - 模型: gpt-4o-mini
  - 查詢擴展: False
💬 聊天模型配置:
  - 模型: gpt-4o-mini
  - 查詢擴展: True
```

搜尋時（熱門分類 UI）：
```
🔍 /api/search 端點被觸發
📦 調用 search_products() 進行基礎搜尋
  ✅ 搜尋到 150 筆記錄
🎯 套用層級分類過濾
  ⚡⚡ 執行超快速路徑（熱門分類 UI L3 直接過濾）
  ✅ 超快速路徑結果: 23 筆
```

## 🧪 4 個測試場景

`test_execution_paths.py` 會自動發送 4 種查詢：

1. **熱門分類 UI** → ⚡⚡ 超快速 (5-10ms)
2. **L3 Only** → ⚡ 快速 (10-20ms)
3. **文字搜尋** → 🔍 完整 (30-50ms+)
4. **多層級** → 🔍 完整 + 逐層驗證

## 💡 核心概念

### 兩個模型系統

```
搜尋模型                    聊天模型
(SEARCH_*)                 (CHAT_*)
  ├─ 可選啟用 LLM             ├─ 預設啟用 LLM
  ├─ 查詢擴展                 ├─ 查詢擴展
  ├─ 意圖分析                 ├─ 意圖分析
  └─ 結果重排                 └─ 行銷推廣
```

### 三層路徑邏輯

```
檢查 from_hot_category && L1 && L2 && L3?
  YES → ⚡⚡ 超快速
  NO → 檢查 L3 && 無 L1 && 無 L2?
       YES → ⚡ 快速
       NO → 🔍 完整
```

## ⚙️ 環境變數

```bash
# 日誌詳細程度
LOG_LEVEL=INFO              # 推薦

# LLM 功能（搜尋模型）
SEARCH_USE_LLM_INTENT=False # 意圖分析
SEARCH_USE_LLM_EXPAND=False # 查詢擴展

# LLM 功能（聊天模型）
CHAT_USE_LLM_INTENT=True    # 預設啟用
CHAT_USE_LLM_EXPAND=True    # 預設啟用
```

## 🎁 交付內容

| 項目 | 數量 |
|------|------|
| 日誌記錄點 | 11 個 |
| 文檔 | 4 份 |
| 測試場景 | 4 個 |
| Git 提交 | 6 個 |
| 代碼行數 | ~300 行 |

## ❓ 常見問題

**Q: 看不到日誌？**
```bash
LOG_LEVEL=INFO python3 -m uvicorn app:app --reload
```

**Q: 想看 LLM 調用？**
```bash
SEARCH_USE_LLM_INTENT=True python3 -m uvicorn app:app --reload
```

**Q: 超快速路徑沒觸發？**
確認 `from_hot_category: true` 且 L1、L2、L3 都指定

## 🏆 立即試用

```bash
# 1. 啟動後端
cd backend && LOG_LEVEL=INFO python3 -m uvicorn app:app --reload

# 2. 在另一個終端運行
python3 test_execution_paths.py

# 3. 看到不同的執行路徑！
```

---

**就是這樣！現在你可以清晰看到程式如何執行。** 🎯

更多細節見其他文檔。祝追蹤愉快！ 🚀
