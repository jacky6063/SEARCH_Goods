# backend

後端使用 FastAPI，讀取 `data/VIEW_GOODS_enhanced.csv` 並提供 `/api/search`。

注意：目前前端 UI 亦由本服務提供（掛載於網站根目錄 / ），Netlify 部署已停用；部署流程請參考 DEPLOYMENT_CHECKLIST.md。

快速啟動：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

生產環境（使用 gunicorn + uvicorn worker）：

```bash
# 建議在虛擬環境中安裝並使用提供的腳本啟動

Start with ADMIN_TOKEN helper
----------------------------

You can use the included helper to start the backend with an ADMIN_TOKEN:

```bash
source .venv/bin/activate
# pass the token as the first argument
./start_with_token.sh "my-strong-admin-token"
```

This will export ADMIN_TOKEN in the environment for the gunicorn process so admin
endpoints are enabled. After starting, test the upload endpoint with curl:

```bash
ADMIN_TOKEN=my-strong-admin-token \
	curl -v -X POST \
		-H "x-admin-token: $ADMIN_TOKEN" \
		-F "file=@/path/to/VIEW_GOODS_enhanced.csv" \
		http://localhost:8000/api/admin/upload-csv
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 安裝 gunicorn（若尚未安裝）
.venv/bin/pip install 'gunicorn==23.0.0'
# 使用專案提供的 run_gunicorn.sh 啟動（會使用 backend/gunicorn_conf.py）
./run_gunicorn.sh
```

如果你想直接用 gunicorn：

```bash
.venv/bin/gunicorn -c gunicorn_conf.py app:app
```

開發環境（docker-compose 範例）
-------------------------------

專案包含 `docker-compose.dev.yml`，可用於在本機以 bind-mount 模式開發，同時把 `ADMIN_TOKEN` 透過 `backend/.env.dev` 注入。

啟動示範（在專案根目錄）：

```bash
docker compose -f docker-compose.dev.yml up --build

# 背景啟動
docker compose -f docker-compose.dev.yml up -d --build
```

或直接使用專案內的 helper：

```bash
source .venv/bin/activate
# 在 backend 目錄執行並傳入 token
./start_with_token.sh "my-strong-admin-token"
```

測試上傳（當服務啟動後執行）

```bash
ADMIN_TOKEN=my-strong-admin-token \
	curl -v -X POST \
		-H "x-admin-token: $ADMIN_TOKEN" \
		-F "file=@/path/to/VIEW_GOODS_enhanced.csv" \
		http://localhost:8000/api/admin/upload-csv
```

Docker / 部署建議：
- 在容器中使用 gunicorn + uvicorn worker 執行，將靜態檔案與 API 一併提供（或使用 nginx 做反向代理以處理 TLS、gzip 與長連線）。
- 簡單 Dockerfile 建議：在基礎映像中安裝 dependencies、copy 專案、執行 `pip install -r requirements.txt` 並使用 `gunicorn -c gunicorn_conf.py app:app` 啟動。

執行測試（pytest）：

```bash
pip install pytest
pytest -q
```

Admin endpoints (上傳 CSV / 清除快取)
---------------------------------

後端提供兩個簡單的管理 API，用於原子性地更新 `VIEW_GOODS_enhanced.csv` 並清除後端的記憶體快取。這些端點預設會被停用，除非你在環境變數中設定 `ADMIN_TOKEN`。

安全提醒：請務必把 `ADMIN_TOKEN` 設為強隨機字串，並僅在內部網路或受保護的環境中暴露這些端點（例如透過反向代理、VPN 或內部子網路）。

1) 上傳 CSV 並覆寫（需在 header `x-admin-token` 提供 token）：

```bash
curl -v -X POST \
	-H "x-admin-token: $ADMIN_TOKEN" \
	-F "file=@/path/to/new_VIEW_GOODS_enhanced.csv" \
	http://localhost:8000/api/admin/upload-csv
```

2) 清除後端 CSV 快取（讓下一次 /api/search 重新載入 CSV）

```bash
curl -v -X POST -H "x-admin-token: $ADMIN_TOKEN" http://localhost:8000/api/admin/clear-cache
```

Development convenience: bypass token
-----------------------------------

If you want to allow uploads without sending `x-admin-token` during local testing, set `ALLOW_DEV_ADMIN=1` in `backend/.env.dev` or export it in your shell. This will skip token checks on admin endpoints. Only use this in a trusted local environment.

備註：`llm_service.py` 預設使用 OpenAI SDK。若要啟用 LLM 功能請在 `.env` 中設定：

```
OPENAI_API_KEY=你的_openai_api_key
USE_LLM_EXPAND=True
USE_LLM_INTENT=True
USE_LLM_RERANK=False
USE_LLM_SHORTDESC=True
USE_LLM_PROMO=False
OPENAI_MODEL=gpt-4o-mini
```

注意：呼叫 OpenAI API 會產生費用，請先確認帳戶額度與使用策略。

### 啟用 LLM 功能

1. 複製 `.env.example` 為 `.env`，並填入真實的 `OPENAI_API_KEY`。
2. 依需求調整下列旗標（均為 `True/False`）：
   - `USE_LLM_INTENT`：啟用語意解析，讓查詢理解「慈心認證」「不含XX」等語意。
   - `USE_LLM_EXPAND`：啟用查詢擴展，提高關鍵字覆蓋率。
   - `USE_LLM_RERANK`：使用 LLM 重新排序結果（需注意成本與延遲）。
   - `USE_LLM_SHORTDESC`：沒有文案時，生成簡短描述。
   - `USE_LLM_PROMO`：嘗試撰寫社群風格的商品文案。
3. 重新啟動後端服務，環境變數生效即可。
