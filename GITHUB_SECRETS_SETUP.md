# GitHub Secrets 配置指南

## 概述

本文檔列出 SEARCH_Goods 在 GitHub Actions CI/CD 流程中所需的所有環境變數和密鑰。

---

## 📋 必要的 Secrets

### 1. OPENAI_API_KEY
**用途**: 用於 LLM 相關功能（查詢擴展、內容生成等）

**獲取方法**:
1. 訪問 https://platform.openai.com/api-keys
2. 登錄你的 OpenAI 賬號
3. 點擊 "Create new secret key"
4. 複製金鑰（格式: `sk-...`）

**設置步驟**:
```bash
# 方法 1: GitHub CLI (推薦)
gh secret set OPENAI_API_KEY
# 系統會提示輸入值，貼上你的 API 金鑰

# 方法 2: GitHub Web UI
# 1. 訪問: https://github.com/jacky6063/SEARCH_Goods/settings/secrets/actions
# 2. 點擊 "New repository secret"
# 3. 名稱: OPENAI_API_KEY
# 4. 值: sk-...（你的 API 金鑰）
# 5. 點擊 "Add secret"
```

**注意**:
- 若不設置此 Secret，CI 會自動跳過所有 LLM 相關測試
- 確保金鑰有效且未過期

---

### 2. NETLIFY_BUILD_HOOK_URL
**用途**: 觸發 Netlify 前端自動部署

**獲取方法**:
1. 訪問 https://app.netlify.com
2. 選擇你的前端站點
3. 轉到 **Site settings** → **Build & deploy** → **Build hooks**
4. 點擊 **Add build hook**
5. 名稱: `GitHub Actions`
6. 分支: 選擇 `main`
7. 點擊 **Save**
8. 複製生成的 URL（格式: `https://api.netlify.com/build_hooks/xxxxx`）

**設置步驟**:
```bash
# 方法 1: GitHub CLI
gh secret set NETLIFY_BUILD_HOOK_URL
# 貼上你的 Build Hook URL

# 方法 2: GitHub Web UI
# 1. 訪問: https://github.com/jacky6063/SEARCH_Goods/settings/secrets/actions
# 2. 點擊 "New repository secret"
# 3. 名稱: NETLIFY_BUILD_HOOK_URL
# 4. 值: https://api.netlify.com/build_hooks/xxxxx
# 5. 點擊 "Add secret"
```

---

### 3. NETLIFY_SITE_ID
**用途**: 用於輪詢部署狀態

**獲取方法**:
1. 訪問 https://app.netlify.com
2. 選擇你的前端站點
3. 轉到 **Site settings** → **General** → **Site information**
4. 複製 **API ID**（格式: `xxxxxxxxxxxxxxxxxxxxxxxx`）

**設置步驟**:
```bash
# 方法 1: GitHub CLI
gh secret set NETLIFY_SITE_ID

# 方法 2: GitHub Web UI (如上)
```

---

### 4. NETLIFY_AUTH_TOKEN
**用途**: 用於 Netlify API 認證（輪詢部署狀態）

**獲取方法**:
1. 訪問 https://app.netlify.com/user/settings/applications
2. 轉到 **Personal access tokens**
3. 點擊 **New access token**
4. 提供名稱（如 `GitHub Actions CI`）
5. 點擊 **Generate token**
6. 複製生成的 token（格式: `nf_...`）

**設置步驟**:
```bash
# 方法 1: GitHub CLI
gh secret set NETLIFY_AUTH_TOKEN

# 方法 2: GitHub Web UI (如上)
```

---

## 📊 可選的 Secrets (用於後端部署)

### 5. RENDER_SERVICE_ID
**用途**: 觸發 Render 後端部署

**獲取方法**:
1. 訪問 https://dashboard.render.com
2. 選擇你的後端服務
3. 複製 Service ID（格式: `srv_xxxxx`）

**設置步驟**:
```bash
gh secret set RENDER_SERVICE_ID
```

---

### 6. RENDER_API_KEY
**用途**: Render API 認證

**獲取方法**:
1. 訪問 https://dashboard.render.com
2. 轉到 Account Settings
3. 點擊 **API Tokens**
4. 生成新的 API Key
5. 複製 token（格式: `rnd_xxxx`）

**設置步驟**:
```bash
gh secret set RENDER_API_KEY
```

---

## ✅ 驗證 Secrets 已正確設置

訪問你的倉庫 Secrets 頁面:
https://github.com/jacky6063/SEARCH_Goods/settings/secrets/actions

你應該看到以下 Secrets（值被隱藏）:
- ✅ `OPENAI_API_KEY`
- ✅ `NETLIFY_BUILD_HOOK_URL`
- ✅ `NETLIFY_SITE_ID`
- ✅ `NETLIFY_AUTH_TOKEN`
- (可選) `RENDER_SERVICE_ID`
- (可選) `RENDER_API_KEY`

---

## 🧪 測試 CI 流程

1. **建立測試提交**:
   ```bash
   cd /Users/huangchangchi/Documents/SEARCH_Goods
   git commit --allow-empty -m "test: 驗證 GitHub Actions CI 流程"
   git push origin main
   ```

2. **監控工作流程執行**:
   - 訪問: https://github.com/jacky6063/SEARCH_Goods/actions
   - 查看最新的工作流程執行
   - 點擊查看詳細日誌

3. **預期結果**:
   - ✅ `test` 工作完成（所有 pytest 通過）
   - ✅ `deploy` 工作完成（Netlify 構建觸發）
   - ✅ Netlify 前端自動構建並發布
   - ✅ `poll_status` 工作完成（確認部署就緒）

---

## 🔧 故障排除

### 問題 1: 部署步驟跳過
**症狀**: GitHub Actions 中看不到 `deploy` 或 `poll_status` 步驟

**原因**: Secrets 未設置或設置錯誤

**解決**:
1. 檢查 https://github.com/jacky6063/SEARCH_Goods/settings/secrets/actions
2. 驗證所有 4 個必要 Secrets 都已添加
3. 檢查值是否正確（特別是 URL 格式）
4. 重新推送代碼以重試

### 問題 2: Netlify 構建失敗
**症狀**: "Trigger Netlify Build Hook" 步驟返回非 2xx/3xx HTTP 碼

**原因**:
- Build Hook URL 無效或已過期
- 分支設置錯誤
- Netlify 站點設置問題

**解決**:
1. 重新生成 Build Hook URL
2. 驗證分支設置為 `main`
3. 檢查 Netlify 站點是否為 "Paused" 狀態

### 問題 3: 輪詢超時
**症狀**: "Poll deploy status" 步驟超時

**原因**:
- Netlify 構建耗時過長
- `NETLIFY_AUTH_TOKEN` 或 `NETLIFY_SITE_ID` 無效

**解決**:
1. 增加輪詢超時時間（編輯 `.github/workflows/ci.yml`）
2. 驗證 Netlify API token 和 site ID
3. 檢查 Netlify 站點的構建日誌

### 問題 4: 測試失敗
**症狀**: "Run pytest" 步驟失敗

**原因**:
- Python 依賴問題
- 代碼錯誤

**解決**:
1. 查看 GitHub Actions 日誌詳情
2. 在本地運行測試:
   ```bash
   cd backend
   pip install -r requirements.txt
   pytest -q
   ```
3. 修復後推送

---

## 📌 環境變數總覽

| 環境變數名稱 | 類型 | 必要 | 用途 | 獲取來源 |
|---|---|---|---|---|
| `OPENAI_API_KEY` | Secret | 可選 | LLM 功能 | OpenAI Platform |
| `NETLIFY_BUILD_HOOK_URL` | Secret | 必要 | 前端部署觸發 | Netlify Site Settings |
| `NETLIFY_SITE_ID` | Secret | 必要 | 部署狀態查詢 | Netlify Site Info |
| `NETLIFY_AUTH_TOKEN` | Secret | 必要 | Netlify API 認證 | Netlify User Settings |
| `RENDER_SERVICE_ID` | Secret | 可選 | 後端部署觸發 | Render Dashboard |
| `RENDER_API_KEY` | Secret | 可選 | Render API 認證 | Render Account |

---

## 📞 相關文檔

- CI 工作流程: `.github/workflows/ci.yml`
- pytest 配置: `backend/tests/conftest.py`
- 部署文檔: `DEPLOYMENT_SETUP.md`

---

**上次更新**: 2025年11月6日
**狀態**: 配置指南完成
