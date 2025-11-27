# 聊天流程優化修改任務清單

## 背景
為了讓所有購物情境都能先透過 LLM 解析並提供個人化建議，同時保留後端補強能力，需要將現有「生日派對」專屬 fallback 流程重構為通用的情境規劃器，並回應以下需求：

- 情境識別準確度
- 對話長度控制
- 商品資料庫整合
- 用戶急迫性處理

## 修改任務概覽
1. **LLM 主導流程調整**
   - 更新 `chat_handler`：移除目前的 fallback 優先邏輯，改為「先聊再補」。
   - 導入信心評估：依 `alignment`、`structured_filters`、LLM meta 判斷是否需要補強。
   - 設計輸出結構：標記 `fallback_used`、`detected_categories` 等欄位，保持前端兼容。

2. **通用情境規劃器（Planner）**
   - 從 `fallback/multi_category_party.py` 提取共用元件至新模組（暫定 `planner/category_planner.py`）。
   - `detect_intent(text)`：辨識品類、預算、急迫性、信心值。
   - `build_plan(intent, catalog)`：支援任意品類組合的預算分配與商品挑選；品類不足時自動替代。
   - `compose_plan_reply(plan)`：統一輸出 `structured_payload` 與建議文字，供 chat handler 合併。

3. **LLM Prompt 與資料流整合**
   - 更新 `chat_reply` prompt，要求模型在辨識情境時回傳品類/預算／急迫性旗標。
   - 若 LLM 回報 `needs_planner=True` 或無商品，即啟用 planner 產生補充內容。
   - 可選：提供快速模式指示（看到急迫性時優先返回精簡清單）。

4. **商品資料庫覆蓋與欄位確保**
   - 檢查/擴充 FieldAccessor 映射，確保所有品類資料一致。
   - 為 planner 建立品類→關鍵字→欄位對應表，方便之後新增品類。
   - 增加離線覆蓋檢測腳本，定期檢查每品類可推薦商品數量。

5. **對話策略 & 急迫性處理**
   - 根據情境設定最大追問輪數與最終總結策略。
   - 急迫性旗標為真時：減少追問，優先輸出核心清單，並附上「是否需要更多建議」選項。
   - 追蹤對話長度統計，超過上限時提示用戶可直接查看推薦。

6. **測試與觀察**
   - 單元測試：`detect_intent` 多情境案例、`build_plan` 預算分配、`chat_handler` 在有/無 LLM alignment 時的輸出。
   - 整合測試：生日派對、廚房用品、健康保健等多情境流程。
   - 日誌顯示：`intent_confidence`、`fallback_used`、`planner_latency` 以利後續監控。

## 待確認事項
- Planner 模組命名與最終放置位置。
- LLM prompt 是否需同步更新（與 Prompt 團隊或模型設定協調）。
- 快速模式切換是否需前端配合 UI 調整。

確認以上清單後，再依序執行實作與測試。

---

## 實作評估紀錄（首次迭代）

- 2025-10-30  
  - **新增** `planner/category_planner.py` 作為獨立模組，未移除或修改原有 `fallback/multi_category_party.py`。  
  - **調整** `chat_handler`：取消直接進入 fallback 的邏輯，改為先透過 LLM→Planner→Fallback 的層級判斷，並在 `meta` 中記錄 `planner_used`/`planner_notes`。  
  - **風險評估**：  
    - 原 fallback 僅在 `party_context` 為真時觸發，其他情境仍沿用 LLM 與搜尋流程。  
    - Planner 僅於 LLM 無結果且偵測信心達門檻時執行，且結果透過 `meta` 呈現以利觀察。  
  - **測試**：新增 `backend/tests/test_category_planner.py` 覆蓋情境偵測與預算分配；待完整跑 CI/pytest 確認無回歸。

---

## 行銷顧問模式擴充任務（2025-10-30 規劃）

| 任務代碼 | 任務名稱 | 內容摘要 | 主要模組 |
|----------|-----------|-----------|-----------|
| **T1** | Intent 擴充與分類優化 | 新增 `event_food_planning`（活動情境）、保留 `shopping_recommendation`，更新 LLM Prompt 與解析流程 | `llm_service.py`, Prompt 設定 |
| **T2** | 對話模式切換器 | 在 `chat_handler` 中明確分流至 `marketing_consultant` / `shopping_recommender` 模組 | `chat_router_goods_action.py`, `backend/modes/*` |
| **T3** | 活動顧問 Planner | `planner/event_food_planner.py`：依活動資訊（場合、人數、預算、受眾）選取商品組合並估算成本、撰寫亮點 | `planner/` |
| **T4** | 資訊蒐集流程 | 設計追問模板與狀態紀錄，資訊不足時回傳顧問式提問而非商品清單 | `chat_router_goods_action.py`, `modes/marketing_consultant.py` |
| **T5** | 商品推薦模式強化 | 既有購物流程整合至 `shopping_recommender`，LLM→Query Spec→DB→行銷包裝，保留 Planner fallback | `modes/shopping_recommender.py`, `planner/` |
| **T6** | 回覆模板與 CTA | 建立統一顧問語氣（活動描述、slogan、估算提醒、CTA），並加測試避免不當宣稱 | Prompt 設定、`marketing_consultant`、測試 |
| **T7** | 前端呈現優化 | 支援對話追問與推薦方案兩種回覆格式，商品卡顯示圖片、價格、亮點、購物連結 | `frontend/index.html` 及 JS |
| **T8** | 測試與 QA | 單元／整合測試：意圖判斷、Planner 選品、多輪對話追問→推薦、CTA 文案檢驗 | `backend/tests/*` |
| **T9** | 設定與監控 | 固化 `.env`/Render 環境變數（如 `USE_CHAT_MODE=true`），記錄 `mode`/`detected_intent`/`planner_used` 以利後續分析 | `app.py`, 部署設定 |

## 上下文重建指令模板（重返專案背景用）

````text
請載入以下專案上下文（SEARCH_Goods AI 導購模組），後續所有回答都以此為基礎：

[專案定位]
- 平台：SEARCH_Goods，結合 AI 導購與商品搜尋的電商系統。
- 目標：讓所有購物／活動情境都先經過 LLM 對話解析，再由後端推薦商品或情境組合，並以顧問式口吻回覆。
- 架構：FastAPI 後端 + LLM（OpenAI GPT-4o-mini） + 商品資料庫 (VIEW_GOODS_enhanced.csv) + 前端聊天介面/商品卡。

[主要模組]
1. `chat_router_goods_action.py`
   - 判斷意圖（event_food_planning / shopping_recommendation / information…）
   - 呼叫 `modes/marketing_consultant.py` 或 `modes/shopping_recommender.py`
   - 視情況啟用 planner / fallback，並保持 `switch_to_search` 行為

2. `modes/marketing_consultant.py`
   - 行銷顧問模式：活動需求蒐集→追問→呼叫活動 planner→產出顧問式推薦（摘要、亮點、CTA）
   - 資訊不足時回傳追問模板

3. `modes/shopping_recommender.py`
   - 商品推薦模式：LLM 抽取查詢條件 → 後端商品搜尋 → 行銷包裝
   - Planner 僅在 LLM 無商品時補強，保留 `switch_to_search`

4. `planner/event_food_planner.py`
   - 依活動類型、人數、預算、受眾挑選商品組合，估算總金額與亮點

[Intent 擴充]
- `event_food_planning` 觸發行銷顧問模式
- `product_search` / `shopping_recommendation` 走商品導購流程
- `information` 可繼續追問或提供資訊建議

[前端呈現]
- 聊天介面支援顧問追問（純文字）與推薦方案（說明 + 商品卡）
- 商品卡顯示圖片、特價、亮點、購物連結

[測試覆蓋]
- `backend/tests/test_event_intent.py`：驗證新意圖
- `backend/tests/test_event_planner.py`：檢查活動 planner 選品與估算
- 既有測試 `test_category_planner.py`、`test_product_id_search.py`、`test_price_filtering.py` 必須持續通過

[環境設定]
- `.env` / Render 環境需設定 `USE_CHAT_MODE=true`
- 回傳的 `meta` 記錄 `mode`、`planner_used`、`detected_intent` 以利後續分析

---

[請將上述內容視為專案上下文，後續所有問題、程式調整、測試或文件輸出皆以此為準。遇到多輪追問時，請維持 AI 行銷顧問的角色與流程。]
````
