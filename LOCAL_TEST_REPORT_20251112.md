# 🧪 本地測試報告 - 木茸查詢優化驗證 (2025-11-12)

**測試日期**: 2025-11-12  
**測試目的**: 驗證 IMPORTANT_CATEGORY_EXAMPLES 和優化後的 Prompt 功能

---

## 📊 測試環境

### 後端服務 (Port 8000)
```
✅ 啟動成功
INFO: Uvicorn running on http://0.0.0.0:8000
INFO: Application startup complete.

✅ 數據載入:
- 文本快取: 953 行商品
- 分類索引: L1(5) / L2(15) / L3(48)
- 分類同義詞: 65 個

✅ 代碼修改應用:
- IMPORTANT_CATEGORY_EXAMPLES 字典: ✅ 已載入
- _build_category_hierarchy_prompt(): ✅ 已更新
```

### 前端服務 (Port 5173)
```
✅ 啟動成功
Serving HTTP on :: port 5173
✅ 瀏覽器訪問: http://localhost:5173
```

---

## ⚠️ 關鍵發現: LLM 功能未啟用

### 後端日誌顯示
```
INFO:search_goods:📝 LLM 搜尋模型配置:
INFO:search_goods:  - 查詢擴展啟用: False  ❌
INFO:search_goods:  - 意圖分析啟用: False  ❌
INFO:search_goods:  - 結果重排啟用: False  ❌

[DEBUG] OPENAI_API_KEY is placeholder value  ❌
INFO:llm_service:      - 略過 (use_intent=False, client=False)
```

### 根本原因
```bash
# backend/.env 檔案
OPENAI_API_KEY=your-openai-api-key  ❌ 佔位符值

# 雖然開關設定正確:
USE_LLM_EXPAND=True   ✅
USE_LLM_INTENT=True   ✅
```

### 影響
1. ❌ 優化後的 Prompt 無法使用
2. ❌ 無法識別「木茸」為「烹調食材」分類
3. ❌ 商品搜尋退化為純文本匹配

---

## 🔍 搜尋結果分析

### API 測試
```bash
curl -X POST "http://localhost:8000/api/search" \
  -d '{"query": "台灣日曬木茸", "topn": 10}'

回應: ❌ 找到 10 筆非相關商品
1. 米森有機黑糖老薑茶
2. 真粥道風味素肉粥
3. 星米果-蒜香海苔
...
```

### 基礎搜尋測試 (debug_mushroom_search.py)
```
1. 台灣日曬木茸/100g     (分數: 39.00) ✅ 最相關
2. 台灣日曬香菇/100g     (分數: 18.00) ✅ 相關
3. 休閒包-黃貓            (分數: 5.50)  ❌ 不相關
4-6. 有機米類             (分數: 5.50)  ⚠️ 可接受
7. 萌貓經典包             (分數: 4.00)  ❌ 不相關
8-10. 天然醬油            (分數: 3.00)  ⚠️ 可接受
```

---

## ✅ 測試結論

### 成功部分
1. ✅ 代碼優化已正確應用
2. ✅ 服務正常運行
3. ✅ 基礎搜尋有效 (木茸排名第 1)

### 待驗證部分
1. ⏳ LLM 分類識別 (需要真實 API key)
2. ⏳ 商品過濾效果 (需要 LLM 啟用)
3. ⏳ 查詢擴展功能 (需要 LLM 啟用)

---

## 🎯 下一步行動

### 完整功能測試 (需要設定 API key)
```bash
# 編輯 backend/.env
OPENAI_API_KEY=sk-your-real-api-key-here

# 重啟服務並重新測試
```

**預期結果** (設定 API key 後):
- LLM 識別「木茸」為「烹調食材」✅
- 過濾不相關商品 (包包類) ✅
- 查詢擴展: "木茸" → "菇類、食材" ✅

### 程式碼改進 (不依賴 LLM)
1. 改進 search_products() 加入分類過濾
2. 提升分類匹配權重
3. 建立靜態同義詞表

---

**報告完成** | 下一步: 設定 OPENAI_API_KEY 並重新測試
