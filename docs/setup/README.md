# Supabase 連線設定（Task SG-DB-001）

本文件說明如何在本地 VSCode 專案串接 Supabase 專案 `search_goods`，並驗證 `chat_sessions` / `chat_messages` 等資料表可被查詢。

---

## 1. 建立 `.env`

1. 複製根目錄的 `.env.example` 為 `.env`。
2. 將 `DATABASE_URL` 內的 `<YOUR_DB_PASSWORD>` 改成 Supabase 專案建立時的密碼。  
   其餘欄位保持預設（`SUPABASE_URL`、`SUPABASE_KEY`）。
3. 建議同時把 `.env` 加入個人開發環境的機密管理器，避免誤傳。

> ⚠️ 若未填寫密碼或輸入錯誤，測試腳本會直接失敗。

---

## 2. 安裝需要的套件

根據使用語言安裝以下依賴：

### Python（FastAPI 等）

```bash
pip install supabase python-dotenv psycopg2-binary
```

### Node.js / Next.js / React

```bash
npm install @supabase/supabase-js dotenv
```

---

## 3. 連線測試

### Python 測試

```bash
python scripts/supabase_db_test.py
```

腳本會載入 `.env`，並嘗試查詢 `chat_messages`。成功時終端會印出陣列（空陣列代表目前無資料，但連線成功）。

### Node.js 測試

```bash
node scripts/supabase_db_test.js
```

同樣會回傳 `chat_messages` 的查詢結果，任何錯誤都會在終端顯示。

---

## 4. 常見問題

- **Missing environment variable**：確認 `.env` 已建立且經由 `python-dotenv` / `dotenv` 載入。
- **RLS 導致 401/permission denied**：Supabase Dashboard 需允許 `anon key` 在相關表開啟讀取，或使用 `service_role` 金鑰。
- **連線逾時**：確保網路可連線到 `*.supabase.co`，必要時開啟代理例外。

> 進階權限策略與 `service_role` 使用方式，請參考 `docs/setup/SUPABASE_RLS指南.md`。

---

## 5. 驗收條件

- [ ] `.env` 設定完成（含正確的 `DATABASE_URL` 密碼）。
- [ ] `scripts/supabase_db_test.py` 成功查詢 `chat_messages`。
- [ ] `scripts/supabase_db_test.js` 成功查詢 `chat_messages`。
- [ ] 此文件（`docs/setup/README.md`）已更新並留存執行步驟與注意事項。

完成後請截圖終端結果並與 `.env` 樣板一併附在提交紀錄，方便 VSD 團隊交叉驗證。***

---

## 6. CI / Deploy Secrets

在 GitHub Actions、Render 等環境需要新增下列變數：

- `SUPABASE_URL`：專案 URL。
- `SUPABASE_KEY`：`anon` key，提供 smoke test 與讀取使用。
- `SUPABASE_SERVICE_KEY`：`service_role` key，僅限後端／CI（必要時才注入）。

CI workflow（`.github/workflows/ci.yml`）會在測試前執行 `python scripts/supabase_db_test.py`，僅在上述 secrets 具備時啟動。
