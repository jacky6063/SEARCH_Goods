# 熱門小分類搜尋資料流分析

## 📋 概述

當用戶點擊熱門小分類（如「米類」）時，系統執行以下完整流程：

```
用戶點擊「米類」 → 前端構造查詢請求 → 後端 LLM 分析 → 分類過濾 → 排序優化 → 聊天區展示
```

---

## 🔵 前端流程 (frontend/index.html)

### 1️⃣ 觸發點：L3 分類選擇 (Line ~540-570)

```javascript
// 當用戶點擊 L3 小分類（例如「米類」）
if(level === 'L3'){
  setHotScopePath({ L3: name });           // 記錄：L3 = 米類
  appendChatBubble('user', name);          // 聊天區顯示：用戶訊息 = 「米類」
  chatHistory.push({ role: 'user', content: name });
  
  // 構造後端查詢請求
  const payload = {
    query: `${hotScopePath.L1 || ''} ${hotScopePath.L2 || ''} ${name}`.trim(),
    // 示例：如果 L1=常溫食品，L2=五穀/豆類/米麵/乾貨，L3=米類
    // 則 query = "常溫食品 五穀/豆類/米麵/乾貨 米類"
    
    page: 1,
    page_size: 30,
    
    // 🔑 關鍵：直接傳入分類層級
    category_hierarchy: { 
      L1: hotScopePath.L1,  // 常溫食品
      L2: hotScopePath.L2,  // 五穀/豆類/米麵/乾貨
      L3: name              // 米類 ⭐️
    },
    
    // 特價優先
    prefer_special_first: true
  };
  
  setMode('search');  // 切換到搜尋模式
  
  // 發送 POST /api/search 請求
  const res = await fetch(buildBackendUrl('search'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  
  const data = await res.json();
  
  // 顯示搜尋結果摘要
  announceCategorySearchResult(name, data);
}
```

### 2️⃣ 聊天區展示 (Line ~895-945)

```javascript
function announceCategorySearchResult(queryName, data){
  // queryName = "米類"
  // data = { items: [...], message: "..." }
  
  const items = data.items || [];
  const header = `根據您的需求「米類」，我為您找到 ${items.length} 款相關商品。`;
  
  // 取前 6 個商品
  const maxList = Math.min(items.length, 6);
  for(let i = 0; i < maxList; i++){
    const item = items[i];
    const name = item.商品名稱 || item.Name;
    const id = item.商品編號 || item.GoodIden;
    const price = item.商品特價 || item.Price_fmt;
    const link = item.商品購物網址 || item.Goods_Link1;
    
    lines.push(`${i+1}. 商品名稱：${name}`);
    lines.push(`   商品編號：${id}`);
    lines.push(`   商品價格：${price}`);
    lines.push(`   購物連結：${link}`);
  }
  
  if(items.length > 6){
    lines.push(`…還有 ${items.length - 6} 款商品`);
  }
  
  // 在聊天區顯示
  appendChatBubble('assistant', lines.join("\n"));
}
```

---

## 🟢 後端流程 (backend/app.py)

### 3️⃣ 搜尋端點 POST /api/search (Line ~560-650)

```python
@app.post("/api/search")
def api_search(req: SearchReq):
    # req.query = "常溫食品 五穀/豆類/米麵/乾貨 米類"
    # req.category_hierarchy = { L1: "常溫食品", L2: "五穀/豆類/米麵/乾貨", L3: "米類" }
    # req.prefer_special_first = True
    
    df = get_df()  # 載入 953 件商品的 CSV
    
    # ========== Step 1: LLM 分析與查詢擴展 ==========
    try:
        # 使用 SEARCH_USE_LLM_INTENT = True
        intent = llm_analyze_query(
            req.query,  # "常溫食品 五穀/豆類/米麵/乾貨 米類"
            use_search_config=True
        )
        # 結果例如：
        # {
        #   "category_hierarchy": { "L1": "常溫食品", "L2": "五穀/豆類/米麵/乾貨", "L3": "米類" },
        #   "required_terms": ["米"],
        #   "excluded_terms": [],
        #   "budget": None
        # }
        
        expanded = llm_expand_query(req.query, use_search_config=True)
        # 擴展結果例如："米 白米 長粒米 短粒米 米粒 米飯 米類"
    except Exception:
        intent = {}
        expanded = req.query
    
    # ========== Step 2: 基礎搜尋 ==========
    all_records, _terms = search_products(
        df,
        expanded,              # "米 白米 長粒米 短粒米..."
        topn=60,               # 先取 60 條候選
        sort_price=True,
        required_terms=intent.get("required_terms"),
        excluded_terms=intent.get("excluded_terms"),
    )
    # 返回：[商品1, 商品2, 商品3, ...]
    
    # ========== Step 3: 🆕 分類層級過濾 ⭐️ ==========
    category_hierarchy = (
        req.category_hierarchy or  # 使用前端傳來的層級 ← 優先
        (intent.get("category_hierarchy") if isinstance(intent, dict) else None)
    )
    
    # 呼叫 _filter_by_hierarchy()
    all_records = _filter_by_hierarchy(all_records, category_hierarchy)
    # 過濾邏輯：只保留「CateName_L3 = 米類」的商品
    # 返回：[米商品1, 米商品2, ...]
```

### 4️⃣ 分類過濾核心 (Line ~511-540)

```python
def _filter_by_hierarchy(
    records: List[Dict[str, Any]], 
    hierarchy: Optional[Dict[str, str]]
) -> List[Dict[str, Any]]:
    
    if not hierarchy:
        return records
    
    # 提取層級
    l1 = hierarchy.get("L1")  # "常溫食品"
    l2 = hierarchy.get("L2")  # "五穀/豆類/米麵/乾貨"
    l3 = hierarchy.get("L3")  # "米類"
    
    if not any([l1, l2, l3]):
        return records
    
    filtered = []
    
    for rec in records:
        ok = True
        
        # 檢查 L1
        if l1:
            v = rec.get("CateName_L1") or rec.get("大分類名稱")
            ok = ok and (l1 in v)  # "常溫食品" in rec的大分類
        
        # 檢查 L2
        if ok and l2:
            v = rec.get("CateName_L2") or rec.get("中分類名稱")
            ok = ok and (l2 in v)  # "五穀/豆類/米麵/乾貨" in rec的中分類
        
        # 檢查 L3
        if ok and l3:
            v = rec.get("CateName_L3") or rec.get("小分類名稱")
            ok = ok and (l3 in v)  # ⭐️ "米類" in rec的小分類
        
        if ok:
            filtered.append(_annotate_hierarchy(rec, hierarchy))
    
    return filtered or records  # 若過濾後為空，回傳原始結果
```

### 5️⃣ LLM 分類分析詳解 (backend/llm_service.py)

#### 🔍 `llm_analyze_query()` 做什麼？

```python
def llm_analyze_query(
    query: str,  # "常溫食品 五穀/豆類/米麵/乾貨 米類"
    use_search_config: bool = True
) -> Dict[str, Any]:
    """
    使用 GPT 分析查詢意圖，識別：
    - category_hierarchy: {L1, L2, L3}
    - required_terms: 必須包含
    - excluded_terms: 必須排除
    """
    
    # 構造系統提示詞（包含分類層級指南）
    category_prompt = _build_category_hierarchy_prompt()
    
    # 呼叫 GPT
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"""
你是商品搜尋系統的意圖分析助手。
{category_prompt}

分析使用者查詢，返回 JSON：
{{
  "category_hierarchy": {{"L1": "...", "L2": "...", "L3": "..."}},
  "required_terms": ["..."],
  "excluded_terms": ["..."],
  "budget": null,
  "intent": "search"
}}
                """
            },
            {"role": "user", "content": query}
        ]
    )
    
    # 解析 LLM 回應
    result = json.loads(response.content)
    
    # 對於「常溫食品 五穀/豆類/米麵/乾貨 米類」，GPT 會分析為：
    # {
    #   "category_hierarchy": {
    #     "L1": "常溫食品",
    #     "L2": "五穀/豆類/米麵/乾貨",
    #     "L3": "米類"
    #   },
    #   "required_terms": ["米"],
    #   "excluded_terms": [],
    #   "budget": None,
    #   "intent": "search"
    # }
    
    return result
```

#### 🔍 `_build_category_hierarchy_prompt()` 提供了什麼信息？

```python
def _build_category_hierarchy_prompt() -> str:
    """
    構造 GPT 的分類層級背景知識
    """
    categories_text = """
已知商品分類層級：
- 常溫食品 > 五穀/豆類/米麵/乾貨 > 米類
- 常溫食品 > 五穀/豆類/米麵/乾貨 > 麵類
- 常溫食品 > 調味油 > 橄欖油
- 常溫食品 > 飲料 > 咖啡
- ...
    """
    
    return f"""
{categories_text}

分析使用者查詢時：
1. 盡可能識別 L1 (大分類)、L2 (中分類)、L3 (小分類)
2. 返回 category_hierarchy 物件
3. 若未能完整識別，仍可部分填補

範例：
使用者說「米類」 → category_hierarchy: {{L1: "常溫食品", L2: "五穀/豆類/米麵/乾貨", L3: "米類"}}
使用者說「米」 → category_hierarchy: {{L1: "常溫食品", L2: "五穀/豆類/米麵/乾貨", L3: ""}}
    """
```

---

## 🟡 排序與特價優先 (Line ~630-670)

```python
# Step 4: 特價優先排序
if prefer_special_first:
    def _has_special(rec):
        special = rec.get("SpecialOffer") or rec.get("特價")
        if special:
            return True
        # 比價：特價 < 原價
        price = float(rec.get("Price") or 0)
        sp = float(rec.get("SpecialOffer") or 0)
        return sp and price and sp < price
    
    # 有特價的商品排前面
    records = sorted(
        list(enumerate(records)),
        key=lambda t: (0 if _has_special(t[1]) else 1, t[0])
    )
    records = [rec for _, rec in records]

# Step 5: LLM 重排（可選）
if SEARCH_USE_RERANK:
    records = llm_rerank_products(
        req.query,
        expanded,
        records,
        use_search_config=True
    )
```

---

## 🔴 回應格式 (Line ~680-700)

```python
return JSONResponse({
    "message": f"為您找到 {len(items)} 項商品",
    "items": [
        {
            "商品名稱": "泰國香米 5kg",
            "商品編號": "G001",
            "商品特價": "NT$250",
            "商品購物網址": "https://...",
            "CateName_L1": "常溫食品",
            "CateName_L2": "五穀/豆類/米麵/乾貨",
            "CateName_L3": "米類",
            "hierarchy_score": 9,           # 匹配所有 3 層 = 9 分
            "matched_levels": ["L1", "L2", "L3"]
        },
        ...
    ],
    "page": 1,
    "page_size": 30,
    "has_next": false,
    "last_page": 1,
    "intent": {
        "category_hierarchy": {"L1": "常溫食品", "L2": "五穀/豆類/米麵/乾貨", "L3": "米類"},
        "required_terms": ["米"],
        "excluded_terms": []
    }
})
```

---

## 📊 完整查詢流程圖

```
前端 (用戶點擊「米類」)
   ↓
   構造 payload:
   {
     query: "常溫食品 五穀/豆類/米麵/乾貨 米類",
     category_hierarchy: {L1: "常溫食品", L2: "五穀/豆類/米麵/乾貨", L3: "米類"},
     prefer_special_first: true
   }
   ↓
POST /api/search
   ↓
後端 Step 1: LLM 意圖分析
   llm_analyze_query("常溫食品 五穀/豆類/米麵/乾貨 米類")
   ↓ 返回：
   {
     category_hierarchy: {L1: "常溫食品", L2: "五穀/豆類/米麵/乾貨", L3: "米類"},
     required_terms: ["米"],
     excluded_terms: []
   }
   ↓
後端 Step 2: 基礎搜尋
   search_products(df, "米 白米 長粒米...", topn=60)
   ↓ 返回 60 個候選商品
   ↓
後端 Step 3: 分類過濾 ⭐️ 核心步驟
   _filter_by_hierarchy(records, {L1: "常溫食品", L2: "五穀/豆類/米麵/乾貨", L3: "米類"})
   ↓ 只保留滿足：
      CateName_L1 包含 "常溫食品" AND
      CateName_L2 包含 "五穀/豆類/米麵/乾貨" AND
      CateName_L3 包含 "米類"
   ↓ 返回 10-20 個米類商品
   ↓
後端 Step 4: 特價優先排序
   prefer_special_first: true
   ↓ 特價商品排前面
   ↓
後端 Step 5: 特殊排序（可選）
   if SEARCH_USE_RERANK:
       llm_rerank_products(...)
   ↓ 可能根據相關性再調整順序
   ↓
後端返回 30 個結果
   ↓
前端接收 JSON
   {
     items: [米商品1, 米商品2, ...],
     message: "找到 X 個商品",
     intent: {category_hierarchy: ...}
   }
   ↓
前端調用 announceCategorySearchResult()
   ↓
聊天區展示：
   ▌我
   米類
   
   ▌助手
   根據您的需求「米類」，我為您找到 15 款相關商品。
   1. 商品名稱：泰國香米 5kg
      商品編號：G001
      商品價格：NT$250
      購物連結：https://...
   2. 商品名稱：日本越光米 3kg
      商品編號：G002
      ...
   …還有 13 款商品，可在商品列表中查看。
```

---

## 🎯 LLM 在米類查詢中的角色

### ✅ LLM 的工作：

1. **意圖分析** (`llm_analyze_query`)
   - 輸入：「米類」
   - 分析：這是一個分類搜尋，應該識別為 L3 層級
   - 輸出：`category_hierarchy: {L1: "常溫食品", L2: "五穀/豆類/米麵/乾貨", L3: "米類"}`

2. **查詢擴展** (`llm_expand_query`)
   - 輸入：「米類」
   - 擴展：「米 白米 長粒米 短粒米 米粒 米飯」
   - 用途：讓搜尋更寬泛，不遺漏相關商品

3. **重排優化** (`llm_rerank_products`) - 可選
   - 基於語義相關性重新排序結果

### 📋 LLM 配置檢查

```bash
# 檢查你的環境變數
echo $SEARCH_USE_LLM_INTENT      # 應該 = True（意圖分析）
echo $SEARCH_USE_LLM_EXPAND      # 應該 = True（查詢擴展）
echo $SEARCH_USE_LLM_RERANK      # 應該 = False（不需要重排）
echo $OPENAI_MODEL               # 應該 = gpt-4o-mini
echo $OPENAI_API_KEY             # 應該已設定
```

---

## 🔧 測試方法

### 方法 1：直接呼叫 API

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "常溫食品 五穀/豆類/米麵/乾貨 米類",
    "category_hierarchy": {
      "L1": "常溫食品",
      "L2": "五穀/豆類/米麵/乾貨",
      "L3": "米類"
    },
    "page": 1,
    "page_size": 30,
    "prefer_special_first": true
  }' | jq .
```

預期結果：返回 10-20 個米類商品

### 方法 2：在前端測試

1. 打開 http://localhost:8000（由 FastAPI 提供）
2. 進入「熱門分類」區域
3. 展開「常溫常溫食品」> 「五穀/豆類/五穀/豆類/米麵/乾貨/乾貨」
4. 點擊「米類」
5. 觀察聊天區是否顯示米商品

### 方法 3：查看後端日誌

```bash
cd backend
python -u app.py 2>&1 | grep -i "hierarchy"
```

---

## 📈 資料流時序圖

```
時間    前端              網路                後端           LLM
────────────────────────────────────────────────────────────────
T0      [用戶點擊米類]
        ├→ 記錄 L3=米類
        └→ 構造 payload
        
T1      ├─────────────────────── POST /api/search ─────────────┐
        
T2                                  ├ 執行 llm_analyze_query  │
        
T3                                  │    ├─── 分類分析 ───────┼→ GPT
        
T4                                  │ ◀────── 返回意圖 ◀──────┼── GPT
        
T5                                  ├ 執行 search_products
        
T6                                  ├ 執行 _filter_by_hierarchy
        
T7                                  ├ 執行排序邏輯
        
T8      ◀─────────────────── JSON 響應 ◀────────────────────────┘
        
T9      ├ 解析 items
        └ 呼叫 announceCategorySearchResult
        
T10     └─ 聊天區顯示結果

總耗時：1-3 秒（網路 + LLM API 延遲）
```

---

## 💡 關鍵設計點

1. **前端優先傳層級**
   - 前端直接傳 `category_hierarchy: {L1, L2, L3}`
   - 後端會優先使用前端傳來的層級，而不是依賴 LLM 分析
   - 好處：避免 LLM 誤判

2. **分層過濾的精確性**
   - 只有同時滿足 L1、L2、L3 的商品才會被保留
   - 確保結果高度相關

3. **特價優先**
   - `prefer_special_first: true` 自動將有特價的商品排到前面
   - 提高轉化率

4. **多重排序**
   ```
   優先度 1: 層級匹配程度 (hierarchy_score)
   優先度 2: 是否有特價
   優先度 3: LLM 重排 (若啟用)
   優先度 4: 搜尋評分
   ```

5. **優雅降級**
   ```
   若過濾後為空 → 回傳原始搜尋結果
   若 LLM 分析失敗 → 使用原始查詢
   若 LLM 重排失敗 → 保留現有排序
   ```

---

## 🐛 可能的問題與除錯

| 問題 | 原因 | 解決方案 |
|------|------|----------|
| 搜尋結果為空 | CSV 中沒有符合的 L3 分類 | 檢查 `VIEW_GOODS_enhanced.csv` 中的 `CateName_L3` 欄位 |
| 返回的不是米類商品 | `CateName_L3` 欄位名稱不符 | 檢查 CSV 欄位名稱，調整過濾邏輯 |
| LLM 分類分析錯誤 | OPENAI_API_KEY 無效或模型不匹配 | 檢查 `.env`，確保 API key 有效 |
| 聊天區不顯示結果 | 前端未正確調用 `announceCategorySearchResult` | 檢查瀏覽器 Console 是否有 JavaScript 錯誤 |
| 特價排序不生效 | `SpecialOffer` 欄位為空或值不正確 | 檢查 CSV 中的特價欄位值格式 |

---

## 📝 環境變數清單

```bash
# LLM 配置
OPENAI_API_KEY=sk-...                           # 必須
OPENAI_MODEL=gpt-4o-mini                        # 可選，默認 gpt-4o-mini
SEARCH_USE_LLM_INTENT=True                      # 意圖分析
SEARCH_USE_LLM_EXPAND=True                      # 查詢擴展
SEARCH_USE_LLM_RERANK=False                     # 重排（通常關閉）

# 資料路徑
DATA_PATH=/path/to/VIEW_GOODS_enhanced.csv      # CSV 位置
CATEGORIES_PATH=/path/to/goods_categories.csv   # 分類表

# 前端 URL
SITE_URL=https://goodsearch.netlify.app         # 前端部署位置
```

---

## ✨ 總結

當用戶點擊「米類」時：

1. **前端** 記錄分類層級並發送查詢
2. **後端 LLM** 驗證意圖分析
3. **基礎搜尋** 找出候選商品
4. **分層過濾** 保留只符合「常溫食品 > 五穀/豆類/米麵/乾貨 > 米類」的商品
5. **特價優先** 將特價商品排到前面
6. **LLM 重排** (可選) 根據相關性調整順序
7. **前端** 在聊天區優雅地展示結果

整個流程確保了高精確度、好相關性、快速回應。

