# 自動部署設定指南

## 概述
SEARCH_Goods 已配置完整的 CI/CD 流程，支持在推送到 `main` 分支時自動部署到 Render (後端) 和 Netlify (前端)。

## 工作流程架構

```
┌─────────────────────────────────────────────────────────────┐
│ Git Push to main 分支                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
   ┌────▼─────┐              ┌──────▼─────┐
   │ CI Tests │              │ Build Image │
   └────┬─────┘              └──────┬─────┘
        │ (tests pass)              │ (push to GHCR)
        └──────────────┬────────────┘
                       │
            ┌──────────▼──────────┐
            │ Trigger Deployments  │
            └──────┬───────────┬──┘
                   │           │
            ┌──────▼──┐   ┌───▼──────┐
            │  Render │   │ Netlify  │
            │ (後端)  │   │ (前端)   │
            └─────────┘   └──────────┘
```

## 所需的 GitHub Secrets

部署自動化需要在 GitHub 倉庫中配置以下密鑰。

### 1️⃣ Render 密鑰

**RENDER_SERVICE_ID**
- 從 Render Dashboard 獲得
- 後端服務的唯一識別碼
- 格式: `srv_xxxxxxxxxxxxxxxx`

**RENDER_API_KEY**
- 從 Render Account Settings → API Keys 獲得
- 允許 GitHub Actions 觸發部署
- 格式: `rnd_xxxxxxxxxxxxxxxxxxxxxxxx`

### 2️⃣ Netlify 密鑰

**NETLIFY_SITE_ID**
- 從 Netlify Site settings → General → Site information 獲得
- 前端應用的唯一識別碼
- 格式: `xxxxxxxxxxxxxxxxxxxxxxxx`

**NETLIFY_AUTH_TOKEN**
- 從 Netlify User settings → Applications → Personal access tokens 獲得
- 允許 GitHub Actions 觸發部署
- 格式: `nf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## 設置步驟

### 步驟 1: 獲取 Render 密鑰

1. 訪問 [Render Dashboard](https://dashboard.render.com)
2. 選擇您的後端服務
3. 複製 **Service ID** (右上角或 URL 中)
   - URL 格式: `https://dashboard.render.com/services/srv_xxxxx`
4. 轉到 [Account Settings](https://dashboard.render.com/account/api-tokens)
5. 在 "API Tokens" 部分創建新的 API Key
6. 複製生成的 **API Key**

### 步驟 2: 獲取 Netlify 密鑰

1. 訪問 [Netlify Dashboard](https://app.netlify.com)
2. 選擇您的前端站點
3. 轉到 **Site settings** → **General** → **Site information**
4. 複製 **API ID** (即 NETLIFY_SITE_ID)
5. 轉到 [User settings](https://app.netlify.com/user/settings/applications)
6. 在 "Personal access tokens" 部分創建新的 token
7. 複製生成的 **Access Token** (即 NETLIFY_AUTH_TOKEN)

### 步驟 3: 在 GitHub 添加 Secrets

1. 訪問您的 GitHub 倉庫: https://github.com/jacky6063/SEARCH_Goods
2. 轉到 **Settings** → **Secrets and variables** → **Actions**
3. 點擊 **New repository secret**，逐個添加以下密鑰:

| 密鑰名稱 | 值 | 來源 |
|---------|-----|------|
| `RENDER_SERVICE_ID` | `srv_xxxxx` | Render Dashboard |
| `RENDER_API_KEY` | `rnd_xxxx` | Render API Tokens |
| `NETLIFY_SITE_ID` | `xxxxx` | Netlify Site Info |
| `NETLIFY_AUTH_TOKEN` | `nf_xxxxx` | Netlify Personal Tokens |

### 步驟 4: 驗證設置

1. 在本機進行一個測試提交:
   ```bash
   cd /Users/huangchangchi/Documents/SEARCH_Goods
   git commit --allow-empty -m "test: 測試自動部署"
   git push origin main
   ```

2. 訪問 GitHub 倉庫的 **Actions** 標籤
3. 您應該看到新的工作流程執行
4. 檢查各個步驟的執行狀態:
   - ✅ 後端測試 (backend tests)
   - ✅ Docker 鏡像構建 (Docker build)
   - ✅ Render 部署觸發
   - ✅ Netlify 部署觸發

## 工作流程細節

### deploy.yml 中的步驟

#### 1. 後端測試 (tests job)
```yaml
- 檢出代碼
- 安裝 Python 3.10
- 安裝依賴 (backend/requirements.txt)
- 執行 pytest (backend/tests/)
```

**失敗時**: 工作流程停止，不會進行後續部署

#### 2. 構建 Docker 鏡像 (build_image job)
```yaml
- 需要: tests job 通過
- 設置 QEMU 和 Docker Buildx
- 登錄到 GitHub Container Registry (GHCR)
- 構建並推送鏡像到 ghcr.io/{owner}/search_goods:{tag}
```

**標籤**:
- `latest` - 最新版本
- `{commit_sha}` - 特定提交版本

#### 3. 觸發部署 (deploy job)
```yaml
- 需要: tests 和 build_image 都通過
- 如果設置了 RENDER_* 密鑰，觸發 Render 部署
- 如果設置了 NETLIFY_* 密鑰，觸發 Netlify 部署
```

## 故障排除

### 問題: 部署步驟被跳過

**原因**: 密鑰未設置

**解決方案**:
```bash
# 檢查是否所有必需的密鑰都已添加
# GitHub Settings → Secrets → 驗證這些密鑰存在:
# - RENDER_SERVICE_ID
# - RENDER_API_KEY
# - NETLIFY_SITE_ID
# - NETLIFY_AUTH_TOKEN
```

### 問題: Render 部署失敗

**原因**: API Key 無效或過期

**解決方案**:
1. 訪問 Render Dashboard
2. 重新生成 API Key
3. 更新 GitHub Secrets 中的 `RENDER_API_KEY`

### 問題: Netlify 部署失敗

**原因**: Access Token 無效或權限不足

**解決方案**:
1. 訪問 Netlify User Settings
2. 重新生成 Personal Access Token
3. 更新 GitHub Secrets 中的 `NETLIFY_AUTH_TOKEN`

### 問題: 測試失敗導致部署停止

**原因**: 後端測試未通過

**解決方案**:
1. 檢查 GitHub Actions 日誌了解失敗詳情
2. 修復代碼中的問題
3. 再次推送以重試

## 部署前檢查清單

在提交代碼前，請確認:

- ✅ 後端測試通過: `cd backend && pytest -q`
- ✅ 沒有 Python 語法錯誤
- ✅ CSV 檔案格式正確
- ✅ 環境變數配置無誤
- ✅ Docker 映像可本地構建

## 本地部署測試

### 在本地運行完整的 CI/CD 流程

```bash
# 1. 安裝依賴
cd backend
pip install -r requirements.txt

# 2. 運行測試
pytest -q

# 3. 構建 Docker 鏡像
docker build -t search_goods:test .

# 4. 測試 Docker 鏡像
docker run -p 8000:8000 -e ALLOW_DEV_ADMIN=1 search_goods:test
```

## 環境變數配置

### Render 後端環境變數

在 Render Dashboard 中設置這些環境變數:

```bash
USE_LLM_EXPAND=True
USE_LLM_SHORTDESC=True
USE_LLM_RERANK=False
USE_LLM_INTENT=True
USE_LLM_PROMO=False
OPENAI_API_KEY=sk-...  # 如果使用 LLM 功能
ADMIN_TOKEN=your-secure-token-here
DATA_PATH=/data/VIEW_GOODS_enhanced.csv
CATEGORIES_PATH=/data/goods_categories.csv
```

### Netlify 前端環境變數

在 Netlify Dashboard 中設置:

```bash
VITE_API_BASE=https://your-render-backend-url.com
```

## 監控部署狀態

### GitHub Actions 儀表板

訪問: https://github.com/jacky6063/SEARCH_Goods/actions

您可以看到:
- ✅ 所有工作流程執行歷史
- ✅ 每個工作流程的詳細日誌
- ✅ 成功/失敗狀態
- ✅ 執行時間和資源使用

### Render 部署監控

訪問: https://dashboard.render.com → 您的服務 → Deploys

### Netlify 部署監控

訪問: https://app.netlify.com → 您的站點 → Deploys

## 手動觸發部署

### 不推送代碼的情況下手動部署

#### 在 Render 上手動部署

```bash
curl -X POST \
  https://api.render.com/v1/services/YOUR_SERVICE_ID/deploys \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### 在 Netlify 上手動部署

```bash
curl -X POST \
  https://api.netlify.com/api/v1/sites/YOUR_SITE_ID/deploys \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 相關文件

- `.github/workflows/deploy.yml` - 主要部署工作流程
- `.github/workflows/ci.yml` - 持續集成配置
- `Dockerfile` - Docker 鏡像定義
- `backend/requirements.txt` - Python 依賴
- `docker-compose.yml` - Docker Compose 配置

## 支持的事件

當前部署工作流程在以下情況下觸發:

| 事件 | 分支 | 行為 |
|------|------|------|
| Push | main | 完整 CI/CD 流程，包括測試、構建和部署 |
| Pull Request | * | 僅運行測試 (由 ci.yml 處理) |

## 下一步

1. ✅ 設置所有必需的 GitHub Secrets
2. ✅ 測試推送以驗證工作流程
3. ✅ 監控 GitHub Actions 日誌
4. ✅ 檢查 Render 和 Netlify 的部署狀態

---

**更新日期**: 2025年11月6日
**配置狀態**: ✅ 已就緒
