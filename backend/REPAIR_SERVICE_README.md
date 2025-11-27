# 🔧 住宅維修服務 - 後端開發文件

> **建立日期**: 2025年11月11日  
> **版本**: 1.0.0  
> **狀態**: ✅ 後端實作完成（前端未實作）

---

## 📋 目錄

- [功能概述](#功能概述)
- [架構設計](#架構設計)
- [API 端點](#api-端點)
- [環境變數配置](#環境變數配置)
- [資料結構](#資料結構)
- [使用範例](#使用範例)
- [測試指南](#測試指南)
- [部署說明](#部署說明)
- [安全保護機制](#安全保護機制)

---

## 🎯 功能概述

住宅維修服務是 SEARCH_Goods 系統的**獨立模組**，專門處理集合式住宅的維修報修場景。

### 核心特性

✅ **完全獨立** - 不影響現有商品搜尋功能  
✅ **環境變數控制** - 預設關閉，需手動啟用  
✅ **CSV 資料驅動** - 40 筆維修項目，8 個欄位  
✅ **LLM 整合** - 智能查詢擴展和對話生成  
✅ **降級保護** - LLM 失敗時自動使用範本回覆  
✅ **完整測試** - 單元測試 + API 測試

### 適用場景

- 🏠 住戶報修諮詢
- 🔍 維修項目搜尋
- 💬 維修對話互動
- 📚 維修知識查詢

---

## 🏗️ 架構設計

### 模組組成

```
backend/
├── repair_search_service.py    # 維修搜尋引擎（核心）
├── repair_llm_service.py        # LLM 整合服務
├── repair_constants.py          # 常數定義
├── app.py                       # API 端點（新增 3 個端點）
└── tests/
    ├── test_repair_search.py    # 搜尋服務測試
    └── test_repair_api.py       # API 端點測試
```

### 設計原則

#### 1️⃣ **獨立性原則**
- 維修服務與商品搜尋完全分離
- 使用獨立的 CSV 資料檔案
- 獨立的 API 路由（`/api/repair/*`）
- 獨立的測試檔案

#### 2️⃣ **安全性原則**
- 環境變數控制啟用狀態
- 預設關閉（`ENABLE_REPAIR_SERVICE=False`）
- 服務關閉時端點返回 404

#### 3️⃣ **降級保護原則**
- LLM 失敗 → 使用範本回覆
- 資料載入失敗 → 返回友善錯誤訊息
- 搜尋無結果 → 提供替代建議

---

## 📡 API 端點

### 1. 維修聊天端點

**`POST /api/repair/chat`**

智能維修對話介面，結合搜尋和 LLM 生成自然回覆。

#### 請求格式

```json
{
  "message": "水龍頭一直滴水怎麼辦",
  "history": [
    {"role": "user", "content": "之前的問題"},
    {"role": "assistant", "content": "之前的回覆"}
  ],
  "session_id": "optional-session-id",
  "topn": 5
}
```

#### 回應格式

```json
{
  "reply": "理解您的水龍頭滴水問題... [AI 生成的專業回覆]",
  "repairs": [
    {
      "序號": 1,
      "責任類型": "住家",
      "維修類別": "給/排水設備",
      "維修項目": "水龍頭持續滴水",
      "常見症狀": "水龍頭或三角凡爾持續滴水。",
      "檢查方法": "觀察滴水點...",
      "處理建議": "關閉進水開關，更換墊圈...",
      "頁面連結": "https://...",
      "影片說明": "https://youtu.be/..."
    }
  ],
  "session_id": "abc123",
  "meta": {
    "query": "水龍頭一直滴水怎麼辦",
    "expanded_query": "水龍頭 滴水 漏水 墊圈 三角凡爾",
    "terms": ["水龍頭", "滴水"],
    "result_count": 1
  }
}
```

---

### 2. 維修搜尋端點

**`POST /api/repair/search`**

純搜尋介面，不生成對話回覆。

#### 請求格式

```json
{
  "query": "漏水",
  "topn": 5,
  "category": "給/排水"
}
```

#### 回應格式

```json
{
  "results": [
    {
      "序號": 1,
      "維修項目": "水龍頭持續滴水",
      "維修類別": "給/排水設備",
      "常見症狀": "水龍頭或三角凡爾持續滴水。",
      "頁面連結": "https://...",
      "影片說明": "https://youtu.be/..."
    }
  ],
  "meta": {
    "query": "漏水",
    "terms": ["漏水"],
    "count": 1
  }
}
```

---

### 3. 維修類別端點

**`GET /api/repair/categories`**

取得所有可用的維修類別。

#### 回應格式

```json
{
  "categories": [
    "給/排水設備",
    "電力系統",
    "門窗設備",
    "空調設備",
    "結構問題"
  ]
}
```

---

## ⚙️ 環境變數配置

### 必要設定

```bash
# .env 檔案

# 啟用維修服務（預設 False）
ENABLE_REPAIR_SERVICE=True

# OpenAI API Key（LLM 功能需要）
OPENAI_API_KEY=sk-xxx...
```

### 選用設定

```bash
# 維修資料 CSV 路徑（預設 data/集合式住宅報修資料.csv）
REPAIR_DATA_PATH=../data/集合式住宅報修資料.csv

# 是否使用 LLM（預設 True，可降級到範本回覆）
REPAIR_USE_LLM=True

# 使用的 OpenAI 模型（預設 gpt-4o-mini）
REPAIR_OPENAI_MODEL=gpt-4o-mini
```

---

## 📊 資料結構

### CSV 欄位定義

維修資料檔案：`data/集合式住宅報修資料.csv`

| 欄位名稱 | 類型 | 說明 | 範例 |
|---------|------|------|------|
| 責任類型 | 字串 | 住家/公設 | 住家 |
| 維修項目類別 | 字串 | 維修分類 | 給/排水設備 |
| 維修項目名稱 | 字串 | 項目名稱 | 水龍頭持續滴水 |
| 常見維修反應細項 | 字串 | 症狀描述 | 水龍頭或三角凡爾持續滴水。 |
| 專業檢查方法 | 字串 | 檢查步驟 | 觀察滴水點（出水口或軸心）... |
| 處理建議 (SOP) 補充 | 字串 | 處理方法 | 關閉進水開關，更換墊圈... |
| 頁面連結 | 字串 | 詳細資料 URL | https://www.sky-family.net/... |
| Youtube 影片說明 | 字串 | 影片 URL | https://youtu.be/yddFy483ta8 |

### 資料統計

- **總筆數**: 40 筆
- **責任類型**: 住家 (多數)、公設
- **主要類別**: 給/排水設備、電力系統、門窗設備等

---

## 💡 使用範例

### Python 代碼範例

#### 1. 使用搜尋服務

```python
from repair_search_service import load_repair_data, search_repairs, format_for_chat

# 載入資料
df = load_repair_data()

# 搜尋維修項目
results, terms = search_repairs(
    df=df,
    query="水龍頭滴水",
    topn=3,
    min_score=1.0
)

# 格式化結果
formatted = format_for_chat(results, slim_mode=False)

print(f"找到 {len(formatted)} 個維修項目")
for item in formatted:
    print(f"- {item['維修項目']}")
```

#### 2. 使用 LLM 服務

```python
from repair_llm_service import repair_expand_query, repair_chat_reply

# 擴展查詢
expanded = repair_expand_query("水龍頭漏水")
print(f"擴展查詢: {expanded}")

# 生成對話回覆
reply = repair_chat_reply(
    query="水龍頭一直滴水",
    history=[],
    results=formatted
)
print(f"回覆: {reply}")
```

### cURL 範例

#### 維修聊天

```bash
curl -X POST http://localhost:8000/api/repair/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "水龍頭滴水",
    "history": [],
    "topn": 3
  }'
```

#### 維修搜尋

```bash
curl -X POST http://localhost:8000/api/repair/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "漏水",
    "topn": 5,
    "category": "給/排水"
  }'
```

#### 取得類別

```bash
curl http://localhost:8000/api/repair/categories
```

---

## 🧪 測試指南

### 執行測試

```bash
cd backend

# 執行所有維修服務測試
pytest tests/test_repair_search.py tests/test_repair_api.py -v

# 只執行搜尋服務測試
pytest tests/test_repair_search.py -v

# 只執行 API 測試
pytest tests/test_repair_api.py -v

# 執行特定測試類
pytest tests/test_repair_search.py::TestSearchRepairs -v
```

### 測試覆蓋範圍

#### 搜尋服務測試 (`test_repair_search.py`)

- ✅ 資料載入
- ✅ 詞彙提取
- ✅ 評分計算
- ✅ 搜尋功能
- ✅ 結果格式化
- ✅ 工具函數

#### API 測試 (`test_repair_api.py`)

- ✅ 服務可用性
- ✅ 聊天端點
- ✅ 搜尋端點
- ✅ 類別端點
- ✅ 錯誤處理
- ✅ 整合測試

### 測試資料

測試使用實際的 CSV 資料檔案：
```
data/集合式住宅報修資料.csv
```

---

## 🚀 部署說明

### 本地開發

```bash
# 1. 設定環境變數
cd backend
cp .env.example .env

# 2. 編輯 .env 啟用維修服務
echo "ENABLE_REPAIR_SERVICE=True" >> .env
echo "OPENAI_API_KEY=your-key" >> .env

# 3. 安裝依賴（已包含在 requirements.txt）
pip install -r requirements.txt

# 4. 啟動服務
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 5. 測試端點
curl http://localhost:8000/api/repair/categories
```

### Docker 部署

```dockerfile
# Dockerfile 無需修改，通過環境變數控制

# docker-compose.yml 新增環境變數
services:
  backend:
    environment:
      - ENABLE_REPAIR_SERVICE=true
      - REPAIR_DATA_PATH=/app/data/集合式住宅報修資料.csv
```

### Render 部署

在 Render Dashboard 設定環境變數：

```
ENABLE_REPAIR_SERVICE=true
REPAIR_DATA_PATH=/opt/render/project/src/data/集合式住宅報修資料.csv
OPENAI_API_KEY=sk-xxx...
```

---

## 🛡️ 安全保護機制

### 1. Feature Toggle 保護

```python
# 服務預設關閉
ENABLE_REPAIR_SERVICE = os.getenv("ENABLE_REPAIR_SERVICE", "False")

# 端點檢查
if ENABLE_REPAIR_SERVICE:
    @app.post("/api/repair/chat")
    def repair_chat_endpoint(...):
        # 端點實作
```

### 2. 降級保護

```python
# LLM 失敗時降級到範本回覆
try:
    reply = repair_chat_reply(query, history, results)
except Exception:
    reply = _generate_template_reply(query, results)
```

### 3. 資料驗證

```python
# 檢查資料可用性
repair_df = load_repair_data()
if repair_df.empty:
    return RepairChatResp(
        reply="抱歉，維修資料庫暫時無法使用",
        repairs=[],
        meta={"error": "data_unavailable"}
    )
```

### 4. 錯誤處理

```python
# 全域錯誤捕獲
try:
    # 處理請求
except Exception as e:
    logger.error(f"[Repair] Error: {e}", exc_info=True)
    return RepairChatResp(
        reply="抱歉，維修服務暫時無法回應",
        repairs=[],
        meta={"error": str(e)}
    )
```

---

## 📝 開發檢查清單

### 實作完成 ✅

- [x] 建立 `repair_search_service.py`
- [x] 建立 `repair_llm_service.py`
- [x] 新增 API 端點（3 個）
- [x] 建立測試檔案（2 個）
- [x] 更新 `.env.example`
- [x] 建立說明文件

### 待完成 📋

- [ ] 前端意圖識別（docs/對話區模型路由設計方案.md）
- [ ] 前端維修回覆渲染
- [ ] 前端 UI 視覺區分
- [ ] 整合測試
- [ ] 效能優化

---

## 🔗 相關文件

- [住宅維修客服系統設計規劃](../docs/住宅維修客服系統設計規劃.md)
- [維修項目中英文對照表](../docs/維修項目中英文對照表.md)
- [LLM 提示詞模板](../docs/LLM_提示詞模板.md)
- [對話區模型路由設計方案](../docs/對話區模型路由設計方案.md)

---

## 📞 技術支援

如有問題請參考：

1. **測試執行**: 執行測試檢查功能正常性
2. **日誌檢查**: 查看 `[Repair]` 前綴的日誌
3. **環境變數**: 確認 `ENABLE_REPAIR_SERVICE=True`
4. **API 測試**: 使用 cURL 或 Postman 測試端點

---

**版本歷史**

| 版本 | 日期 | 說明 |
|------|------|------|
| 1.0.0 | 2025-11-11 | 後端維修服務完整實作完成 |

