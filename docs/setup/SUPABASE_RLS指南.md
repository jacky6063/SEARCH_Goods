# Supabase RLS 與權限設定指南

本指南說明 `search_goods` 專案如何設定 Supabase Row Level Security（RLS）與金鑰，確保本地開發、CI、正式後端都能正確存取 `chat_sessions` 系列資料表。

---

## 1. 金鑰與環境變數約定

| 變數 | 用途 | 建議存放位置 |
| --- | --- | --- |
| `SUPABASE_URL` | Supabase 專案 URL | `.env`、CI secrets |
| `SUPABASE_KEY` | `anon` 公開金鑰，提供唯讀或受限寫入 | `.env`、前端／本地測試 |
| `SUPABASE_SERVICE_KEY` | `service_role` 金鑰，可繞過 RLS，僅供後端/CI | 只放在伺服器、CI Secret（不可進版本控制） |
| `DATABASE_URL` | 直接連線 PostgreSQL（可選） | 本地/ETL 用 |

> `.env.example` 已新增 `SUPABASE_SERVICE_KEY` 欄位，請在正式環境中填寫。

---

## 2. 啟用 RLS 與預設策略

針對四張聊天紀錄表（`chat_sessions`、`chat_messages`、`product_recommendations`、`session_events`）執行以下 SQL：

```sql
alter table chat_sessions enable row level security;
alter table chat_messages enable row level security;
alter table product_recommendations enable row level security;
alter table session_events enable row level security;
```

建立策略：

```sql
-- 允許 anon key 查詢所有聊天資料（僅供內部工具，若需限制可增加條件）
create policy "allow_read_for_anon"
on chat_sessions
for select
to anon
using (true);

create policy "allow_read_for_anon"
on chat_messages
for select
to anon
using (true);

-- 允許 service_role 進行任意操作
create policy "service_role_full_access"
on chat_sessions
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

create policy "service_role_full_access"
on chat_messages
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');
```

其餘兩張表以相同概念建立策略即可。若需限制 anon 寫入，請勿建立 insert/update/delete 策略，讓其自動被拒絕。

---

## 3. 實作建議

1. **後端程式**：預設使用 `SUPABASE_SERVICE_KEY`（透過 `get_supabase_client(prefer_service_role=True)`），避免 RLS 阻擋寫入。
2. **本地/工具**：使用 `SUPABASE_KEY` 即可閱讀資料；如需寫入，可在開發環境暫時設定 `SUPABASE_SERVICE_KEY`。
3. **CI/部署**：於 GitHub Actions / Docker secrets 注入 `SUPABASE_SERVICE_KEY`，並在部署腳本中執行 smoke test。

---

## 4. 驗證流程

1. 在 Supabase SQL Editor 執行 `select * from chat_sessions limit 1;` 確認服務角色可以讀取。
2. 將 `.env` 中的 `SUPABASE_SERVICE_KEY` 留空，再跑 `python3 scripts/supabase_db_test.py`（應可讀取但無法寫入）。
3. 填上 `SUPABASE_SERVICE_KEY`，執行日誌寫入測試（待 Logging SDK 完成）確認 RLS 生效。

如需更細緻的條件（例如限定同一 `company_code` 讀取），可再擴充 policy 條件。請將任何調整回填到本文件，維持團隊同步。***
