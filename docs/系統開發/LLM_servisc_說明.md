# LLM 服務模組說明（llm_service.py）

> 版本：v1.0（文件） | 來源檔：backend/llm_service.py | 最後更新：依原始碼 2025-11-05

本文件說明「SEARCH_Goods 系統 - 大語言模型服務」模組的用途、功能、依賴、配置與回傳格式，協助產品、研發與運維快速理解與維護。

---

## 1. 模組摘要
- 定位：封裝 OpenAI Chat Completions（GPT）以支援商品搜尋與對話客服情境。
- 主要職責：
  - 查詢擴展（expand）、意圖分析（intent）、短摘要、文案生成（promo/marketing）
  - 對話回覆入口（chat_reply）：依意圖自動切換「資訊諮詢/商品搜尋/房產介紹/活動規劃」等流程
  - 商品對齊、排序、結構化輸出與內容格式化（自動偵測商品並轉化標準區塊）
- 關鍵特性：
  - 環境變數控制功能開關（Search/Chat 可分流配置）
  - OpenAI 客戶端快取，支援 API Key 動態切換
  - 無 API Key 時自動降級為「Mock 回覆」確保功能可用
  - 以 CSV 產品資料（VIEW_GOODS_enhanced.csv）為資料源進行搜尋、比對與輸出

---

## 2. 對外主要函式與用途
- llm_expand_query(query: str, use_search_config=True) -> str
  - 說明：使用 LLM 生成同義與相關詞組（逗號分隔）。開關由 SEARCH_USE_LLM_EXPAND/CHAT_USE_LLM_EXPAND 控制。
  - 失效處理：關閉或無 API Key 則回傳原查詢。

- llm_analyze_query(query: str, use_search_config=True) -> Dict
  - 說明：分析查詢意圖與分類層級，輸出 JSON：
    - required_terms[], category_terms[], excluded_terms[]
    - category_hierarchy: {L1, L2, L3}
    - hierarchy_confidence: {L1, L2, L3}
  - 失效處理：關閉或無 API Key 則回傳 {}。

- llm_shorten_20(text: str, use_search_config=True) -> str
  - 說明：將文本濃縮至 <= 20 字（繁中）。關閉或無 API Key 時回傳截斷文字。

- llm_generate_promo(name, raw_description, extra=None, use_search_config=True) -> str
  - 說明：產生社群短文案（2 句內、無 Emoji/Tag）。關閉或無 API Key 回傳截斷原描述。

- llm_rerank_products(user_query, expanded_query, candidates, topn=10, use_search_config=True) -> List[Dict]
  - 說明：以 LLM 對候選商品語義重排。關閉或無 API Key 時回傳原序。

- chat_reply(user_message, history, catalog, topn=8) -> Dict
  - 說明：對話主入口。根據意圖自動走不同分支並整合 CSV 搜尋結果，輸出：
    - reply: 回覆文字（可能已附商品推薦區塊）
    - action: {type: none | switch_to_search, ...}
    - intent: information | product_search | real_estate | event_food_planning | general | confirmation_needed
    - alignment: 對齊資訊（intent=product_align|product_confirm, items[]）
    - structured_filters: 結構化篩選（類別/價格等）
    - structured_payload / structured_products: 商品清單（標準結構）
    - meta/status: 額外狀態（如 OOS、健康/用法子態）

- format_product_recommendations(text: str) -> {formatted_text, products[], product_count}
  - 說明：從文字中偵測商品編號/名稱/連結，查表補齊資料並在回覆末尾產生「商品推薦區塊」。

- generate_enhanced_marketing_description(item: Dict) -> str
  - 說明：行銷描述生成（LLM → 智能模板 → 基礎模板）三級降級策略。

---

## 3. chat_reply 主要流程（簡版）
1) 前置檢測
   - 房產關鍵詞 → 切換房產專員提示詞與過濾器，直接生成回覆
   - 上下文產品詢問（高/中置信度）→ 直接搜尋或先詢問確認
2) 一般意圖判斷
   - company_info（公司資訊）→ 視為 information 流程處理
   - information（健康/用法/比較/推薦等）→ 呼叫 LLM 回答，並嘗試附上結構化商品備選
   - product_search（購買/價格/下單等）→ 搜尋 CSV（分類層級 + 嚴格/模糊對齊）
3) OOS（超出販售範圍）守門
   - 3C 等關鍵詞或分類白名單未命中 → 返回販售範圍導引（不捏造）
4) 產出對齊與引導
   - 找到商品 → alignment.intent=product_align + items[]，以「需要我顯示詳細介紹與圖片嗎？」引導
   - 使用者明確回覆「要/看詳細」→ action=switch_to_search
5) 商品格式化
   - 自動偵測回覆文字中的商品，補齊標準商品區塊與 structured_products

---

## 4. 產品搜尋與對齊邏輯（CSV）
- 資料載入：goods_search_service.load_data(DEFAULT_DATA_PATH)
- 搜尋路徑：
  1) 分類層級搜尋：llm_analyze_query → category_hierarchy → search_products_with_hierarchy（優先）或 _search_by_category_hierarchy（降級）
  2) 模糊搜尋：search_products + 結構化過濾（類別/必含/排除/價格）
  3) 嚴格補齊：search_ext_goods_1024001.search_products_strict（可選）
  4) 食品守護：非食品查詢時過濾食品類商品
- 對齊輸出：_build_alignment_items() 限 8 筆，用於前端確認切換到詳情清單
- 結構化輸出：_build_structured_payload(items) 產出標準欄位（商品編號/名稱/價格/特價/連結/圖片）

---

## 5. 依賴與整合
- 外部 SDK：openai (Chat Completions)
- 第三方/服務：無（資料來源為本地 CSV）
- 專案內部依賴：
  - goods_search_service（資料載入、搜尋、分類索引）
  - field_utils.FieldAccessor（欄位存取統一）
  - services.categories_service.get_category_terms（分類白名單）
  - planner.event_food_planner.parse_event_context（活動語境解析）
  - utils.logging_utils.get_logger（統一日誌）
  - utils.simple_extract.extract_budget_and_cats（預算抽取，可選）
  - search_ext_goods_1024001.search_products_strict（嚴格搜尋，可選）

---

## 6. 環境變數（功能開關與模型）
- 通用
  - OPENAI_API_KEY：OpenAI 金鑰（缺省則一律使用 Mock）
  - OPENAI_MODEL：預設模型（預設 gpt-4o-mini）
- 搜尋（SEARCH_*，預設較保守）
  - SEARCH_USE_LLM_EXPAND / USE_LLM_EXPAND
  - SEARCH_USE_LLM_SHORTDESC / USE_LLM_SHORTDESC
  - SEARCH_USE_LLM_RERANK / USE_LLM_RERANK
  - SEARCH_USE_LLM_INTENT / USE_LLM_INTENT
  - SEARCH_USE_LLM_PROMO / USE_LLM_PROMO
  - SEARCH_OPENAI_MODEL / OPENAI_MODEL
- 聊天（CHAT_*，預設較積極）
  - CHAT_USE_LLM_EXPAND / USE_LLM_EXPAND（預設 True）
  - CHAT_USE_LLM_SHORTDESC / USE_LLM_SHORTDESC（預設 True）
  - CHAT_USE_LLM_RERANK / USE_LLM_RERANK
  - CHAT_USE_LLM_INTENT / USE_LLM_INTENT（預設 True）
  - CHAT_USE_LLM_PROMO / USE_LLM_PROMO（預設 True）
  - CHAT_OPENAI_MODEL / CHAT_MODEL / OPENAI_MODEL
- 行銷描述
  - USE_LLM_MARKETING（預設 False）
  - MARKETING_MAX_LENGTH（預設 25）
  - MARKETING_FALLBACK_MODE（smart|basic，預設 smart）
- 其他
  - USE_CHAT_MODE（True|False，關閉時 chat_reply 直接回覆未啟用）

開關解析：字串 '1'/'true'/'yes' → True

---

## 7. 回傳格式與前端契約（重點）
- chat_reply 基本回傳
```json
{
  "reply": "文字回覆（可能含商品推薦區塊）",
  "action": {"type": "none" | "switch_to_search", "items": [...], "query": "..."},
  "intent": "information|product_search|real_estate|event_food_planning|general|confirmation_needed",
  "alignment": {"intent": "product_align|product_confirm", "items": [{"id":"","name":""}], "need_confirm_show_details": true, "reason": "..."},
  "structured_filters": {"category_filter":"...","price_filter":{"min_price":0,"max_price":0},"category_hierarchy":{"L1":"","L2":"","L3":""}},
  "structured_payload": {"summary":"...","items":[{"商品編號":"","商品名稱":"","商品價格":"","商品特價":"","商品購物網址":"","商品圖片網址":""}]},
  "structured_products": [{"product_id":"","name":"","description":"","price":0,"special_price":0,"url":"","image_url":""}],
  "meta": {"oos_category": true, "oos_reason":"keyword_block|whitelist_miss"},
  "status": "🩺 專業健康諮詢中 | 📋 使用指導分析中 | ..."
}
```
- alignment 與 switch_to_search 的互動：
  - 對齊時僅詢問是否要顯示詳情；收到「要/OK」等確認詞 → 觸發 switch_to_search（攜帶 items 或 query）

---

## 8. 降級與錯誤處理
- OpenAI 客戶端快取與金鑰切換
  - _get_client() 會快取 client；偵測 API Key 變更時重建
- 無金鑰/失敗降級
  - 所有 LLM 功能均安全降級：回傳空值/原文/模板，chat_reply 走 Mock 回覆
- OOS 守門與白名單
  - 若查詢超出販售範圍（3C 等）或未命中分類白名單，回覆販售範圍與引導
- 例外處理
  - 關鍵路徑皆以 try/except 包覆並記錄日誌，不阻斷主流程

---

## 9. 日誌與監控
- 統一使用 utils.logging_utils.get_logger
- 關鍵節點（意圖分析、分類層級、回覆生成、嚴格搜尋、格式化檢測）均有 info/debug 記錄
- 建議監控：
  - LLM 調用成功率/延遲、降級比例
  - oos_suspected 命中率、product_align 產出率、switch_to_search 轉換率

---

## 10. 測試建議
- 單元測試
  - 無金鑰環境：llm_* 函式降級行為、chat_reply Mock 路徑
  - 意圖判斷：information/health/usage/comparison/recommendation 分支
  - 分類層級：llm_analyze_query JSON 結構修復
  - 產品搜尋：分類層級 → 嚴格搜尋 → 模糊搜尋之合併與去重
- 端對端
  - 對齊 → 確認詞 → switch_to_search 行為
  - 商品格式化：format_product_recommendations 對各類文本的解析
  - OOS 與白名單：正反樣例

---

## 11. 安全與合規
- 不回傳 API Key（僅日誌遮罩顯示前 8/後 4 碼）
- 不臆測不存在商品；OOS 場景提供販售範圍導引
- 健康與功效資訊：使用中立、基於常識之陳述，避免醫療宣稱

---

## 12. 常見問題（FAQ）
- Q：為何同一功能有 SEARCH_* 與 CHAT_* 兩組設定？
  - A：搜尋與對話場景的預設不同。搜尋較保守（多數關閉），聊天較積極（多數開啟）。
- Q：沒有 OPENAI_API_KEY 能跑嗎？
  - A：可以，會以 Mock/模板策略降級，確保頁面可運作。
- Q：CSV 欄位不一致怎麼辦？
  - A：統一使用 field_utils.FieldAccessor 取得欄位，對齊多別名。
- Q：如何提升精度？
  - A：補齊分類白名單、擴充 IMPORTANT_CATEGORY_EXAMPLES、為熱門詞加規則、配置 RERANK。

---

## 13. 版本與變更
- 原始碼標註：2025-11-05 由 Copilot (Claude 3.5 Sonnet) 生成與整理
- 本文件：首次產生 v1.0（對應當前原始碼）
