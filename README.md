# SEARCH_Goods

輕量商品查詢客服系統 MVP 範例ＡAＢ。

快速啟動參考請見 `backend/README.md`。

Docker 支援：

```bash
docker build -t search_goods .
docker run -p 8000:8000 -e DATA_PATH=/app/data/VIEW_GOODS_enhanced.csv search_goods
```

## GitHub Actions 自動部署

當程式推送到 `main` 分支時，`.github/workflows/deploy.yml` 會先執行後端測試，通過後會同時觸發 Render 與 Netlify 重新部署。請在 GitHub 專案的 Secrets 中設定下列項目：

- `RENDER_SERVICE_ID`：Render 後端服務的 ID。
- `RENDER_API_KEY`：Render API key，需具備部署權限。
- `NETLIFY_SITE_ID`：Netlify 前端站台的 Site ID。
- `NETLIFY_AUTH_TOKEN`：Netlify Personal access token。

若任一服務尚未設定，對應的觸發步驟會被自動略過。

使用 GitHub Actions CI：專案已包含 `.github/workflows/ci.yml`，會在 push/PR 時跑 pytest（後端）。

管理 API（可選）
-----------------

如果你啟用了 `ADMIN_TOKEN`（環境變數），後端會提供兩個管理端點：上傳 CSV（`/api/admin/upload-csv`）與清除快取（`/api/admin/clear-cache`）。使用範例如下：

```bash
# 上傳 CSV（將本機檔案上傳並覆寫後端資料檔）
curl -X POST -H "x-admin-token: $ADMIN_TOKEN" -F "file=@/path/to/new_VIEW_GOODS_enhanced.csv" http://localhost:8000/api/admin/upload-csv

# 清除快取（讓下一次查詢重新載入 CSV）
curl -X POST -H "x-admin-token: $ADMIN_TOKEN" http://localhost:8000/api/admin/clear-cache
```

安全提醒：務必把 `ADMIN_TOKEN` 設為強隨機字串，並僅在內部網路或受保護的環境中使用這些端點。

## Local development with docker-compose (optional)

If you prefer a reproducible local environment, a `docker-compose.dev.yml` is included. It launches the backend with a bind mount so code changes are picked up immediately and `ADMIN_TOKEN` can be provided via `backend/.env.dev`.

Example (from project root):

```bash
# build and start the backend service
docker compose -f docker-compose.dev.yml up --build

# or run in detached mode
docker compose -f docker-compose.dev.yml up -d --build
```

The `backend/.env.dev` file contains a sample `ADMIN_TOKEN` (default `testtoken123`).

Testing admin upload with curl (when service is running):

```bash
ADMIN_TOKEN=testtoken123 \
	curl -v -X POST \
		-H "x-admin-token: $ADMIN_TOKEN" \
		-F "file=@./data/VIEW_GOODS_enhanced.csv" \
		http://localhost:8000/api/admin/upload-csv
```


# SEARCH_Goods
# SEARCH_Goods
\n
