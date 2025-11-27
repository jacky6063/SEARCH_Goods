# llm_analyze_query 的真正功能

## ❌ 錯誤認知
```
❌ llm_analyze_query 的功能 = 做商品過濾
```

## ✅ 正確認知
```
✅ llm_analyze_query 的功能 = 「分析查詢意圖」，不是過濾商品！
```

---

## 📊 llm_analyze_query 做什麼

### 📝 定義 (backend/llm_service.py Line 934)

```python
def llm_analyze_query(query: str, system_prompt: Optional[str] = None, use_search_config: bool = True) -> Dict[str, Any]:
    """分析查詢意圖，可指定使用搜索或聊天配置。
    
    新增功能：自動識別分類層級 (L1/L2/L3)
    """
```

### 🔍 功能明細

llm_analyze_query 的工作是**理解使用者的需求**，輸出**結構化的意圖分析**：

```
輸入：使用者查詢
"我要買無調味的核桃堅果，不要太鹹"

    ↓
    🤖 GPT 分析：
    - 這個查詢包含哪些必要條件？
    - 應該排除哪些詞？
    - 涉及哪個商品分類？

    ↓
輸出：結構化意圖對象
{
  "required_terms": ["無調味", "核桃"],
  "excluded_terms": ["鹹", "太鹹"],
  "category_terms": ["堅果", "零食"],
  "category_hierarchy": {
    "L1": "食品",
    "L2": "堅果",
    "L3": ""
  },
  "hierarchy_confidence": {
    "L1": 0.95,
    "L2": 0.8,
    "L3": 0.0
  },
  "notes": "使用者偏好低鹽堅果"
}
```

---

## 🎯 llm_analyze_query vs _filter_by_hierarchy

### 很容易搞混！讓我比較一下：

| 方面 | llm_analyze_query | _filter_by_hierarchy |
|------|-------------------|---------------------|
| **功能** | 📋 分析意圖，提取需求 | 🔍 過濾商品 |
| **輸入** | 🔤 文字查詢 | 📦 商品列表 + 分類層級 |
| **輸出** | 📊 結構化意圖物件 | 📦 過濾後的商品列表 |
| **是否涉及商品資料** | ❌ 不涉及 | ✅ 涉及 |
| **是否修改商品資料** | ❌ 不修改 | ✅ 移除不符合的 |
| **何時執行** | ⏰ Step 1 (最早) | ⏰ Step 4 (中間) |
| **LLM 呼叫** | ✅ 呼叫 GPT | ❌ 不呼叫 |
| **執行速度** | 🐢 500-1000ms | ⚡ 10-50ms |

---

## 📌 llm_analyze_query 的 5 個輸出欄位

### 1️⃣ required_terms (必要詞)
```
用戶說："無調味的核桃"
↓
required_terms: ["無調味", "核桃"]
↓
後續用途：search_products() 會只搜尋包含「無調味」且包含「核桃」的商品
```

### 2️⃣ excluded_terms (排除詞)
```
用戶說："堅果，但不要太鹹的"
↓
excluded_terms: ["鹹", "太鹹"]
↓
後續用途：search_products() 會排除包含「鹹」的商品
```

### 3️⃣ category_terms (分類詞)
```
用戶說："我要買堅果零食"
↓
category_terms: ["堅果", "零食"]
↓
後續用途：搜尋時優先考慮「堅果」和「零食」相關商品
```

### 4️⃣ category_hierarchy (分類層級)
```
用戶說："食品類的米麞下的米類商品"
↓
category_hierarchy: {
  "L1": "食品",
  "L2": "米麞",
  "L3": "米類"
}
↓
後續用途：_filter_by_hierarchy() 會過濾到只符合這個層級的商品
```

### 5️⃣ hierarchy_confidence (信心度)
```
用戶說："食品類的米"
↓
hierarchy_confidence: {
  "L1": 0.95,  ← 非常確定是「食品」大分類
  "L2": 0.8,   ← 相對確定是「米麞」中分類
  "L3": 0.0    ← 不確定 L3 小分類
}
↓
後續用途：系統可根據信心度決定是否使用這個層級進行過濾
```

---

## 🔄 llm_analyze_query 的結果如何被使用

### 流程圖

```
llm_analyze_query()
    ↓
    輸出 intent
    
    {
      required_terms: ["米"],
      excluded_terms: [],
      category_terms: ["米"],
      category_hierarchy: {L1: "食品", L2: "米麞", L3: "米類"},
      hierarchy_confidence: {L1: 0.95, L2: 0.9, L3: 0.85}
    }
    
    ├─ required_terms → Step 3: search_products()
    │  └─ 呼叫時傳入 required_terms 參數
    │  └─ 搜尋結果只會包含「米」
    │
    ├─ excluded_terms → Step 3: search_products()
    │  └─ 呼叫時傳入 excluded_terms 參數
    │  └─ 搜尋結果會排除指定的詞
    │
    ├─ category_terms → Step 3: search_products()
    │  └─ 用於優先搜尋分類相關商品
    │
    ├─ category_hierarchy → Step 4: _filter_by_hierarchy()
    │  └─ 過濾商品，只保留符合層級的
    │  └─ 檢查：CateName_L3 == "米類" ✓
    │
    ├─ hierarchy_confidence → (可選)
    │  └─ 系統可根據信心度調整過濾嚴格程度
    │
    └─ 整個 intent 物件 → 返回給前端
       └─ 前端可展示意圖分析結果給用戶
```

---

## 📋 代碼實例：米類搜尋

### 前端發送：
```json
{
  "query": "食品 米麞 米類",
  "category_hierarchy": {
    "L1": "食品",
    "L2": "米麞",
    "L3": "米類"
  },
  "prefer_special_first": true
}
```

### Step 1: llm_analyze_query 執行

```python
# backend/app.py Line 578

intent = llm_analyze_query(
    "食品 米麞 米類",
    use_search_config=True
)

# 返回的 intent 可能是：
# {
#   "required_terms": ["米"],
#   "excluded_terms": [],
#   "category_terms": ["米"],
#   "category_hierarchy": {
#     "L1": "食品",
#     "L2": "米麞",
#     "L3": "米類"
#   },
#   "hierarchy_confidence": {
#     "L1": 0.95,
#     "L2": 0.9,
#     "L3": 0.85
#   }
# }
```

### Step 3: search_products 使用 intent

```python
# backend/app.py Line 595

required_terms = intent.get("required_terms")  # ["米"]
excluded_terms = intent.get("excluded_terms")  # []

all_records, _terms = search_products(
    df,
    expanded,
    topn=60,
    required_terms=required_terms,        # ← 傳入
    excluded_terms=excluded_terms,        # ← 傳入
)

# 搜尋結果只會包含「米」相關的 60 個商品
```

### Step 4: _filter_by_hierarchy 使用 intent

```python
# backend/app.py Line 603

category_hierarchy = (
    req.category_hierarchy or  # 優先使用前端的
    intent.get("category_hierarchy")  # 否則使用 LLM 分析的
)

# category_hierarchy = {
#   "L1": "食品",
#   "L2": "米麞",
#   "L3": "米類"
# }

all_records = _filter_by_hierarchy(all_records, category_hierarchy)

# 過濾到只有「大分類=食品 且 中分類=米麞 且 小分類=米類」的商品
# 通常 15-20 個商品
```

---

## 💡 llm_analyze_query 不做的事

| 不做的事 | 原因 |
|---------|------|
| ❌ 不過濾商品 | 它不涉及商品資料庫 |
| ❌ 不修改商品資料 | 它只分析文字 |
| ❌ 不返回商品列表 | 它返回的是意圖結構 |
| ❌ 不排序商品 | 那是其他 Step 的工作 |
| ❌ 不判斷特價 | 那是 Step 6 的工作 |

---

## 🎬 完整流程中的位置

```
                用戶點擊「米類」
                     ↓
              前端構造查詢請求
         {query: "...", category_hierarchy: {...}}
                     ↓
              POST /api/search
                     ↓
    ┌──────────────────────────────────────┐
    │ 後端開始處理                           │
    │                                      │
    │ Step 1: llm_analyze_query()  ⭐️     │
    │ 功能：分析意圖                        │
    │ 目的：提取需求信息                    │
    │ 輸出：{required_terms, ..., 層級}    │
    │                                      │
    │ 並不做商品過濾！                      │
    │                                      │
    │ Step 2: llm_expand_query()           │
    │ 步驟 3: search_products()            │
    │ 步驟 4: _filter_by_hierarchy() ⭐️   │
    │ 功能：實際過濾商品                    │
    │ 目的：按層級限制商品                  │
    │                                      │
    │ 步驟 5: (可選) 重排                  │
    │ 步驟 6: 特價優先                     │
    │                                      │
    └──────────────────────────────────────┘
                     ↓
              返回過濾後的商品
                     ↓
              前端聊天區展示
```

---

## 🧠 記憶技巧

### llm_analyze_query = 「理解」
```
llm_analyze_query 就像一個「翻譯員」：
- 輸入：自然語言 ("我要買無調味核桃")
- 工作：理解用戶的真實需求
- 輸出：結構化的需求說明書 (required_terms, excluded_terms, ...)
- 目的：讓後續步驟知道該怎麼搜尋和過濾
```

### _filter_by_hierarchy = 「執行」
```
_filter_by_hierarchy 就像一個「檢查員」：
- 輸入：商品列表 + 層級過濾條件
- 工作：逐個檢查商品是否符合層級
- 輸出：符合層級的商品列表
- 目的：確保只返回正確分類的商品
```

---

## 📋 總結表

| 特性 | llm_analyze_query | _filter_by_hierarchy |
|------|-------------------|---------------------|
| **是意圖分析嗎？** | ✅ 是 | ❌ 否 |
| **是商品過濾嗎？** | ❌ 否 | ✅ 是 |
| **涉及 GPT 嗎？** | ✅ 是 | ❌ 否 |
| **涉及商品資料庫嗎？** | ❌ 否 | ✅ 是 |
| **返回意圖對象嗎？** | ✅ 是 | ❌ 否 |
| **返回商品列表嗎？** | ❌ 否 | ✅ 是 |
| **執行速度快嗎？** | ❌ 慢 (500-1000ms) | ✅ 快 (10-50ms) |

---

## 📚 相關檔案

| 內容 | 位置 |
|------|------|
| llm_analyze_query 函數定義 | backend/llm_service.py Line 934 |
| llm_analyze_query 呼叫 | backend/app.py Line 578 |
| _filter_by_hierarchy 函數定義 | backend/app.py Line 511 |
| _filter_by_hierarchy 呼叫 | backend/app.py Line 606 |

---

## ✨ 簡短答案

```
❌ 問：llm_analyze_query 功能是做商品過濾嗎？
✅ 答：不是！它是分析查詢意圖，提取需求資訊

      真正做商品過濾的是 _filter_by_hierarchy()

      llm_analyze_query 做的是：
      - 理解用戶說了什麼
      - 提取出必要條件 (required_terms)
      - 提取排除條件 (excluded_terms)
      - 識別商品分類 (category_hierarchy)
      
      然後把這些信息傳給：
      - search_products() 用來搜尋
      - _filter_by_hierarchy() 用來過濾
```

