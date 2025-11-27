# LLM 搜尋優化 - API 參考文檔

**文檔日期**: 2025-11-04  
**版本**: 1.0  
**基礎 URL**: `http://localhost:8000` (開發環境)

---

## 概述

本文檔描述 LLM 搜尋優化後新增/修改的 API 端點及其參數。

### 核心改進

- ✅ 新增分類層級識別能力
- ✅ 支持多層級搜尋
- ✅ 信心度評分返回
- ✅ 完整向後相容

---

## 端點清單

| 方法 | 端點 | 說明 | 狀態 |
|------|------|------|------|
| POST | `/api/chat` | 聊天模式（含分類分析） | ✅ 改進 |
| POST | `/api/search` | 關鍵字搜尋（含分類信息） | ✅ 改進 |
| POST | `/api/suggest` | 推薦端點 | ✅ 相容 |
| GET | `/health` | 健康檢查 | ✓ 不變 |

---

## 詳細 API 文檔

### 1. POST /api/chat

聊天模式 - 自然語言與 LLM 智能分析

#### 請求

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "我想找食品類的調味品",
    "history": [],
    "catalog": []
  }'
```

#### 請求參數

| 參數 | 類型 | 必須 | 說明 |
|------|------|------|------|
| `user_message` | string | ✓ | 用戶查詢文本 |
| `history` | array | - | 聊天歷史 (可空) |
| `catalog` | array | - | 商品目錄 (可空) |
| `topn` | number | - | 返回數量 (預設: 8) |

#### 請求示例

```json
{
  "user_message": "我想找食品類的調味品，推薦一些橄欖油",
  "history": [
    {
      "role": "user",
      "content": "你好"
    },
    {
      "role": "assistant", 
      "content": "你好！歡迎使用商品搜尋系統"
    }
  ],
  "catalog": []
}
```

#### 響應 (200 OK)

```json
{
  "reply": "為您推薦以下特級橄欖油商品...",
  "action": {
    "type": "none"
  },
  "intent": "product_search",
  "category_hierarchy": {
    "L1": "食品",
    "L2": "調味品",
    "L3": "橄欖油"
  },
  "hierarchy_confidence": {
    "L1": 0.95,
    "L2": 0.87,
    "L3": 0.72
  },
  "overview": {
    "results": [
      {
        "商品編號": "123456",
        "商品名稱": "特級初榨橄欖油 500ml",
        "商品價格": "580",
        "商品特價": "499",
        "CateName_L1": "食品",
        "CateName_L2": "調味品",
        "CateName_L3": "橄欖油",
        "matched_levels": ["L1", "L2", "L3"],
        "hierarchy_score": 0.95
      },
      {
        "商品編號": "123457",
        "商品名稱": "葡萄籽油 1L",
        "商品價格": "420",
        "CateName_L1": "食品",
        "CateName_L2": "調味品",
        "CateName_L3": "植物油",
        "matched_levels": ["L1", "L2"],
        "hierarchy_score": 0.75
      }
    ],
    "total": 12,
    "query": "食品 調味品 橄欖油"
  },
  "structured_filters": {
    "category": "調味品"
  }
}
```

#### 響應字段說明

**新增字段** (LLM 優化):

| 字段 | 類型 | 說明 |
|------|------|------|
| `category_hierarchy` | object | LLM 識別的分類層級 |
| `category_hierarchy.L1` | string | 大分類 |
| `category_hierarchy.L2` | string | 中分類 |
| `category_hierarchy.L3` | string | 小分類 |
| `hierarchy_confidence` | object | 各層級的置信度 |
| `hierarchy_confidence.L1` | number | L1 置信度 (0-1) |
| `hierarchy_confidence.L2` | number | L2 置信度 (0-1) |
| `hierarchy_confidence.L3` | number | L3 置信度 (0-1) |

**結果商品字段** (新增):

| 字段 | 類型 | 說明 |
|------|------|------|
| `matched_levels` | array | 匹配的層級 ["L1"], ["L1","L2"], ["L1","L2","L3"] |
| `hierarchy_score` | number | 層級搜尋的得分 (0-1) |
| `CateName_L1` | string | 商品的大分類 |
| `CateName_L2` | string | 商品的中分類 |
| `CateName_L3` | string | 商品的小分類 |

#### 錯誤響應

```json
{
  "detail": "LLM 服務暫時不可用，使用關鍵字搜尋",
  "reply": "為您搜尋相關商品...",
  "items": []
}
```

---

### 2. POST /api/search

搜尋模式 - 關鍵字搜尋 (含分類信息)

#### 請求

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "橄欖油",
    "topn": 10
  }'
```

#### 請求參數

| 參數 | 類型 | 必須 | 說明 |
|------|------|------|------|
| `query` | string | ✓ | 搜尋關鍵詞 |
| `topn` | number | - | 返回數量 (預設: 10) |
| `page` | number | - | 分頁 (預設: 1) |
| `sort_price` | boolean | - | 按價格排序 (預設: false) |

#### 響應 (200 OK)

```json
{
  "items": [
    {
      "商品編號": "123456",
      "商品名稱": "特級初榨橄欖油 500ml",
      "商品價格": "580",
      "商品特價": "499",
      "商品描述": "來自義大利進口，富含多酚，健康美味",
      "商品圖片網址": "https://...",
      "商品購物網址": "https://...",
      "品牌": "EVOO",
      "CateName_L1": "食品",
      "CateName_L2": "調味品",
      "CateName_L3": "橄欖油",
      "matched_levels": ["L1", "L2", "L3"],
      "hierarchy_score": 0.95
    },
    {
      "商品編號": "123457",
      "商品名稱": "葡萄籽油 1L",
      "商品價格": "420",
      "CateName_L1": "食品",
      "CateName_L2": "調味品",
      "CateName_L3": "植物油",
      "matched_levels": ["L1", "L2"],
      "hierarchy_score": 0.75
    }
  ],
  "total": 45,
  "page": 1,
  "has_next": true,
  "message": "找到 45 件相關商品"
}
```

#### 分頁示例

```bash
# 第二頁
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "橄欖油",
    "page": 2,
    "topn": 10
  }'
```

---

### 3. POST /api/suggest

推薦端點 - 獲得個性化推薦

#### 請求

```bash
curl -X POST http://localhost:8000/api/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "trigger": "按1",
    "topn": 8
  }'
```

#### 請求參數

| 參數 | 類型 | 說明 |
|------|------|------|
| `trigger` | string | 推薦觸發類型 |
| `topn` | number | 返回數量 |

#### 響應

```json
{
  "suggestion_ids": ["123456", "123457", "123458"],
  "items": [
    {
      "商品編號": "123456",
      "商品名稱": "特級初榨橄欖油",
      ...
      "CateName_L1": "食品",
      "CateName_L2": "調味品",
      "CateName_L3": "橄欖油"
    }
  ],
  "message": "為您精選 3 款推薦商品"
}
```

---

## 資料型別定義

### CategoryHierarchy

```typescript
interface CategoryHierarchy {
  L1: string;        // 大分類名稱，空字符串表示未識別
  L2: string;        // 中分類名稱
  L3: string;        // 小分類名稱
}

// 示例
{
  "L1": "食品",
  "L2": "調味品",
  "L3": "橄欖油"
}
```

### HierarchyConfidence

```typescript
interface HierarchyConfidence {
  L1: number;        // 0.0 - 1.0
  L2: number;        // 0.0 - 1.0
  L3: number;        // 0.0 - 1.0
}

// 示例
{
  "L1": 0.95,
  "L2": 0.87,
  "L3": 0.72
}
```

### ProductItem

```typescript
interface ProductItem {
  商品編號: string;
  商品名稱: string;
  商品價格?: string;
  商品特價?: string;
  商品描述?: string;
  商品圖片網址?: string;
  商品購物網址?: string;
  品牌?: string;
  
  // 新增分類字段
  CateName_L1?: string;
  CateName_L2?: string;
  CateName_L3?: string;
  
  // 新增評分字段
  matched_levels?: string[];    // ["L1", "L2", "L3"]
  hierarchy_score?: number;     // 0.0 - 1.0
}
```

---

## 使用場景

### 場景 1: 聊天模式 - 分類識別

**用戶**: "我想找食品類的調味品"

**流程**:
1. 用戶發送文本到 `/api/chat`
2. LLM 分析識別: L1="食品", L2="調味品", L3=""
3. 系統執行多層過濾搜尋
4. 返回結果含分類信息和置信度

**預期效果**: 
- 搜尋精度提升 30-40%
- 相關商品排在前面
- 用戶可看到分類麵包屑

### 場景 2: 搜尋模式 - 關鍵字搜尋

**用戶**: 在搜尋框輸入 "橄欖油"

**流程**:
1. 提交到 `/api/search`
2. 執行關鍵字匹配
3. 如有分類匹配則額外評分
4. 返回結果含分類信息

**預期效果**:
- 顯示分類麵包屑
- 信心度指標可視化
- 支持點擊分類進行二次搜尋

### 場景 3: 前端交互 - 分類點擊

**用戶**: 點擊搜尋結果中的分類按鈕 "調味品"

**流程**:
1. 前端調用 `triggerCategorySearch("食品 調味品")`
2. 重新提交到 `/api/search` 或 `/api/chat`
3. 系統進行分類搜尋
4. 返回該分類下的商品

**預期效果**:
- 動態篩選結果
- 用戶快速找到所需分類

---

## HTTP 狀態碼

| 狀態碼 | 說明 |
|--------|------|
| 200 | 請求成功 |
| 400 | 請求參數錯誤 |
| 401 | 未授權 |
| 403 | 禁止訪問 |
| 500 | 伺服器內部錯誤 |
| 503 | 服務暫時不可用 (LLM API 故障) |

### 錯誤響應範例

```json
{
  "detail": "查詢參數不能為空",
  "status": 400,
  "error_code": "INVALID_QUERY"
}
```

---

## 範例程式碼

### Python 用戶端

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# 聊天查詢
def chat_search(query):
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "user_message": query,
            "history": [],
            "catalog": []
        }
    )
    data = response.json()
    
    # 提取分類信息
    if "category_hierarchy" in data:
        hierarchy = data["category_hierarchy"]
        print(f"分類: {hierarchy['L1']} > {hierarchy['L2']} > {hierarchy['L3']}")
    
    # 顯示結果
    if "overview" in data and "results" in data["overview"]:
        for item in data["overview"]["results"]:
            print(f"商品: {item['商品名稱']}")
            print(f"信心度: {item.get('hierarchy_score', 'N/A')}")
    
    return data

# 關鍵字搜尋
def keyword_search(query, topn=10):
    response = requests.post(
        f"{BASE_URL}/api/search",
        json={
            "query": query,
            "topn": topn
        }
    )
    return response.json()

# 使用示例
result = chat_search("我想找食品類的調味品")
print(json.dumps(result, indent=2, ensure_ascii=False))
```

### JavaScript 用戶端

```javascript
// 聊天搜尋
async function chatSearch(query) {
    const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            user_message: query,
            history: [],
            catalog: []
        })
    });
    
    const data = await response.json();
    
    // 提取分類信息
    if (data.category_hierarchy) {
        const { L1, L2, L3 } = data.category_hierarchy;
        console.log(`分類: ${L1} > ${L2} > ${L3}`);
    }
    
    // 顯示結果
    if (data.overview?.results) {
        data.overview.results.forEach(item => {
            console.log(`商品: ${item.商品名稱}`);
            console.log(`信心度: ${item.hierarchy_score}`);
        });
    }
    
    return data;
}

// 使用示例
chatSearch("我想找食品類的調味品").then(result => {
    console.log(JSON.stringify(result, null, 2));
});
```

### cURL 範例

```bash
# 聊天查詢
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "我想找食品類的調味品",
    "history": [],
    "catalog": []
  }' | jq '.category_hierarchy'

# 關鍵字搜尋
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "橄欖油",
    "topn": 5
  }' | jq '.items[] | {商品名稱, matched_levels, hierarchy_score}'
```

---

## 效能指標

### 典型響應時間

| 操作 | 耗時 (毫秒) |
|------|-----------|
| `/api/search` (關鍵字) | 100-200 |
| `/api/chat` (含 LLM) | 2000-3000 |
| 分類麵包屑渲染 | 50-100 |
| 信心度計算 | 10-20 |

### 推薦實踐

1. **緩存**: 在客戶端緩存相同查詢的結果
2. **超時**: 設置 LLM 調用超時為 10 秒
3. **重試**: 失敗時自動回退到關鍵字搜尋
4. **分頁**: 大結果集使用分頁避免加載過多數據

---

## 更新日誌

### v1.0 (2025-11-04)
- ✅ 初始版本發布
- ✅ 新增分類層級識別
- ✅ 支持多層級搜尋
- ✅ 信心度評分返回
