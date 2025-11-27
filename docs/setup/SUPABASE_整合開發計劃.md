# Supabase 整合開發計劃

本文件彙整目前 `search_goods` 專案的 Supabase 連線狀態、尚未完成的基礎設定，以及下一階段程式開發任務卡流程。完成此文件的事項後，即可進入正式的功能串接實作。

---

## 1. 基礎設定檢查結果

| 檢查項目 | 現況 | 待補動作 |
| --- | --- | --- |
| `.env` 與樣板 | `.env.example` 已提供必要欄位，並在根目錄產生 `.env` 供測試腳本使用。 | 將 `.env.example` 加入官方說明（完成），實際 `.env` 只留在本端即可。 |
| SDK / 連線測試 | `pip3 install supabase python-dotenv psycopg2-binary` 與 `npm install @supabase/supabase-js dotenv` 已安裝；`scripts/supabase_db_test.{py,js}` 皆能查詢 `chat_messages`。 | 保留終端畫面作為驗收附件（待貼圖），並在後續 README 中引用。 |
| RLS / 權限 | 尚未在專案 repo 中記錄 Supabase RLS 規則與 `service_role` 使用方式。 | 需要新增一份簡要設定說明，避免開發時因 RLS 阻擋寫入。 |
| Backend 介接 | 後端程式尚未建立「統一 Supabase client」或 `Logging SDK` 封裝，現有業務程式尚未呼叫 Supabase。 | 需安排開發任務：新增 `supabase_client.py` / Node 封裝，並在聊天模組寫入紀錄。 |
| CI / 部署整合 | GitHub Actions/Docker 尚未注入 Supabase 相關環境變數，CI 也未跑連線 smoke test。 | 待設定機密（Supabase URL/Key/DB），並新增 quick check step。 |
| 文件 & 手冊 | `docs/setup/README.md` 已說明環境建置，但缺少後續串接與驗收流程。 | 本文件即作為延伸說明，另外在主 README / 相關模組文件補充連結。 |

---

## 2. 程式開發任務卡流程（建議拆解）

1. **SG-DB-002：Supabase Client 封裝**
   - 建立 `backend/supabase_client.py`（或 Node 對應檔），集中管理 create_client、例外處理與重試。
   - 支援 `server_role` 金鑰注入（僅限後端安全環境），本地使用 `anon key`。
   - 撰寫簡易單元測試（mock Supabase 回傳）。

2. **SG-DB-003：Logging SDK 實作**
   - （已完成於 `backend/chat_logging.py`）提供 `start_session / append_message / log_recommendations / log_session_event` API。
   - 透過 `get_supabase_client(prefer_service_role=True)` 寫入 Supabase，並在異常時回傳 `ChatLoggingError`。
   - 模組在呼叫前應確保已建立 session，再串接 message 與推薦紀錄。

3. **SG-DB-004：模組串接與回填**
   - 由「商品查詢」、「公司資料」、「住宅維修客服」三個模組逐步導入 Logging SDK。
   - 在 LLM 回覆商品清單後呼叫 `log_recommendations`，其餘模組至少寫入 `chat_sessions/chat_messages`。
   - 加入 feature flag，便於分批上線。

4. **SG-DB-005：監控與驗收**
   - 在 Supabase Realtime / SQL Editor 建立基本視圖（如當日 session 數）。
   - GitHub Actions 新增 smoke test：使用 `scripts/supabase_db_test.py` 驗證 Supabase secrets（`SUPABASE_URL`、`SUPABASE_KEY`）。
   - 文件更新：主 README 加入「Supabase 日誌」章節，並附上用量監控方法。

---

## 3. 後續文件與驗收建議

- **文件調整**
  - 在 `docs/setup/README.md` 追加「下一步：串接 Logging SDK」段落，指向本文件與資料表設計文件以及 `backend/chat_logging.py`。
  - 對於 RLS / Service Role 使用，建議新增 `docs/setup/SUPABASE_RLS指南.md`。

- **驗收清單（建議加入 Task Card）**
  - [x] `supabase_client` 可重複供後端模組引用，並通過單元測試／驗證。
  - [ ] 三大模組皆可寫入 `chat_sessions` / `chat_messages`，商品模組額外寫入 `product_recommendations`。
  - [ ] GitHub Actions 上成功執行 Supabase 連線 smoke test。
  - [ ] 相關文件（本文件 + README + 模組說明）已更新，並附上終端測試截圖。

> 本文件可直接貼到 Jira/Notion 任務說明中，作為接續開發的依據。若後續流程或範圍有更新，請同步維護此文件與 Task Card。***
