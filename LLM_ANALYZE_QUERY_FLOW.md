# llm_analyze_query 執行流程

## 🎯 關鍵發現：llm_analyze_query 不經過步驟 5、6

### 📊 完整執行順序

```
Step 1: ✅ llm_analyze_query()        ← 立即執行
        ├─ 分析用戶查詢
        ├─ 識別 category_hierarchy
        └─ 返回 intent 結構

Step 2: ✅ llm_expand_query()         ← 並行執行
        ├─ 擴展查詢詞
        └─ 返回 expanded query

Step 3: ⏭️  search_products()         ← 使用 Step 1、2 的結果
        ├─ 使用 expanded query
        ├─ 使用 intent 中的 required_terms 等
        └─ 返回候選商品

Step 4: ⏭️  _filter_by_hierarchy()    ← 使用 Step 1 的 category_hierarchy
        ├─ 過濾商品
        └─ 返回符合層級的商品

Step 5: ⏭️  llm_rerank_products()     ← 只有啟用時執行
        ├─ (可選) 重排商品
        └─ 若 SEARCH_USE_RERANK = True

Step 6: ⏭️  special_first_sort        ← 始終執行
        ├─ 將特價商品排到前面
        └─ (不是 LLM)
```

---

## 🔴 重要：llm_analyze_query 在程式流程中的位置

### 後端代碼結構 (backend/app.py Line 560-610)

```python
@app.post("/api/search")
def api_search(req: SearchReq):
    df = get_df()
    
    # ═══════════════════════════════════════════════════════
    # STEP 1 & 2: 立即執行 LLM 分析與擴展
    # ═══════════════════════════════════════════════════════
    
    try:
        # 🔵 STEP 1: llm_analyze_query 立即執行
        intent = llm_analyze_query(
            req.query,  # "食品 米麵 米類"
            system_prompt=custom_prompt,
            use_search_config=True
        )
        # 返回：
        # {
        #   "category_hierarchy": {"L1": "食品", "L2": "米麵", "L3": "米類"},
        #   "required_terms": ["米"],
        #   "excluded_terms": []
        # }
        
        # 🔵 STEP 2: llm_expand_query 立即執行
        expanded = llm_expand_query(
            req.query,
            system_prompt=custom_prompt,
            use_search_config=True
        )
        # 返回：
        # "米 白米 長粒米 短粒米 米粒 米飯"
        
    except Exception:
        intent = {}
        expanded = req.query
    
    # ═══════════════════════════════════════════════════════
    # STEP 3: 基礎搜尋（使用 Step 1、2 的結果）
    # ═══════════════════════════════════════════════════════
    
    required_terms = intent.get("required_terms")  # 來自 Step 1
    category_terms = intent.get("category_terms")  # 來自 Step 1
    excluded_terms = intent.get("excluded_terms")  # 來自 Step 1
    
    all_records, _terms = search_products(
        df,
        expanded,  # ← 使用 Step 2 的擴展查詢
        topn=candidate_topn,
        sort_price=True,
        required_terms=required_terms,        # ← 來自 Step 1
        category_terms=category_terms,        # ← 來自 Step 1
        excluded_terms=excluded_terms,        # ← 來自 Step 1
    )
    
    # ═══════════════════════════════════════════════════════
    # STEP 4: 分層過濾（使用 Step 1 的 category_hierarchy）
    # ═══════════════════════════════════════════════════════
    
    category_hierarchy = (
        req.category_hierarchy or  # 優先使用前端傳來的
        intent.get("category_hierarchy")  # 否則使用 Step 1 的分析結果
    )
    
    all_records = _filter_by_hierarchy(all_records, category_hierarchy)
    
    # ═══════════════════════════════════════════════════════
    # STEP 5: LLM 重排（可選）
    # ═══════════════════════════════════════════════════════
    
    if SEARCH_USE_RERANK:
        reranked = llm_rerank_products(
            req.query,
            expanded,
            all_records,
            topn=end_idx,
            system_prompt=custom_prompt,
            use_search_config=True
        )
        records = reranked[start_idx:end_idx]
    else:
        records = all_records[start_idx:end_idx]
    
    # ═══════════════════════════════════════════════════════
    # STEP 6: 特價優先排序
    # ═══════════════════════════════════════════════════════
    
    if prefer_special_first:
        # 排序邏輯（不涉及 LLM）
        records = sorted(
            list(enumerate(records)),
            key=lambda t: (0 if _has_special(t[1]) else 1, t[0])
        )
        records = [rec for _, rec in records]
    
    # ═══════════════════════════════════════════════════════
    # 返回結果
    # ═══════════════════════════════════════════════════════
    
    return JSONResponse({
        "message": f"為您找到 {len(items)} 項商品：",
        "items": items,
        "intent": intent or {}  # ← 返回 Step 1 的分析結果
    })
```

---

## 📍 llm_analyze_query 的具體作用範圍

```
llm_analyze_query 輸入輸出：
┌─────────────────────────────────────────────────┐
│ 輸入：req.query = "食品 米麵 米類"              │
└─────────────────────────────────────────────────┘
                      ↓
            🔵 GPT 分析（1 次 API 呼叫）
                      ↓
┌─────────────────────────────────────────────────┐
│ 輸出：intent 結構                               │
│ {                                               │
│   "category_hierarchy": {                       │
│     "L1": "食品",      ← 用在 Step 4 過濾        │
│     "L2": "米麵",      ← 用在 Step 4 過濾        │
│     "L3": "米類"       ← 用在 Step 4 過濾 ⭐️    │
│   },                                            │
│   "required_terms": ["米"],  ← 用在 Step 3 搜尋 │
│   "excluded_terms": []       ← 用在 Step 3 搜尋 │
│ }                                               │
└─────────────────────────────────────────────────┘
```

---

## 🚀 米類搜尋的實際執行流

### 用戶點擊「米類」

```
前端發送：
{
  query: "食品 米麵 米類",
  category_hierarchy: { L1: "食品", L2: "米麞", L3: "米類" }
  prefer_special_first: true
}
  ↓
  
後端 /api/search 開始處理
  ↓
  
┌─ STEP 1: llm_analyze_query("食品 米麞 米類")
│  └─ 執行時間：500-1000ms (GPT 呼叫)
│  └─ 返回：intent = {...category_hierarchy...}
│
├─ STEP 2: llm_expand_query("食品 米麞 米類")
│  └─ 執行時間：500-1000ms (GPT 呼叫)
│  └─ 返回：expanded = "米 白米 長粒米..."
│
├─ STEP 3: search_products(df, expanded)
│  └─ 執行時間：50-100ms (本地搜尋)
│  └─ 返回：[商品1, 商品2, ..., 商品60]
│
├─ STEP 4: _filter_by_hierarchy(records, {L1, L2, L3})
│  └─ 執行時間：10-50ms (本地過濾)
│  └─ 條件：
│     ✓ CateName_L1 包含 "食品"
│     ✓ CateName_L2 包含 "米麞"
│     ✓ CateName_L3 包含 "米類"
│  └─ 返回：[米商品1, 米商品2, ..., 米商品15]
│
├─ STEP 5: llm_rerank_products() [可選，預設關閉]
│  └─ 執行時間：0ms (跳過)
│
├─ STEP 6: special_first_sort()
│  └─ 執行時間：10-50ms (本地排序)
│  └─ 將有特價的米商品排到前面
│
└─ 返回 JSON 給前端
   [米商品1(特價), 米商品2(特價), 米商品3, ...]

總耗時：1-2 秒（主要是 LLM 呼叫時間）
```

---

## ⚡ 性能分析

| Step | 函數 | 執行時間 | LLM呼叫 | 備註 |
|------|------|---------|--------|------|
| 1 | `llm_analyze_query()` | 500-1000ms | ✅ 1次 | 返回 category_hierarchy |
| 2 | `llm_expand_query()` | 500-1000ms | ✅ 1次 | 返回擴展查詢 |
| 3 | `search_products()` | 50-100ms | ❌ | 使用 Step 1、2 結果 |
| 4 | `_filter_by_hierarchy()` | 10-50ms | ❌ | 使用 Step 1 的 category_hierarchy |
| 5 | `llm_rerank_products()` | 0ms (關閉) | ❌ | 預設關閉，提高速度 |
| 6 | `special_first_sort()` | 10-50ms | ❌ | 簡單排序 |

**總耗時：1-2.5 秒**
- LLM 呼叫：~1-2 秒 (Step 1+2)
- 本地處理：~100-200ms (Step 3-6)

---

## 🎯 答案：llm_analyze_query 要經過 5、6 嗎？

### ❌ **不需要！**

llm_analyze_query 的結果**不會直接經過**步驟 5、6：

```
llm_analyze_query 的輸出 (intent)
    ↓
    ├─ 輸入給 Step 3 (search_products) ✅
    ├─ 輸入給 Step 4 (_filter_by_hierarchy) ✅
    ├─ Step 5 (llm_rerank_products) 使用的是「商品列表」，而非 intent ❌
    └─ Step 6 (special_first_sort) 完全不涉及 LLM ❌
```

### 更準確地說：

```
llm_analyze_query() 
    ↓ 輸出
    intent
    ├─ "category_hierarchy" → 用在 Step 4
    ├─ "required_terms" → 用在 Step 3
    └─ "excluded_terms" → 用在 Step 3

llm_expand_query()
    ↓ 輸出
    expanded query
    └─ 用在 Step 3

search_products()
    ↓ 輸出
    候選商品列表 (60 個)
    ├─ 用在 Step 4
    ├─ 用在 Step 5 (如啟用)
    └─ 用在 Step 6

_filter_by_hierarchy()
    ↓ 輸出
    過濾後的商品列表 (10-20 個)
    ├─ 用在 Step 5 (如啟用)
    └─ 用在 Step 6

llm_rerank_products() [可選]
    ↓ 輸出
    重排後的商品列表

special_first_sort
    ↓ 輸出
    最終商品列表 (30 個) → 返回前端
```

---

## 📋 完整的資料流向圖

```
                    ┌─────────────────────┐
                    │ 用戶查詢             │
                    │ "食品 米麞 米類"     │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │ Step 1              │
                    │ llm_analyze_query() │◄───── 💬 GPT 分析
                    └──────────┬──────────┘
                               │
                   ┌───────────┴───────────┐
                   │ intent:              │
                   │ category_hierarchy   │
                   │ required_terms       │
                   │ excluded_terms       │
                   └───────┬──────────┬───┘
                           │          │
                    ┌──────▼──┐   ┌───▼──────────┐
                    │ Step 2  │   │ Step 3       │
                    │ llm_exp │   │ search_prod  │
                    │ expand  │   │              │
                    └──────┬──┘   └───┬──────┬───┘
                           │          │      │
                        ExpandQ   Required  Excluded
                           │        Terms    Terms
                           └────┬────┬────┬─┘
                                │    │    │
                    ┌───────────▼────▼────▼────┐
                    │ 候選商品列表 (60 個)     │
                    └───────────┬──────────────┘
                                │
                    ┌───────────▼──────────────┐
                    │ Step 4                   │
                    │ _filter_by_hierarchy()   │ ← 使用 intent.category_hierarchy
                    └───────────┬──────────────┘
                                │
                    ┌───────────▼──────────────┐
                    │ 過濾商品列表 (15 個)    │
                    └───────────┬──────────────┘
                                │
                       ┌────────▼────────┐
                       │ if RERANK:      │
                       │ Step 5 LLM重排  │◄── 💬 (可選)
                       └────────┬────────┘
                                │
                    ┌───────────▼──────────────┐
                    │ Step 6                   │
                    │ special_first_sort()     │
                    │ 特價優先排序             │
                    └───────────┬──────────────┘
                                │
                    ┌───────────▼──────────────┐
                    │ 最終商品列表 (30 個)    │
                    │ 返回前端                │
                    └──────────────────────────┘
```

---

## 🎬 時序圖

```
時間軸                  後端處理

T0ms    ├─ 收到前端查詢
        │  query = "食品 米麞 米類"
        │
T1ms    ├─ 調用 llm_analyze_query()
        │  ├─ 發送給 GPT ───────────┐
        │  │                        │
        │  ⏳ 等待 GPT 回應..       │ LLM 處理：500-1000ms
        │  │                        │
T500ms  │  └─ 收到 intent ◀─────────┤
        │    {category_hierarchy,...}
        │
T501ms  ├─ 調用 llm_expand_query()
        │  ├─ 發送給 GPT ───────────┐
        │  │                        │
        │  ⏳ 等待 GPT 回應..       │ LLM 處理：500-1000ms
        │  │                        │
T1000ms │  └─ 收到 expanded ◄──────┤
        │    "米 白米 長粒米..."
        │
T1010ms ├─ Step 3: search_products()
        │  └─ 返回 60 個候選 (50ms)
        │
T1060ms ├─ Step 4: _filter_by_hierarchy()
        │  └─ 返回 15 個米商品 (30ms)
        │
T1090ms ├─ Step 5: [跳過 RERANK]
        │
T1110ms ├─ Step 6: special_first_sort()
        │  └─ 返回 15 個排序商品 (20ms)
        │
T1130ms └─ 返回 JSON 給前端 ✅

【總耗時：~1.13 秒】
  LLM 呼叫：~1 秒
  本地處理：~130ms
```

---

## 💡 重點總結

| 問題 | 答案 |
|------|------|
| llm_analyze_query 執行一次嗎？ | ✅ 是，Step 1 立即執行 |
| 它經過 Step 5 (LLM重排) 嗎？ | ❌ 不，Step 5 使用的是「商品列表」 |
| 它經過 Step 6 (特價排序) 嗎？ | ❌ 不，Step 6 完全不涉及 LLM |
| 它的結果哪裡用到？ | ✅ Step 3、Step 4、以及返回給前端的 intent |
| llm_analyze_query 會阻擋其他 Step 嗎？ | ✅ 會，因為 Step 3 需要它的結果 |

