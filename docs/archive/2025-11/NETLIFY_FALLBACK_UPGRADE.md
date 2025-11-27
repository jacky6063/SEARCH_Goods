# Netlify 部署觸發機制升級 - Hook → API Fallback

**版本**: v2.0  
**日期**: 2025年11月6日  
**狀態**: ✅ 已部署到 GitHub Actions  

## 📋 升級內容

GitHub Actions CI/CD 工作流程已升級，現在使用 **雙重備份** 部署觸發機制：

```
Build Hook (首選) 
    ↓
失敗？ → Netlify REST API (自動降級)
    ↓
成功 → 前端部署開始 → 狀態輪詢 → 完成
```

## 🔧 觸發邏輯

### 階段 1: Build Hook 嘗試
- 如果設置了 `NETLIFY_BUILD_HOOK_URL`：
  - 執行 GET 預檢 (預期 405 Method Not Allowed)
  - 執行 POST 觸發
  - 檢查 HTTP 狀態碼 (200-399 為成功)

### 階段 2: API 自動降級
- 如果 Hook 失敗或未設置：
  - 使用 `NETLIFY_AUTH_TOKEN` + `NETLIFY_SITE_ID`
  - 調用 Netlify REST API (`/sites/{id}/builds`)
  - 啟用 `"clear_cache":true` 確保前端更新
  - 檢查 HTTP 狀態碼 (200-399 為成功)

## ✅ 必需的 GitHub Secrets

| Secret | 必填 | 說明 | 來源 |
|--------|------|------|------|
| `NETLIFY_BUILD_HOOK_URL` | ❌ 可選 | Build Hook URL | Netlify → Site configuration → Build & deploy → Build hooks |
| `NETLIFY_AUTH_TOKEN` | ✅ 必填 | API 認証令牌 | Netlify → User settings → Applications → Personal access tokens |
| `NETLIFY_SITE_ID` | ✅ 必填 | 網站 ID | Netlify → Site settings → General → Site information |
| `OPENAI_API_KEY` | ❌ 可選 | LLM 功能 (非部署必需) | OpenAI Platform |

## 🚀 設置步驟

### 1️⃣ 獲取 Build Hook URL (可選但建議)

1. 前往 **Netlify → Site configuration → Build & deploy → Build hooks**
2. 點擊 **Add build hook**
3. 填寫表單：
   - **Hook name**: `GitHub Actions`
   - **Branch to build**: `main`
4. 複製生成的 URL: `https://api.netlify.com/build_hooks/xxxxx`

### 2️⃣ 獲取 Auth Token (必需)

1. 前往 **Netlify → User settings → Applications → Personal access tokens**
2. 點擊 **New access token**
3. 命名為 `github-actions` (或自訂)
4. 複製生成的令牌: `nf_xxxxxxxxxxxxxxxxxxxxx`

### 3️⃣ 獲取 Site ID (必需)

1. 前往 **Netlify → Site settings → General**
2. 在 **Site information** 區段找到 **Site ID**
3. 複製 ID: `xxxxxxxxxxxxxxxxxxxxxxxx`

### 4️⃣ 設置 GitHub Secrets

前往 **GitHub → Repository → Settings → Secrets and variables → Actions**，添加以下 secrets：

```bash
# 1. Build Hook URL (可選)
NETLIFY_BUILD_HOOK_URL = https://api.netlify.com/build_hooks/xxxxx

# 2. Auth Token (必填)
NETLIFY_AUTH_TOKEN = nf_xxxxxxxxxxxxxxxxxxxxx

# 3. Site ID (必填)
NETLIFY_SITE_ID = xxxxxxxxxxxxxxxxxxxxxxxx

# 4. OpenAI API Key (可選，用於 LLM 測試)
OPENAI_API_KEY = sk-proj-xxxxxxxxxxxxxxxxxxxxx
```

## 🔄 工作流程執行順序

```
GitHub Actions Triggered (Push to main)
    ↓
[1] Test Job - 運行後端測試 (~8-10 秒)
    • pytest 所有測試
    • LLM 測試自動跳過（若無 API KEY）
    • ✅ 通過 → 進入部署
    ❌ 失敗 → 停止，不部署
    ↓
[2] Deploy Job - 觸發前端部署 (~50+ 秒)
    • 嘗試 Build Hook
    • Hook 失敗自動改走 API
    • 等待 45 秒讓 Netlify 開始構建
    • 煙霧測試 (GET /)
    ↓
[3] Poll Status Job - 輪詢部署狀態 (最多 ~6 分鐘)
    • 每 15 秒查詢一次部署狀態
    • 等待 "ready" 或 "published"
    • 成功時顯示最終 URL
    ↓
✅ 完成 - 前端自動更新到最新版本
```

## 📊 失敗排查

### 問題 1: Build Hook 返回 404

**症狀**: `POST code: 404`

**原因**: Hook URL 已過期或被刪除

**解決方案**:
1. 前往 Netlify → Site configuration → Build hooks
2. 刪除舊的 Hook
3. 點擊 **Add build hook** 創建新的
4. 複製新 URL 到 GitHub Secret `NETLIFY_BUILD_HOOK_URL`

### 問題 2: API 返回 401

**症狀**: `API code: 401` / `unauthorized`

**原因**: `NETLIFY_AUTH_TOKEN` 無效或過期

**解決方案**:
1. 前往 Netlify → User settings → Applications
2. 查看現有令牌，可能需要重新生成
3. 複製新令牌到 GitHub Secret `NETLIFY_AUTH_TOKEN`

### 問題 3: API 返回 404

**症狀**: `API code: 404` / `site not found`

**原因**: `NETLIFY_SITE_ID` 錯誤或不存在

**解決方案**:
1. 前往 Netlify → Site settings → General
2. 驗證 **Site ID** 是否正確
3. 更新 GitHub Secret `NETLIFY_SITE_ID`

### 問題 4: 測試失敗導致部署被跳過

**症狀**: Deploy Job 未執行

**原因**: Test Job 失敗

**解決方案**:
1. 檢查 GitHub Actions 日誌中的測試輸出
2. 確認所有依賴已安裝 (`pip install -r backend/requirements.txt`)
3. 本地運行 `pytest` 進行調試
4. 修復代碼並推送新提交

## 🎯 最佳實踐

1. **定期驗證**:
   ```bash
   # 本地測試
   cd backend
   pytest -q
   
   # 確認沒有阻止部署的失敗
   ```

2. **監控部署日誌**:
   - 查看 GitHub Actions 選項卡的執行日誌
   - 每個步驟都會清晰記錄成功/失敗

3. **保持 Token 安全**:
   - 定期檢查 Netlify 令牌的使用情況
   - 若發現異常活動立即重新生成

4. **使用兩層機制的好處**:
   - Build Hook 更快（無 HTTP 往返）
   - API 更可靠（永不過期）
   - 雙重備份確保部署幾乎不會失敗

## 📚 相關資源

- [Netlify Build Hooks 文檔](https://docs.netlify.com/configure-builds/build-hooks/)
- [Netlify API 文檔](https://docs.netlify.com/api/overview/)
- [GitHub Actions 文檔](https://docs.github.com/en/actions)

## 📝 更新日誌

### v2.0 (2025-11-06)
- ✅ 實現 Hook → API Fallback 機制
- ✅ 詳細的日誌輸出
- ✅ 自動化降級邏輯
- ✅ 完整的故障排查指南

### v1.0 (2025-11-05)
- 基礎 Build Hook 觸發

---

**狀態**: 🟢 生產就緒  
**最後更新**: 2025年11月6日  
**維護者**: GitHub Copilot

