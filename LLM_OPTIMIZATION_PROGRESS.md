# LLM 搜尋優化實施進度

## ✅ 已完成 (Commit: 97de764)

### 步驟 1️⃣: 提取分類同義詞庫
- ✅ `_extract_category_synonyms()` - 自動從 CSV L1/L2/L3 提取分類
- ✅ 模組載入時初始化 `_CATEGORY_SYNONYMS_CACHE`
- ✅ 支援快取機制，避免重複計算

### 步驟 2️⃣: 優化 LLM 分析函數  
- ✅ `llm_analyze_query()` 新增 `category_hierarchy` 欄位
- ✅ 新增 `hierarchy_confidence` 信心度評分
- ✅ `_build_category_hierarchy_prompt()` 動態生成提示詞
- ✅ 自動檢測和填充空層級

### 步驟 3️⃣: 創建層級搜尋函數
- ✅ `_search_by_category_hierarchy()` 實現多層過濾
- ✅ L1→L2→L3 逐級細化搜尋
- ✅ 返回 `matched_levels` 和 `hierarchy_score`
- ✅ 支援中英文欄位名

---

## ⏳ 待實施 (第 4-6 步)

### 步驟 4️⃣: 整合到 `_search_products_for_chat()`
**位置**: llm_service.py ~1550 行

**修改方式**:
```python
def _search_products_for_chat(
    query: str, 
    keywords: List[str], 
    topn: int = 5, 
    filters: Optional[Dict[str, Any]] = None,
    hierarchy: Optional[Dict[str, str]] = None  # 🆕 新參數
) -> Dict[str, List[Dict[str, Any]]]:
    result = {"exact": [], "fuzzy": []}
    
    # 🆕 優先使用層級搜尋
    if hierarchy and any(hierarchy.get(k) for k in ["L1", "L2", "L3"]):
        df = _get_chat_df()
        if df is not None and not df.empty:
            hierarchy_results = _search_by_category_hierarchy(df, hierarchy, topn)
            if hierarchy_results:
                result["hierarchy"] = hierarchy_results
                return result
    
    # 原有的模糊搜尋邏輯保持不變
    # ... 現有代碼
```

### 步驟 5️⃣: 在 `chat_reply()` 中使用層級搜尋
**位置**: llm_service.py ~1956 行

**修改方式**:
```python
def chat_reply(...):
    # ... 現有代碼
    
    # 🆕 優先呼叫 llm_analyze_query 得到分類層級
    analysis = llm_analyze_query(user_message, use_search_config=False)
    category_hierarchy = analysis.get("category_hierarchy", {})
    
    # 🆕 若識別到分類層級，使用層級搜尋
    if category_hierarchy and any(category_hierarchy.get(k) for k in ["L1", "L2", "L3"]):
        products = _search_products_for_chat(
            user_message, 
            keywords,
            topn=6,
            filters=structured_filters,
            hierarchy=category_hierarchy  # 🆕 傳入層級
        )
        # 處理 products["hierarchy"] 結果
    else:
        # 原有的關鍵詞搜尋
        products = _search_products_for_chat(...)
```

### 步驟 6️⃣: 前端展示層級信息
**位置**: frontend/index.html

**展示方式**:
- 搜尋結果中顯示 "分類路徑": 食品 > 調味品 > 橄欖油
- 支援點擊分類進行二次搜尋
- 顯示 LLM 信心度: "98% 確信您要找食品類調味品"

---

## 🎯 優化效果驗證

### 測試場景

#### 1️⃣ L3 精確搜尋
```
用戶: "橄欖油"
LLM: 識別 L3="橄欖油"
結果: 返回橄欖油商品
```

#### 2️⃣ L1+L2+L3 完整路徑
```
用戶: "食品類的調味油橄欖油"
LLM: L1="食品" + L2="調味油" + L3="橄欖油"
結果: 精確返回相關商品
```

#### 3️⃣ 非食品查詢不混入食品
```
用戶: "包"
LLM: L1="" (未識別為食品)
結果: 只返回包類商品，不包含食品
```

---

## 📊 架構圖

```
用戶查詢 "我要買食品類調味油"
    ↓
【新】llm_analyze_query()
    ↓ 識別分類層級
category_hierarchy: {L1:"食品", L2:"調味油", L3:""}
    ↓
【新】_search_products_for_chat(hierarchy=...)
    ↓
【新】_search_by_category_hierarchy()
    ↓ L1→L2→L3 層級過濾
① 過濾 L1="食品"
② 再過濾 L2="調味油"
③ 返回結果標記層級信息
    ↓
✅ 精確返回調味油商品
   (matched_levels: ["L1", "L2"], hierarchy_score: 6)
```

---

## 🔧 後續考慮

1. **性能優化**
   - [ ] 考慮添加分類層級索引加快查詢
   - [ ] 快取常見查詢的層級結果

2. **用戶體驗**
   - [ ] 前端顯示搜尋過程 ("正在分析分類...")
   - [ ] 顯示 LLM 信心度視覺化
   - [ ] 支援分類層級面包屑導航

3. **資料品質**
   - [ ] 定期檢查 CSV L1/L2/L3 的資料品質
   - [ ] 識別和清理重複/不規範的分類名稱

---

## 📝 相關文件

- **主文件**: `backend/llm_service.py`
- **測試**: 可用 `/api/chat` 端點進行端到端測試
- **配置**: 無需額外配置，自動啟用

