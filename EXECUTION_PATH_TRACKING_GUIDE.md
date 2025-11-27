# 執行路徑追蹤指南

## 概述

你現在可以看到程式實際執行的路徑！我已經在關鍵位置加入了詳細的日誌記錄，讓你能清楚地追蹤每個請求經過哪些函式、採用了哪些策略。

## 三層執行路徑策略

程式根據不同的查詢場景，會執行三種不同的過濾策略：

### 1️⃣ 超快速路徑 ⚡⚡ （來自熱門分類 UI 的 L3 點擊）

**特徵**：
- `from_hot_category: true` 標誌
- L1、L2、L3 都已指定
- 前端已驗證層級關係

**執行時間**：5-10ms

**日誌特徵**：
```
🎯 套用層級分類過濾
  - 來自熱門分類 UI: True
    ⚡⚡ 執行超快速路徑（熱門分類 UI L3 直接過濾）
    ✅ 超快速路徑結果: X 筆
```

---

### 2️⃣ 快速路徑 ⚡ （L3 Only 查詢）

**特徵**：
- 只指定了 L3
- 沒有 L1、L2
- 不來自熱門分類 UI

**執行時間**：10-20ms

**日誌特徵**：
```
🎯 套用層級分類過濾
  - 來自熱門分類 UI: False
    ⚡ 執行快速路徑（L3 Only 直接過濾）
    ✅ 快速路徑結果: X 筆
```

---

### 3️⃣ 完整路徑 🔍 （其他查詢）

**特徵**：
- 部分或全部層級查詢（L1 Only、L1+L2、L1+L2+L3 等）
- 普通文字搜尋（可能觸發 LLM）
- 逐層驗證層級關係

**執行時間**：30-50ms

**日誌特徵**：
```
📝 LLM 搜尋模型配置:
  - 查詢擴展啟用: True/False
  - 意圖分析啟用: True/False
  ...
    📋 llm_analyze_query() 被呼叫
      - 意圖分析啟用: True
      - 呼叫 OpenAI API 進行意圖分析
      ✅ 意圖分析結果: {...}
    
    📝 llm_expand_query() 被呼叫
      - 查詢擴展啟用: True
      - 呼叫 OpenAI API
      ✅ 擴展結果: ...

🔍 執行完整路徑（逐層驗證）
✅ 完整路徑結果: X 筆
```

---

## 快速開始

### 方式 1: 使用測試腳本（推薦）

```bash
# 終端 1: 啟動後端
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app:app --reload --port 8000

# 終端 2: 運行測試腳本
cd /path/to/SEARCH_Goods
python3 test_execution_paths.py
```

測試腳本會發送 4 個不同的請求：
1. ⚡⚡ 熱門分類 UI L3 點擊
2. ⚡ L3 Only 查詢
3. 🔍 普通文字搜尋（完整路徑 + LLM）
4. 🔍 多層級階層查詢

觀察後端終端機的日誌，你會看到不同的執行路徑被觸發。

### 方式 2: 手動使用 curl 測試

```bash
# 測試 1: 熱門分類 UI 路徑（超快速）
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "食品 米麞 米類",
    "category_hierarchy": {"L1": "食品", "L2": "米麞", "L3": "米類"},
    "from_hot_category": true,
    "page": 1,
    "page_size": 5
  }'

# 測試 2: L3 Only 查詢（快速）
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "米類",
    "category_hierarchy": {"L1": "", "L2": "", "L3": "米類"},
    "page": 1,
    "page_size": 5
  }'

# 測試 3: 普通文字搜尋（完整路徑 + LLM）
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "有機米", "page": 1, "page_size": 5}'
```

---

## 日誌位置和內容

### 1. 程式啟動日誌

啟動時，你會看到：

```
================================================================================
🚀 SEARCH_Goods 系統啟動
================================================================================
📊 搜尋模型配置:
  - 模型: gpt-4o-mini
  - 查詢擴展 (LLM_EXPAND): False
  - 意圖分析 (LLM_INTENT): False
  - 結果重排 (LLM_RERANK): False
💬 聊天模型配置:
  - 模型: gpt-4o-mini
  - 查詢擴展 (LLM_EXPAND): True
  - 意圖分析 (LLM_INTENT): True
  - 行銷推廣 (LLM_PROMO): True
================================================================================
```

這展示了兩個模型系統的初始化狀態。

### 2. 搜尋請求日誌

每個搜尋請求會輸出：

```
--------------------------------------------------------------------------------
🔍 /api/search 端點被觸發
  查詢: '...'
  分類階層: {...}
  來自熱門分類 UI: True/False
  頁碼: 1, 每頁筆數: 5
```

### 3. LLM 調用日誌

當啟用 LLM 功能時：

```
📝 LLM 搜尋模型配置:
  - 查詢擴展啟用: True/False
  - 意圖分析啟用: True/False
  - 結果重排啟用: True/False
  ➡️ 調用 llm_analyze_query() 進行意圖分析
  ✅ 意圖分析結果: {...}
  ➡️ 調用 llm_expand_query() 進行查詢擴展
  ✅ 擴展查詢: '...'
```

### 4. 搜尋和過濾日誌

```
🔎 搜尋參數:
  - 展開查詢: '...'
  - 必需詞: [...]
  - 排除詞: [...]
  - 分類層級: {...}

📦 調用 search_products() 進行基礎搜尋
    🔎 search_products() 被呼叫
      - 查詢: '...'
      - 必需詞: [...], 類別詞: [...], 排除詞: [...]
  ✅ 搜尋到 X 筆記錄

🎯 套用層級分類過濾
  - 來自熱門分類 UI: True/False
    ⚡⚡/⚡/🔍 執行 [超快速/快速/完整] 路徑
    ✅ [超快速/快速/完整]路徑結果: X 筆
```

---

## 控制日誌詳細程度

### 設定日誌級別

在後端啟動時設定 `LOG_LEVEL` 環境變數：

```bash
# 詳細日誌（DEBUG）
LOG_LEVEL=DEBUG python3 -m uvicorn app:app --reload

# 標準日誌（INFO）- 預設
LOG_LEVEL=INFO python3 -m uvicorn app:app --reload

# 最少日誌（WARNING）
LOG_LEVEL=WARNING python3 -m uvicorn app:app --reload
```

---

## 關鍵日誌記錄點

以下是程式中加入的所有日誌記錄點：

| 位置 | 檔案 | 功能 | 日誌級別 |
|------|------|------|--------|
| 程式啟動 | app.py:430-450 | 初始化模型配置 | INFO |
| API 端點 | app.py:591-605 | 記錄搜尋請求 | INFO |
| LLM 調用 | app.py:625-650 | LLM 配置和調用 | INFO |
| 層級過濾 | app.py:651-690 | 過濾過程和結果 | INFO |
| _filter_by_hierarchy() | app.py:535-605 | 三層過濾策略 | INFO |
| llm_analyze_query() | llm_service.py:940-1000 | 意圖分析 | INFO |
| llm_expand_query() | llm_service.py:1010-1030 | 查詢擴展 | INFO |
| search_products() | goods_search_service.py:478-512 | 基礎搜尋 | INFO |

---

## 效能監控

根據日誌，你可以計算每個步驟的執行時間：

```
時間戳: 2025-11-07 10:30:45,123
日誌: 🔍 /api/search 端點被觸發

時間戳: 2025-11-07 10:30:45,128  <- 3ms 後
日誌: ✅ 搜尋到 150 筆記錄

時間戳: 2025-11-07 10:30:45,132  <- 4ms 後
日誌: ✅ 超快速路徑結果: 23 筆

總耗時: ~9ms (包括網路延遲)
```

---

## 常見場景和日誌特徵

### 場景 1: 用戶在前端點擊「米麞 > 米類」

預期日誌：
```
🔍 /api/search 端點被觸發
  來自熱門分類 UI: True
    ⚡⚡ 執行超快速路徑（熱門分類 UI L3 直接過濾）
    ✅ 超快速路徑結果: 23 筆
```

### 場景 2: 用戶搜尋「有機米」

預期日誌：
```
📋 llm_analyze_query() 被呼叫
  ✅ 意圖分析結果: {category_hierarchy: {L3: "米類"}, ...}
📝 llm_expand_query() 被呼叫
  ✅ 擴展結果: "有機米, 有機糙米, ..."
📦 調用 search_products() 進行基礎搜尋
🎯 套用層級分類過濾
  🔍 執行完整路徑（逐層驗證）
```

### 場景 3: 用戶直接搜尋「米類」（分類詞）

預期日誌：
```
🔍 /api/search 端點被觸發
  分類階層: {L1: "", L2: "", L3: "米類"}
📦 調用 search_products() 進行基礎搜尋
🎯 套用層級分類過濾
  ⚡ 執行快速路徑（L3 Only 直接過濾）
```

---

## 故障排查

### 問題 1: 看不到日誌

**原因**：
- 日誌級別設定太高（WARNING/ERROR）
- 沒有看對終端機

**解決**：
```bash
LOG_LEVEL=INFO python3 -m uvicorn app:app --reload
```

### 問題 2: 看不到特定函式的日誌

**原因**：
- 該函式可能沒有被呼叫（邏輯跳過了）
- API key 不存在或無效

**檢查**：
- 在程式啟動時觀看模型配置日誌
- 確認是否有 `❌ LLM 調用失敗` 或 `- 略過` 訊息

### 問題 3: 性能比預期慢

**檢查**：
- 觀看哪個路徑被執行（超快速/快速/完整）
- 查看是否有 LLM 調用（會增加 500ms-2s 延遲）
- 計算從 `🔍 /api/search 被觸發` 到 `✅ 結果` 的時間

---

## 進階：自訂日誌

如果你想加入更多日誌點，編輯相應檔案並加入：

```python
logger.info("你的日誌訊息")
logger.warning("警告訊息")
logger.error("錯誤訊息")
```

常用前置圖標：
- `🚀` 程式啟動
- `🔍` 搜尋相關
- `📊` 配置/統計
- `📝` LLM 相關
- `📦` 函式呼叫
- `🎯` 過濾相關
- `⚡⚡/⚡/🔍` 執行路徑
- `✅` 成功
- `❌` 失敗

---

## 總結

現在你可以：

✅ 清晰看到每個查詢經過的執行路徑
✅ 了解三層過濾策略何時被觸發
✅ 監控 LLM 函式的調用
✅ 測量每個步驟的效能
✅ 快速診斷問題

使用提供的 `test_execution_paths.py` 測試腳本，你會看到：

1. **超快速路徑** ⚡⚡ - 5-10ms
2. **快速路徑** ⚡ - 10-20ms  
3. **完整路徑** 🔍 - 30-50ms（可能更多，取決於 LLM）

祝你追蹤愉快！ 🎯
