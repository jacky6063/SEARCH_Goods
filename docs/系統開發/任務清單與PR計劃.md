# 任務清單與 PR 分支計劃

目的
- 對齊系統設計：
  1) 先用聊天模式建立銷售範圍認知（L1/L2/L3）
  2) 非販售品類（OOS）要明確告知並主動推薦可售品類
  3) 僅在明確品類後再進入單品搜尋
- 確保 API 與前端行為一致，不在概覽/資訊階段直接跳商品模式

分支策略
- feature/chat-overview-guard：聊天概覽與 OOS 守門（本 PR）
- feature/search-hierarchy-support：搜尋支援 L1/L2/L3 加權（下一階段）
- feature/admin-diagnostics：管理端點診斷與上傳體驗增強（可選）

P0：聊天概覽與 OOS 守門（本 PR）
- LLM 服務（backend/llm_service.py）
  - 概覽（overview）回覆改為：intent="information"、display_mode="text_only"、action={type:"none"}，不含 suggestion_ids
  - 意圖偵測：加入概覽觸發詞（賣什麼/有哪些/商品分類/類別/分幾類/類型）→ information
  - OOS 守門：對 3C 類關鍵詞明確告知不販售，列出可售範圍（CHAT_CATEGORY_TOPICS），intent="information"，不切商品
- 聊天路由（backend/chat_router_goods_action.py）
  - 若 llm_result.intent 為 information 或含 overview，直接回傳聊天回覆，不產生 suggestion_ids / 不觸發 switch_to_search
- 購物導購（backend/modes/shopping_recommender.py）
  - 僅在 intent == product_search 且 suggestion_ids 存在時才切換到商品模式

驗收案例（P0）
- Q: 你們有賣什麼類型東西？
  - A: 留在聊天模式，顯示 L1/L2 清單，不切商品卡
- Q: 我要 3C 耳機
  - A: 回覆不販售該品類 + 列出可售範圍，留在聊天模式
- Q: 我要橄欖油
  - A: intent=product_search → 返回 suggestion_ids 或 action.switch_to_search，前端切商品模式

P1：搜尋支援 L1/L2/L3（下一 PR）
- goods_search_service：_row_text 與 score_row 納入 CateName_L1/2/3；新增 by_category 過濾；format_for_chat 帶回 CateName_L1/2/3 與 matched_levels/hierarchy_score
- llm_service：分類層級（category_hierarchy）傳入 _search_products_for_chat 優先過濾
- API 契約：/api/search、/api/chat 的 items 補齊 CateName_L1/2/3 與 matched_levels/hierarchy_score（為空也回鍵）

P2：管理端點診斷與上傳體驗（可選）
- 新增 /api/admin/info 顯示路徑與權限狀態（不含敏感值）
- 上傳前驗證 CSV 類型/大小/必要欄位，寫入失敗降級到 /tmp 並切換 catalog_service 資料來源

風險與回退
- 若 LLM intent 誤判：前端僅在 action.switch_to_search 或使用者確認詞才切商品模式
- 若 taxonomy 過長：只輸出 L1 全列舉 + 每 L1 前 K 個 L2，L3 延後

發佈與回報
- 合併 feature/chat-overview-guard 後，請以以下腳本驗收：
  - curl -X POST /api/chat '{"message":"你們有賣什麼類型東西？"}' → 留在聊天模式
  - curl -X POST /api/chat '{"message":"我要 3C 耳機"}' → OOS 回覆
  - curl -X POST /api/chat '{"message":"我要橄欖油"}' → 切到商品模式或返回 suggestion_ids
