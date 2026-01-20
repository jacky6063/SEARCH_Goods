# 對話流程比較：我要買運動用品 vs 我要購買女用包包

## 說明
此文件整理使用者在「對話區按送出」後的實際後端流程，並比較兩個查詢的共用步驟與分歧點。
流程依據 `backend/chat_router_goods_action.py` 的實作整理。

## 共用流程與分歧點比較表

| 步驟 | 共用流程 | 我要買運動用品 | 我要購買女用包包 |
|---|---|---|---|
| 1 | 前端送出 `/api/chat` | 共用 | 共用 |
| 2 | `chat_handler()` 接收並記錄 log | 共用 | 共用 |
| 3 | `ConversationOrchestrator` → `ShoppingSupportHandler` | 共用 | 共用 |
| 4 | 進入 `_legacy_chat_flow()` | 共用 | 共用 |
| 5 | 熱門分類點擊 `_extract_hot_category_click` | 通常不觸發 | 通常不觸發 |
| 6 | 商品編號偵測 `_looks_like_product_id_query` | 通常為否 | 通常為否 |
| 7 | 負面查詢判斷 `is_negative_query` | 通常為否 | 通常為否 |
| 8 | 直接解析完整 L1/L2/L3 `_extract_selected_levels_from_text` | 可能否 | 可能否 |
| 9 | 類目導覽/總覽 `_try_category_navigation_reply` / `_try_overview_scope_reply` | 視問句是否屬於導覽 | 視問句是否屬於導覽 |
| 10 | LLM 意圖分析 / 澄清 `llm_analyze_query` / `llm_clarify_or_confirm` | 可能要求澄清 | 可能要求澄清 |
| 11 | `planner_detect_intent` | 共用 | 共用 |
| 12 | LLM 主流程 `chat_reply()` | 共用 | 共用 |
| 13 | 依 LLM `intent` 分支 | 多半走 `shopping` | 多半走 `shopping`（更容易帶性別/包類線索） |
| 14 | `prepare_shopping_response()` 產出商品建議 | 共用 | 共用 |
| 15 | `catalog_service.get_items_by_ids()` 對齊與快取 | 共用 | 共用 |
| 16 | 回傳 `ChatResponse` 給前端 | 共用 | 共用 |

## 各步驟用途說明（中文）

1) 前端送出 `/api/chat`  
   - 用途：把使用者在對話區輸入的文字傳給後端處理。

2) `chat_handler()` 接收並記錄 log  
   - 用途：統一入口、記錄對話與追蹤資訊，方便除錯與紀錄。

3) `ConversationOrchestrator` → `ShoppingSupportHandler`  
   - 用途：依意圖決定交給哪個對話處理器，這裡預設是商品購買支援。

4) 進入 `_legacy_chat_flow()`  
   - 用途：主要對話邏輯入口，實際商品搜尋與回覆分支都在此處。

5) 熱門分類點擊 `_extract_hot_category_click`  
   - 用途：判斷是否是前端點擊熱門分類的操作，若是直接走分類查詢快路徑。

6) 商品編號偵測 `_looks_like_product_id_query`  
   - 用途：若輸入像商品編號，優先用精準查詢避免誤搜。

7) 負面查詢判斷 `is_negative_query`  
   - 用途：若是非販售範圍的類別，直接回覆引導語，不進行搜尋。

8) 直接解析完整 L1/L2/L3 `_extract_selected_levels_from_text`  
   - 用途：若文字中已包含完整分類階層，直接用分類索引加速查詢。

9) 類目導覽/總覽 `_try_category_navigation_reply` / `_try_overview_scope_reply`  
   - 用途：處理「你們賣什麼」類的導覽問題，回覆分類清單而不是進入商品推薦。

10) LLM 意圖分析 / 澄清 `llm_analyze_query` / `llm_clarify_or_confirm`  
   - 用途：判斷需求是否足夠；不足則先提澄清問題避免錯誤推薦。

11) `planner_detect_intent`  
   - 用途：補充意圖判斷與結構化需求（例如預算/類別），供後續推薦使用。

12) LLM 主流程 `chat_reply()`  
   - 用途：產生主要回覆內容，並可能附帶商品候選或條件資訊。

13) 依 LLM `intent` 分支  
   - 用途：區分資訊型、概覽型、購買型等流程，決定是否進入商品推薦。

14) `prepare_shopping_response()` 產出商品建議  
   - 用途：整理商品清單、生成回覆結構與可顯示商品卡的資料。

15) `catalog_service.get_items_by_ids()` 對齊與快取  
   - 用途：依商品 ID 取得完整商品資料並快取，支援後續對話與顯示。

16) 回傳 `ChatResponse` 給前端  
   - 用途：把回覆文字、商品卡資料、meta 資訊完整回傳給前端顯示。

## 流程圖版（含節點資料與差異點標記）

> 註：節點中的 `data:` 表示該步驟常見產出資料。  
> 差異點以 `DIFF` 標註。

### 路徑圖 A：我要買運動用品

```mermaid
flowchart TD
  A[1. /api/chat<br/>data: {message, history, session_id}] --> B[2. chat_handler<br/>data: log_id, supabase_session_id]
  B --> C[3. Orchestrator->ShoppingSupportHandler<br/>data: intent=shopping_support]
  C --> D[4. _legacy_chat_flow<br/>data: user_text, history]
  D --> E[5. 熱門分類點擊判斷<br/>data: hot_ctx=null]
  E --> F[6. 商品編號偵測<br/>data: product_id_query=false]
  F --> G[7. 負面查詢判斷<br/>data: is_negative=false]
  G --> H[8. L1/L2/L3 完整解析<br/>data: selected_full={} ]
  H --> I[9. 類目導覽/總覽<br/>data: nav_early=null, overview_early=null]
  I --> J[10. LLM 意圖分析/澄清<br/>data: analysis={}, clarification=ok]
  J --> K[11. planner_detect_intent<br/>data: planner_intent]
  K --> L[12. chat_reply()<br/>data: llm_result.intent=shopping, structured_filters(較少)]
  L --> M[13. intent 分支<br/>data: shopping]
  M --> N[14. prepare_shopping_response<br/>data: suggestion_ids, structured_products]
  N --> O[15. get_items_by_ids + cache<br/>data: align_rows, structured_summary]
  O --> P[16. ChatResponse 回傳<br/>data: reply, items, meta]
  L --> X[DIFF: 條件/分類較泛<br/>data: structured_filters 可能較少]
```

### 路徑圖 B：我要購買女用包包

```mermaid
flowchart TD
  A2[1. /api/chat<br/>data: {message, history, session_id}] --> B2[2. chat_handler<br/>data: log_id, supabase_session_id]
  B2 --> C2[3. Orchestrator->ShoppingSupportHandler<br/>data: intent=shopping_support]
  C2 --> D2[4. _legacy_chat_flow<br/>data: user_text, history]
  D2 --> E2[5. 熱門分類點擊判斷<br/>data: hot_ctx=null]
  E2 --> F2[6. 商品編號偵測<br/>data: product_id_query=false]
  F2 --> G2[7. 負面查詢判斷<br/>data: is_negative=false]
  G2 --> H2[8. L1/L2/L3 完整解析<br/>data: selected_full={} 或部分命中]
  H2 --> I2[9. 類目導覽/總覽<br/>data: nav_early=null, overview_early=null]
  I2 --> J2[10. LLM 意圖分析/澄清<br/>data: analysis(含女用/包類), clarification=ok]
  J2 --> K2[11. planner_detect_intent<br/>data: planner_intent]
  K2 --> L2[12. chat_reply()<br/>data: llm_result.intent=shopping, structured_filters(較多)]
  L2 --> M2[13. intent 分支<br/>data: shopping]
  M2 --> N2[14. prepare_shopping_response<br/>data: suggestion_ids, structured_products]
  N2 --> O2[15. get_items_by_ids + cache<br/>data: align_rows, structured_summary]
  O2 --> P2[16. ChatResponse 回傳<br/>data: reply, items, meta]
  L2 --> Y2[DIFF: 性別/品類更明確<br/>data: structured_filters 可能較完整]
```

## 差異點摘要

1) **LLM 意圖分析輸出**
   - 運動用品：多為大類詞彙，`structured_filters` 可能較少。
   - 女用包包：性別 + 品類線索較清楚，`structured_filters` 通常較完整。

2) **分類層級命中**
   - 運動用品：較難直接命中 L3。
   - 女用包包：較容易引導到包款相關分類。

## 主要分歧點說明

1) **分類/篩選資訊精準度**
   - 「運動用品」屬於大範圍詞彙，LLM 可能只給大類或模糊分類，後續商品候選較廣。
   - 「女用包包」通常會帶性別 + 類型線索，較容易產出更精準的 `structured_filters` 或分類候選。

2) **澄清機率**
   - 廣泛需求（例如「運動用品」）較容易觸發澄清問題。
   - 明確需求（例如「女用包包」）較容易直接進入商品建議流程。

## 對應程式位置
- `backend/chat_router_goods_action.py`（核心對話流程與分支）
- `backend/app.py`（對話 API `/api/chat` 入口）
