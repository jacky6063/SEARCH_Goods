# 聊天模式 LLM 判讀與商品搜尋流程

## 📊 整體架構流程圖

```
用戶在前端輸入查詢
        ↓
   ┌────────────────────────────────────────────┐
   │  API 端點：POST /api/chat                   │
   │  Frontend → Backend (Chat Request)         │
   │  app.py:1373 @app.post("/api/chat")        │
   └────────────────────────────────────────────┘
        ↓
   ┌────────────────────────────────────────────┐
   │ chat_endpoint(req: ChatReq)                │
   │ app.py:1373-1409                           │
   │ 作用：接收聊天請求，調用 chat_handler     │
   └────────────────────────────────────────────┘
        ↓
   ┌────────────────────────────────────────────────────────────────┐
   │ chat_handler(req) 分派邏輯                                     │
   │ chat_router_goods_action.py:1356                               │
   │ 核心：執行 _legacy_chat_flow() 邏輯                           │
   │                                                                │
   │ [決策點] 快速判讀用戶意圖：                                    │
   │  1️⃣  類目導覽檢測 (L1→L2→L3)                                 │
   │  2️⃣  概覽/販售範圍檢測                                       │
   │  3️⃣  LLM 聊天模式判讀                                        │
   │  4️⃣  強制 LLM 互動                                           │
   └────────────────────────────────────────────────────────────────┘
        ↓
   ┌─────────────────────────────────────────────────┐
   │ ❌ 否 → 是否為「類目導覽」查詢？               │
   │ _try_category_navigation_reply()               │
   │ chat_router_goods_action.py:919               │
   │                                               │
   │ 匹配模式：「在X下」、「X的品類」              │
   │ 提供 L2 或 L3 的品類清單                      │
   │ 返回分類導覽模式                             │
   └─────────────────────────────────────────────────┘
        ↓ [是]
   📋 分類導覽回覆
        ↓ [否]
   ┌─────────────────────────────────────────────────┐
   │ ❌ 否 → 是否為「概覽」查詢？                    │
   │ _try_overview_scope_reply()                    │
   │ chat_router_goods_action.py:850               │
   │                                               │
   │ 匹配模式：「賣什麼」、「有哪些」              │
   │ 從 /api/catalog/scope 讀取 Top-K L1 分類    │
   │ 返回商品販售範圍概覽                         │
   └─────────────────────────────────────────────────┘
        ↓ [是]
   📊 概覽回覆 (Top-K L1 列表)
        ↓ [否]
   ┌──────────────────────────────────────────────────────────────┐
   │ 進入 LLM 判讀階段                                            │
   │ _legacy_chat_flow() → chat_reply()                           │
   │ llm_service.py:2200+                                         │
   │                                                              │
   │ 🔑 核心決策邏輯                                             │
   └──────────────────────────────────────────────────────────────┘
        ↓
   ┌──────────────────────────────────────────────────────────────┐
   │ 🎯 Step 1: LLM 意圖分析                                      │
   │ llm_analyze_query(query, use_search_config=False)            │
   │ llm_service.py:1740                                          │
   │                                                              │
   │ 輸入：用戶查詢原文                                          │
   │ 輸出 JSON：{                                                │
   │   "required_terms": [...],   # 必須條件                    │
   │   "category_terms": [...],   # 分類建議                    │
   │   "excluded_terms": [...],   # 排除詞                      │
   │   "category_hierarchy": {    # 🆕 分類層級識別             │
   │     "L1": "",   # 大分類                                    │
   │     "L2": "",   # 中分類                                    │
   │     "L3": ""    # 小分類                                    │
   │   },                                                        │
   │   "hierarchy_confidence": {  # 信心度                       │
   │     "L1": 0.9,                                             │
   │     "L2": 0.7,                                             │
   │     "L3": 0.5                                              │
   │   }                                                         │
   │ }                                                           │
   │                                                              │
   │ LLM 模型：CHAT_OPENAI_MODEL                                │
   │ 啟用條件：CHAT_USE_INTENT=True                             │
   └──────────────────────────────────────────────────────────────┘
        ↓
   ┌──────────────────────────────────────────────────────────────┐
   │ 🎯 Step 2: 對話意圖分類                                     │
   │ _detect_conversation_intent(query)                           │
   │ llm_service.py:1570                                          │
   │                                                              │
   │ 決策樹：                                                     │
   │  ├─ 概覽/導航 → "information"                              │
   │  ├─ 健康/使用/知識 → "information"                         │
   │  ├─ 事件/派對/聚會 → "event_food_planning"                 │
   │  ├─ 推薦/建議 → "information"                              │
   │  ├─ 購買意圖 → "product_search"                            │
   │  └─ 預設 → "general"                                       │
   │                                                              │
   │ 返回：意圖類型字符串                                        │
   └──────────────────────────────────────────────────────────────┘
        ↓
   ┌────────────────────────────────────────────┐
   │ [分支] 根據意圖類型執行不同邏輯              │
   └────────────────────────────────────────────┘
        ↓
   ┌─────────────────────────────────────────────────┐
   │ 🔀 分支 A：「information」（資訊諮詢）        │
   │ _call_chat_for_information()                   │
   │ llm_service.py:1631                           │
   │                                               │
   │ 情景：用戶詢問產品知識、使用方法、健康效果   │
   │ 作用：由 LLM 直接回答資訊性問題              │
   │ 輸出：資訊回覆 + 自然引導語                  │
   │ 範例：「椰子油有什麼健康好處？」              │
   │      → LLM 回答 + 「您需要推薦相關產品嗎？」  │
   └─────────────────────────────────────────────────┘
        ↓
   📚 資訊回覆（不涉及商品搜尋）
        ↓
   ┌─────────────────────────────────────────────────┐
   │ 🔀 分支 B：「event_food_planning」（活動策劃） │
   │ run_fallback() 或自訂邏輯                      │
   │ fallback/multi_category_party.py               │
   │                                               │
   │ 情景：用戶策劃派對/聚會/活動，需要商品建議   │
   │ 作用：理解活動類型，推薦相應商品組合         │
   │ 輸出：活動導購回覆 + 商品清單                │
   │ 範例：「幫我準備生日聚會」                    │
   │      → 分析聚會人數、風格、預算              │
   │      → 推薦相應商品組合                      │
   └─────────────────────────────────────────────────┘
        ↓
   🎉 活動導購回覆
        ↓
   ┌──────────────────────────────────────────────────────────────┐
   │ 🔀 分支 C：「product_search」（商品搜尋）✨ [主流程]      │
   │ _prepare_chat_context() → _search_products_for_chat()        │
   │ llm_service.py:1443-1485                                     │
   │                                                              │
   │ [核心商品搜尋引擎]                                          │
   └──────────────────────────────────────────────────────────────┘
        ↓
   ┌──────────────────────────────────────────────────────────────┐
   │ 🎯 Step 3: 商品搜尋準備                                     │
   │ _prepare_chat_context(user_message, catalog)                │
   │ llm_service.py:1443                                          │
   │                                                              │
   │ 提取：                                                      │
   │  • keywords：從查詢中抽取關鍵詞                            │
   │  • structured_filters：價格/預算過濾                       │
   │  • category_hierarchy：L1/L2/L3 分類層級                  │
   │                                                              │
   │ 返回完整上下文：{                                           │
   │   "query": "",                  # 清理後的查詢              │
   │   "keywords": [...],            # 關鍵詞列表                │
   │   "products": [...],            # 搜尋結果                  │
   │   "structured_filters": {...},  # 篩選器                   │
   │   "overview": {...}             # 分類概覽（如需）          │
   │ }                                                            │
   └──────────────────────────────────────────────────────────────┘
        ↓
   ┌──────────────────────────────────────────────────────────────┐
   │ 🎯 Step 4: 多層次商品搜尋                                   │
   │ _search_products_for_chat(query, keywords, filters, hierarchy)│
   │ llm_service.py:1254                                          │
   │                                                              │
   │ 搜尋優先級（按順序）：                                     │
   │                                                              │
   │ 1️⃣  分類層級搜尋（如可用）                                 │
   │     _search_by_category_hierarchy()                         │
   │     llm_service.py:1100                                      │
   │                                                              │
   │     - 從 LLM 分析中提取 L1/L2/L3                          │
   │     - 多層過濾：L1 → L2 → L3                              │
   │     - 返回分類完全匹配的商品                              │
   │     - 評分：matched_levels * 3 分                         │
   │                                                              │
   │ 2️⃣  模糊搜尋 (Fallback)                                    │
   │     search_products() from goods_search_service.py           │
   │     llm_service.py:1275                                      │
   │                                                              │
   │     - 使用傳統的名稱+描述+分類匹配                        │
   │     - 計分算法：名稱 +2，描述 +1，分類 +1                 │
   │     - 最低分門檻：1.5 分                                   │
   │                                                              │
   │ 3️⃣  結構化篩選 (Filter)                                    │
   │     _apply_structured_filters()                             │
   │     llm_service.py:1229                                      │
   │                                                              │
   │     - 應用 must_have_keywords：所有必須詞必須出現          │
   │     - 應用 excluded_keywords：排除詞不能出現              │
   │     - 應用 price_filter：價格在範圍內                      │
   │                                                              │
   │ 4️⃣  嚴格搜尋 (Strict Mode)                                 │
   │     search_products_strict()                                │
   │     search_ext_goods_1024001.py                             │
   │                                                              │
   │     - 結果不足時觸發                                       │
   │     - 嚴格匹配欄位別名和數值過濾                         │
   │                                                              │
   │ 5️⃣  關鍵詞篩選                                             │
   │     _filter_products_by_keywords()                          │
   │     llm_service.py:1308                                      │
   │                                                              │
   │     - 進一步過濾，確保匹配關鍵詞                         │
   │                                                              │
   │ 返回結果集：{                                              │
   │   "exact": [...],   # 精確匹配（分類層級）                │
   │   "fuzzy": [...]    # 模糊匹配（傳統搜尋）                │
   │ }                                                            │
   └──────────────────────────────────────────────────────────────┘
        ↓
   ┌──────────────────────────────────────────────────────────────┐
   │ 🎯 Step 5: LLM 查詢擴展（可選）                            │
   │ llm_expand_query(query, use_search_config=False)            │
   │ llm_service.py:1700                                          │
   │                                                              │
   │ 作用：擴展查詢，包含同義詞和相關詞彙                       │
   │ 啟用條件：CHAT_USE_LLM_EXPAND=True                         │
   │ 範例：「椰子油」→ 「椰子油, 冷壓椰油, 純椰子油」          │
   │ 用途：用擴展查詢再次搜尋以覆蓋同義產品                    │
   └──────────────────────────────────────────────────────────────┘
        ↓
   ┌──────────────────────────────────────────────────────────────┐
   │ 🎯 Step 6: LLM 結果重排序（可選）                          │
   │ llm_rerank_products(user_query, expanded_query, candidates) │
   │ llm_service.py:1851                                          │
   │                                                              │
   │ 作用：LLM 基於語義相關性重新排序候選商品                    │
   │ 啟用條件：CHAT_USE_LLM_RERANK=True（默認 False）          │
   │ 過程：                                                      │
   │   1. 準備最多 15 個候選商品（JSON 格式）                   │
   │   2. 發送給 LLM 進行相關性評分（1-5 分）                   │
   │   3. LLM 返回重排序後的商品列表                           │
   │ 輸出：按相關性排序的商品（最多 topn 個）                   │
   └──────────────────────────────────────────────────────────────┘
        ↓
   ┌──────────────────────────────────────────────────────────────┐
   │ 🎯 Step 7: 生成 Mock 或 LLM 聊天回覆                       │
   │ _mock_or_real_llm() OR _generate_mock_reply()               │
   │ llm_service.py:1486 / 1596                                   │
   │                                                              │
   │ [選擇路徑]                                                   │
   │                                                              │
   │ 路徑 A：存在有效 OpenAI 客戶端                              │
   │   → 調用 LLM chat completions 生成自然對話回覆             │
   │   → 確保回覆包含找到的商品信息                             │
   │   → 返回經 LLM 潤色的商品推薦                              │
   │                                                              │
   │ 路徑 B：無 OpenAI 客戶端或 Mock 模式                        │
   │   → 調用 _generate_mock_reply() 生成模板回覆               │
   │   → 直接組合商品名稱、價格、特價                          │
   │                                                              │
   │ 返回：完整的自然語言回覆                                    │
   └──────────────────────────────────────────────────────────────┘
        ↓
   ┌──────────────────────────────────────────────────────────────┐
   │ 🎯 Step 8: 商品對齊與隱藏 JSON 生成                        │
   │ chat_router_goods_action.py:350-400                         │
   │                                                              │
   │ 作用：提取搜尋到的商品，附加到回覆中                       │
   │                                                              │
   │ 生成隱藏 JSON：{                                            │
   │   "intent": "product_align",                               │
   │   "items": [                                               │
   │     {"id": "商品編號", "name": "商品名稱"},              │
   │     ...                                                     │
   │   ],                                                        │
   │   "need_confirm_show_details": true                        │
   │ }                                                            │
   │                                                              │
   │ 用途：前端解析 JSON，提取商品 ID 用於搜尋結果顯示          │
   └──────────────────────────────────────────────────────────────┘
        ↓
   ┌──────────────────────────────────────────────────────────────┐
   │ 🎯 Step 9: 會話管理與快取                                  │
   │ chat_endpoint() → bundle_service.save_bundle()              │
   │ app.py:1390-1407                                            │
   │                                                              │
   │ 保存內容：                                                  │
   │   • session_id：會話唯一標識                              │
   │   • suggestion_ids：推薦商品 ID 列表                       │
   │   • align_rows：對應的商品詳細資料                         │
   │   • query_terms：用戶的查詢詞                              │
   │   • structured_items：結構化商品信息                       │
   │   • structured_filters：應用的篩選條件                     │
   │                                                              │
   │ TTL：可配置，默認 600 秒                                   │
   │ 用途：前端可透過 /api/chat-session/{session_id} 查詢      │
   └──────────────────────────────────────────────────────────────┘
        ↓
   ┌──────────────────────────────────────────────────────────────┐
   │ 📤 回傳標準 ChatResp 格式                                  │
   │ app.py:1373 response_model=ChatResp                         │
   │                                                              │
   │ 返回 JSON：{                                               │
   │   "reply": "自然語言回覆",                                │
   │   "suggestion_ids": ["id1", "id2", ...],                  │
   │   "session_id": "唯一會話 ID",                            │
   │   "structured_products": [...],                            │
   │   "structured_filters": {...},                             │
   │   "meta": {...}                                            │
   │ }                                                            │
   └──────────────────────────────────────────────────────────────┘
        ↓
   📱 前端接收 JSON 回覆，解析並顯示商品
```

---

## 🔑 核心決策邏輯

### 1️⃣ 意圖分類決策樹

```
用戶查詢
  ├─ 概覽型 ("賣什麼", "有哪些")
  │  └─→ 返回 Top-K L1 分類清單 (概覽模式)
  │
  ├─ 導航型 ("在X下", "X的品類")
  │  └─→ 提供 L2/L3 品類清單 (分類導覽模式)
  │
  ├─ 資訊型 (健康/使用/知識)
  │  └─→ LLM 資訊回答 (不涉及商品搜尋)
  │
  ├─ 活動型 (派對/聚會/慶祝)
  │  └─→ 活動策劃邏輯 (推薦組合)
  │
  └─ 購買型 ✨ [主流程]
     └─→ 執行多層商品搜尋
```

### 2️⃣ 商品搜尋優先級

```
❶ 分類層級搜尋 (最優先)
   ├─ 條件：LLM 成功識別 L1/L2/L3
   ├─ 過程：逐層篩選 (L1 → L2 → L3)
   ├─ 結果：精確分類匹配
   └─ 評分：每匹配層級 +3 分

❷ 模糊搜尋 (傳統搜尋)
   ├─ 條件：分類搜尋結果不足
   ├─ 過程：名稱/描述/分類 多維匹配
   ├─ 計分：名稱 +2, 描述 +1, 分類 +1
   └─ 門檻：最少 1.5 分

❸ 結構化篩選 (同步進行)
   ├─ 必須詞 (must_have_keywords)：必須包含
   ├─ 排除詞 (excluded_keywords)：不能包含
   └─ 價格範圍 (price_filter)：預算過濾

❹ 嚴格搜尋 (備用方案)
   ├─ 條件：普通搜尋結果 < topn
   ├─ 方式：嚴格欄位別名和數值匹配
   └─ 用途：確保最少找到足夠結果

❺ 關鍵詞篩選 (最後過濾)
   ├─ 條件：還有多餘結果
   └─ 方式：確保至少有一個關鍵詞匹配
```

---

## 📍 代碼位置速查表

| 組件 | 文件 | 行號 | 功能 |
|------|------|------|------|
| **API 端點** | app.py | 1373 | @app.post("/api/chat") 聊天入口 |
| **聊天分派** | chat_router_goods_action.py | 1356 | chat_handler() 分派邏輯 |
| **遺留流程** | chat_router_goods_action.py | 1000 | _legacy_chat_flow() 主邏輯 |
| **類目導覽** | chat_router_goods_action.py | 919 | _try_category_navigation_reply() |
| **概覽查詢** | chat_router_goods_action.py | 850 | _try_overview_scope_reply() |
| **意圖分析** | llm_service.py | 1740 | llm_analyze_query() LLM 意圖判讀 |
| **對話意圖** | llm_service.py | 1570 | _detect_conversation_intent() 意圖分類 |
| **搜尋準備** | llm_service.py | 1443 | _prepare_chat_context() 上下文準備 |
| **商品搜尋** | llm_service.py | 1254 | _search_products_for_chat() 多層搜尋 |
| **分類搜尋** | llm_service.py | 1100 | _search_by_category_hierarchy() 層級搜尋 |
| **篩選邏輯** | llm_service.py | 1229 | _apply_structured_filters() 結構化篩選 |
| **查詢擴展** | llm_service.py | 1700 | llm_expand_query() 同義詞擴展 |
| **結果重排** | llm_service.py | 1851 | llm_rerank_products() LLM 重排 |
| **LLM 回覆** | llm_service.py | 1486 | _mock_or_real_llm() LLM 聊天 |
| **Mock 回覆** | llm_service.py | 1596 | _generate_mock_reply() 模板回覆 |
| **會話保存** | app.py | 1390 | bundle_service.save_bundle() 快取管理 |

---

## 🎛️ 環境變數配置

### LLM 功能開關

```bash
# 聊天模式 LLM 配置（強制啟用以確保 LLM 互動）
CHAT_USE_LLM_EXPAND=True          # 查詢擴展
CHAT_USE_LLM_SHORTDESC=True       # 短描述生成
CHAT_USE_LLM_RERANK=False         # 結果重排
CHAT_USE_LLM_INTENT=True          # 意圖分析
CHAT_USE_LLM_PROMO=True           # 行銷文案生成

# 搜尋模式 LLM 配置（可獨立控制）
SEARCH_USE_LLM_EXPAND=False       # 預設關閉，避免搜尋變慢
SEARCH_USE_LLM_SHORTDESC=False
SEARCH_USE_LLM_RERANK=False
SEARCH_USE_LLM_INTENT=False
SEARCH_USE_LLM_PROMO=False

# 模型選擇
OPENAI_API_KEY=sk-...             # OpenAI API 金鑰
OPENAI_MODEL=gpt-4o-mini          # 搜尋模型
CHAT_MODEL=gpt-4o-mini            # 聊天模型（可不同）
CHAT_OPENAI_MODEL=gpt-4o-mini     # 聊天專用模型

# 分類查詢配置
SCOPE_TOPK_L1=8                   # 概覽返回 L1 個數
SCOPE_TOPK_L2=8                   # L2 導覽返回個數
SCOPE_TOPK_L3=8                   # L3 導覽返回個數

# 會話管理
CHAT_ALIGNMENT_CACHE_TTL=600      # 會話快取 TTL (秒)
```

---

## 🧪 端到端流程範例

### 案例 1: 分類層級搜尋

```
用戶輸入：「我要買食品類的調味油，特別是橄欖油」

Step 1: 意圖分析 (llm_analyze_query)
  ↓ LLM 識別
  {
    "required_terms": ["調味油"],
    "category_hierarchy": {
      "L1": "食品",
      "L2": "調味油",
      "L3": "橄欖油"
    },
    "hierarchy_confidence": {"L1": 0.95, "L2": 0.92, "L3": 0.88}
  }

Step 2: 對話意圖分類
  ↓ 結果：product_search (購買意圖)

Step 3: 搜尋準備
  ↓ 提取關鍵詞、預算、過濾器

Step 4: 多層商品搜尋
  ├─ 分類層級搜尋
  │  ├─ 過濾 L1 = "食品" → 514 件商品
  │  ├─ 過濾 L2 = "調味油" → 85 件商品
  │  └─ 過濾 L3 = "橄欖油" → 12 件商品 ✅
  │
  └─ 返回精確匹配的 12 件橄欖油商品

Step 5: LLM 回覆生成
  ↓ LLM 組織回覆 + 隱藏 JSON

Step 6: 會話保存 & 返回
  ↓ ChatResp JSON

前端顯示：
  - 自然語言回覆：「根據您的需求，我為您找到了 12 款食品類調味油，特別推薦以下幾款高品質橄欖油...」
  - 商品列表：展示前 3-5 件商品
  - 建議操作：「需要我顯示詳細商品資訊與圖片嗎？」
```

### 案例 2: 資訊諮詢

```
用戶輸入：「椰子油對健康有什麼幫助？」

Step 1: 意圖分析
  ↓ LLM 識別健康相關模式

Step 2: 對話意圖分類
  ↓ 結果：information (資訊諮詢)

Step 3: 資訊回答流程
  ├─ 檢測意圖子類型：health_info
  ├─ 構建資訊專用系統提示詞
  ├─ 調用 _call_chat_for_information()
  └─ LLM 生成科學、實用的健康資訊

Step 4: 自然引導
  ├─ 資訊回覆長度 < 180 字
  └─ 附加引導語：「想進一步了解相關的健康產品嗎？我可以為您推薦。」

前端顯示：
  - 資訊回覆：詳細解釋椰子油的健康效果
  - 自然引導：邀請進一步推薦商品
  - 不直接顯示商品清單
```

### 案例 3: 概覽查詢

```
用戶輸入：「你們店裡賣什麼？」

Step 1: 快速意圖檢測
  ↓ 匹配 GENERAL_OVERVIEW_TRIGGERS

Step 2: 直接返回概覽回覆
  ├─ 調用 _get_top_l1_list()
  ├─ 從 /api/catalog/scope 讀取 Top-K L1
  └─ 快速返回，不涉及 LLM

前端顯示：
  - 回覆：「我們目前可銷售的大分類包含：常溫食品、保健飲品、生活用品...還有 5 類可在左側分類樹查看。想先看看哪一類？」
  - 分類按鈕：Top-8 L1 分類供快速點擊
```

---

## 🔧 常見調試點

### 1. LLM 未呼叫 (卡在 mock 模式)

**檢查清單：**
```bash
# 檢查 API key 和模型
echo $OPENAI_API_KEY | head -c 10
echo $CHAT_OPENAI_MODEL

# 檢查環境變數開關
echo $CHAT_USE_LLM_INTENT
echo $CHAT_USE_LLM_EXPAND

# 檢查 _get_client() 能否初始化
# llm_service.py 行 78-96
```

### 2. 商品搜尋結果為空

**檢查清單：**
```bash
# 1. 驗證 CSV 資料
wc -l data/VIEW_GOODS_enhanced.csv  # 應 > 900 行

# 2. 驗證分類欄位
grep -o "CateName_L1\|大分類名稱" data/VIEW_GOODS_enhanced.csv | wc -l

# 3. 運行搜尋測試
python3 -c "
from backend.goods_search_service import load_data, search_products
df = load_data('data/VIEW_GOODS_enhanced.csv')
results, _ = search_products(df, '椰子油', topn=5)
print(f'Found: {len(results or [])} products')
"
```

### 3. 分類層級識別失敗

**檢查清單：**
```bash
# 1. 驗證 LLM 分析輸出
# llm_service.py 行 1778-1785：檢查 JSON 解析是否正常

# 2. 檢查分類層級同義詞快取
# llm_service.py 行 92-140：_extract_category_synonyms()

# 3. 運行層級搜尋測試
python3 -c "
from backend.llm_service import _search_by_category_hierarchy, _get_chat_df
df = _get_chat_df()
hierarchy = {'L1': '食品', 'L2': '調味油', 'L3': '橄欖油'}
results = _search_by_category_hierarchy(df, hierarchy, topn=5)
print(f'Found: {len(results)} products')
for r in results[:2]:
    print(f\"  - {r.get('Name')}\")
"
```

---

## 📚 相關文檔

- **欄位標準化指南**：`欄位使用記錄_中英文對照_標準化指南.md`
- **開發原則**：`後續開發原則_檢查清單.md`
- **快速參考**：`欄位_快速參考表.md`

