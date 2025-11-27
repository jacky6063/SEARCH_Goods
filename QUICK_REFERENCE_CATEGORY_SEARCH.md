# 米類搜尋流程 - 快速參考卡

## 🎯 用戶動作
```
點擊「米類」按鈕
```

## 📍 關鍵數據傳遞

### 前端發送 (Line ~540)
```json
POST http://localhost:8000/api/search
{
  "query": "常溫食品 五穀/豆類/米麵/乾貨 米類",
  "category_hierarchy": {
    "L1": "常溫食品",
    "L2": "五穀/豆類/米麵/乾貨", 
    "L3": "米類"           ⭐️ 核心指標
  },
  "prefer_special_first": true,
  "page": 1,
  "page_size": 30
}
```

### 後端處理流程

```
Step 1: LLM 意圖分析 (llm_analyze_query)
  ├─ 輸入："常溫食品 五穀/豆類/米麵/乾貨 米類"
  ├─ GPT 分析：識別分類層級
  └─ 輸出：category_hierarchy 結構化物件

Step 2: 基礎搜尋 (search_products)
  ├─ 擴展查詢："米 白米 長粒米 短粒米..."
  ├─ 在 953 個商品中搜尋
  └─ 返回 60 個候選

Step 3: 分層過濾 ⭐️ (_filter_by_hierarchy)
  ├─ 檢查 CateName_L1 是否包含 "常溫食品"
  ├─ 檢查 CateName_L2 是否包含 "五穀/豆類/米麵/乾貨"
  ├─ 檢查 CateName_L3 是否包含 "米類"
  └─ 只保留全部符合的商品 (通常 10-20 個)

Step 4: 特價優先排序
  └─ 將有 SpecialOffer 的商品排到前面

Step 5: LLM 重排 (可選)
  └─ 如果啟用 SEARCH_USE_LLM_RERANK

Step 6: 分頁處理
  └─ 返回 30 個結果給前端
```

### 後端回應 (Line ~680)
```json
{
  "message": "為您找到 X 款相關商品",
  "items": [
    {
      "商品名稱": "泰國香米 5kg",
      "商品編號": "G001",
      "商品特價": "NT$250",
      "商品購物網址": "https://...",
      "CateName_L1": "常溫食品",
      "CateName_L2": "五穀/豆類/米麵/乾貨",
      "CateName_L3": "米類",
      "hierarchy_score": 9,        ← 三層都符合 = 9 分
      "matched_levels": ["L1", "L2", "L3"]
    },
    ...
  ],
  "intent": {
    "category_hierarchy": {"L1": "常溫食品", "L2": "五穀/豆類/米麵/乾貨", "L3": "米類"}
  }
}
```

### 前端展示 (Line ~895)
```javascript
聊天區顯示：

▌用戶
米類

▌助手
根據您的需求「米類」，我為您找到 15 款相關商品。
1. 商品名稱：泰國香米 5kg
   商品編號：G001
   商品價格：NT$250
   購物連結：https://...
2. 商品名稱：日本越光米 3kg
   ...
…還有 13 款商品，可在商品列表中查看。
```

---

## 🔍 LLM 在此流程中的作用

| 階段 | LLM 函數 | 作用 | 輸入 | 輸出 |
|------|---------|------|------|------|
| **1** | `llm_analyze_query()` | 意圖分析 | "常溫食品 五穀/豆類/米麵/乾貨 米類" | `{category_hierarchy: {L1, L2, L3}}` |
| **2** | `llm_expand_query()` | 查詢擴展 | "常溫食品 五穀/豆類/米麵/乾貨 米類" | "米 白米 長粒米 短粒米..." |
| **5** | `llm_rerank_products()` | 結果重排 | query + items | 重新排序的 items |

---

## 🐞 測試和除錯

### 查看後端日誌
```bash
cd backend && python -u app.py 2>&1 | grep -i hierarchy
```

期望看到：
```
[INFO] Hierarchy search: matched 15 products with levels ['L1', 'L2', 'L3']
```

### 直接測試 API
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "常溫食品 五穀/豆類/米麵/乾貨 米類",
    "category_hierarchy": {"L1": "常溫食品", "L2": "五穀/豆類/米麵/乾貨", "L3": "米類"},
    "page": 1,
    "page_size": 30,
    "prefer_special_first": true
  }' | jq '.items | length'
```

期望結果：應該返回 10-30 個商品

### 檢查前端行為
1. 打開瀏覽器 DevTools (F12)
2. 點擊「米類」
3. 在 Console 中執行：
   ```javascript
   // 檢查最後一條 API 請求
   console.log(chatHistory[chatHistory.length - 1]);
   
   // 應該顯示：
   // {role: "assistant", content: "根據您的需求「米類」，我為您找到 15 款相關商品。\n1. ..."}
   ```

---

## 📊 分類過濾的核心邏輯

```python
# app.py Line ~520
def _filter_by_hierarchy(records, hierarchy):
    l1 = hierarchy.get("L1")  # "常溫食品"
    l2 = hierarchy.get("L2")  # "五穀/豆類/米麵/乾貨"
    l3 = hierarchy.get("L3")  # "米類"
    
    filtered = []
    for rec in records:
        # 三個條件都要滿足：
        if (l1 in rec["CateName_L1"] and
            l2 in rec["CateName_L2"] and
            l3 in rec["CateName_L3"]):
            filtered.append(rec)
    
    return filtered
```

---

## ⚙️ 環境變數檢查表

```bash
# 必須設定
✓ OPENAI_API_KEY=sk-...

# 搜尋配置（影響米類搜尋）
✓ SEARCH_USE_LLM_INTENT=True         # 意圖分析
✓ SEARCH_USE_LLM_EXPAND=True         # 查詢擴展  
✓ SEARCH_USE_LLM_RERANK=False        # 通常關閉

# CSV 配置
✓ DATA_PATH=/path/to/VIEW_GOODS_enhanced.csv
✓ CATEGORIES_PATH=/path/to/goods_categories.csv
```

---

## 🎬 完整時序

```
T0: 用戶點擊「米類」
   ↓
T1: 前端構造 payload (hotScopePath 記錄 L3)
   ↓
T2: 發送 POST http://localhost:8000/api/search (100ms)
   ↓
T3: 後端 LLM 分析 (500-1000ms) ← GPT 呼叫
   ↓
T4: 基礎搜尋 (50-100ms)
   ↓
T5: 分層過濾 (10-50ms) ⭐️ 最快
   ↓
T6: 特價排序 (10-50ms)
   ↓
T7: 後端返回 JSON (100ms)
   ↓
T8: 前端解析並調用 announceCategorySearchResult()
   ↓
T9: 聊天區顯示結果 (100ms)
   ↓
T10: 完成！(總計 1-2 秒)
```

---

## 💾 相關檔案位置

| 內容 | 檔案 | 行數 |
|------|------|------|
| L3 分類觸發 | frontend/index.html | ~540 |
| 聊天區展示 | frontend/index.html | ~895 |
| 搜尋端點 | backend/app.py | ~560 |
| 分層過濾 | backend/app.py | ~511 |
| LLM 意圖分析 | backend/llm_service.py | ~934 |
| 分類搜尋函數 | backend/llm_service.py | ~704 |

---

## ✨ 快速診斷清單

```
□ 是否收到搜尋結果？
  ├─ No → 檢查 API 日誌，LLM 是否正確分析
  └─ Yes → 繼續

□ 結果是否都是米類商品？
  ├─ No → 檢查 CSV 的 CateName_L3 欄位值
  └─ Yes → 繼續

□ 特價商品是否排在前面？
  ├─ No → 檢查 prefer_special_first 是否傳入
  └─ Yes → ✅ 工作正常！

□ 聊天區是否顯示結果摘要？
  ├─ No → 檢查瀏覽器 Console 是否有錯誤
  └─ Yes → ✅ 完美！
```

