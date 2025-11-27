# Netlify 404 錯誤診斷與修復指南

**問題**: `GET https://goodsearch.netlify.app => HTTP 404`  
**發生時間**: GitHub Actions CI/CD 執行時的 Smoke Test 步驟  
**嚴重性**: 🔴 高 - 前端部署失敗

---

## 📋 問題分析

### 404 可能的原因

| 優先級 | 原因 | 症狀 | 概率 |
|--------|------|------|------|
| 🔴 高 | 前端構建失敗 | Netlify 構建日誌有錯誤 | 60% |
| 🔴 高 | 錯誤的部署分支 | 部署了錯誤的代碼版本 | 25% |
| 🟡 中 | Build Hook/API 觸發失敗 | Netlify 未收到觸發信號 | 10% |
| 🟢 低 | 網站未完全初始化 | 部署中，等待完成 | 5% |

---

## 🔧 Step-by-Step 診斷流程

### 第 1 步：檢查 Netlify 構建日誌

1. **前往 Netlify Dashboard**
   ```
   https://app.netlify.com
   ```

2. **選擇你的網站**
   ```
   Sites → goodsearch (或你的網站名)
   ```

3. **查看最新部署**
   ```
   Deploys → 最新部署記錄 (通常在上面)
   ```

4. **檢查構建日誌**
   - 點擊部署記錄
   - 查看 **Build log** 選項卡
   - 搜尋 `error` 或 `failed` 關鍵字

**常見的構建錯誤**:
```
❌ npm install failed
❌ Build command exited with code 1
❌ ENOENT: no such file or directory
❌ Module not found: ...
```

### 第 2 步：檢查 GitHub Actions 日誌

1. **前往 GitHub Actions**
   ```
   https://github.com/jacky6063/SEARCH_Goods/actions
   ```

2. **查看最新工作流程執行**
   - 點擊失敗的 workflow run

3. **檢查各個 Job 的輸出**
   ```
   ✅ test job       - 測試是否通過
   ✅ deploy job     - Hook/API 是否成功觸發
   ❌ poll_status job - 是否輪詢到 ready/published
   ❌ smoke test      - 404 發生在這裡
   ```

4. **查看 Deploy Job 的輸出**
   ```
   Trigger Netlify (Hook → API Fallback)
   ├─ Preflight GET → ？
   ├─ POST Hook → ？
   ├─ POST API → ？
   └─ API response → ？
   ```

### 第 3 步：驗證部署是否真的發生

```bash
# 查看 Netlify 最新 5 個部署
# (在 Netlify → Deploys 頁面可以看到)

時間          分支    狀態        URL
2025-11-06    main    ❌ Failed   ...
2025-11-05    main    ✅ Success  ...
```

### 第 4 步：檢查部署設置

1. **Netlify Site Settings**
   ```
   Site settings → Build & deploy
   ```

2. **驗證構建設置**
   ```
   Build command:   npm run build (或你的命令)
   Publish directory: dist (或 build/frontend)
   ```

3. **驗證分支設置**
   ```
   Branch to deploy:  main (確認是 main)
   Deploy previews:   Enabled/Disabled
   ```

---

## 🚀 常見問題與解決方案

### 問題 1: Netlify 說「部署成功」但返回 404

**症狀**:
```
Netlify Deploys 頁面顯示 ✅ Published
但訪問網址返回 404
```

**原因**: 前端文件未正確部署到 Netlify

**解決方案**:
1. **檢查發布目錄**
   ```
   Site settings → Build & deploy → Build settings
   確認 "Publish directory" 指向正確的文件夾
   ```

2. **本地驗證構建**
   ```bash
   cd frontend
   npm run build  # 或你的構建命令
   ls -la dist/   # 確認生成了文件
   cat dist/index.html  # 確認 HTML 存在
   ```

3. **重新觸發部署**
   - Netlify 右上角 → **Trigger deploy** → Deploy site
   - 或推送一個新提交到 main 分支

### 問題 2: Build Hook 返回 404

**症狀**:
```
[Deploy Job 日誌]
POST Hook...
POST code: 404
⚠️ Hook failed. Will try API fallback...
```

**原因**: Build Hook URL 已過期或不存在

**解決方案**:
1. **在 Netlify 刪除舊 Hook**
   ```
   Site configuration → Build & deploy → Build hooks
   找到舊的 Hook → Delete
   ```

2. **創建新 Build Hook**
   ```
   Build hooks → Add build hook
   Hook name: GitHub Actions
   Branch to build: main
   → Create hook
   複製新 URL
   ```

3. **更新 GitHub Secret**
   ```
   https://github.com/jacky6063/SEARCH_Goods/settings/secrets/actions
   NETLIFY_BUILD_HOOK_URL = <新 URL>
   ```

4. **推送新提交以觸發工作流程**
   ```bash
   git commit --allow-empty -m "test: re-trigger with new hook"
   git push origin main
   ```

### 問題 3: API 觸發失敗 (API code: 404)

**症狀**:
```
[Deploy Job 日誌]
Triggering build via Netlify API...
API code: 404
site not found
```

**原因**: `NETLIFY_SITE_ID` 錯誤

**解決方案**:
1. **驗證 Site ID**
   ```
   Netlify → Site settings → General → Site information
   Site ID: xxxxxxxxxxxxxxxxxxxxxxxx (複製)
   ```

2. **更新 GitHub Secret**
   ```
   Settings → Secrets and variables → Actions
   NETLIFY_SITE_ID = <正確的 ID>
   ```

3. **重新推送以觸發工作流程**

### 問題 4: API 觸發失敗 (API code: 401)

**症狀**:
```
API code: 401
unauthorized
```

**原因**: `NETLIFY_AUTH_TOKEN` 無效或過期

**解決方案**:
1. **檢查令牌狀態**
   ```
   Netlify → User settings → Applications → Personal access tokens
   檢查你的 token 是否仍然存在
   ```

2. **重新生成令牌**
   ```
   New access token → Give it a name (e.g., github-actions)
   → Generate token → 複製新令牌
   ```

3. **更新 GitHub Secret**
   ```
   Settings → Secrets and variables → Actions
   NETLIFY_AUTH_TOKEN = <新令牌>
   ```

4. **重新推送工作流程**

### 問題 5: 部署成功但頁面內容錯誤

**症狀**:
```
HTTP 200 OK
但頁面顯示舊版本或錯誤內容
```

**原因**: 瀏覽器緩存或 Netlify 未清除舊緩存

**解決方案**:
1. **清除瀏覽器緩存**
   ```
   Ctrl+Shift+Delete (Windows)
   Cmd+Shift+Delete (Mac)
   → 清除所有時間的緩存
   ```

2. **清除 Netlify CDN 緩存**
   ```
   Site settings → Domain management
   點擊 "Purge cache" 或
   使用 GitHub Actions 中的 clear_cache=true (已包含)
   ```

3. **強制刷新**
   ```
   Ctrl+F5 (或 Cmd+Shift+R)
   訪問: https://goodsearch.netlify.app?v=<timestamp>
   ```

---

## 📊 完整的診斷檢查清單

在 GitHub Actions 失敗時逐項檢查：

### ✅ 代碼和構建

- [ ] 本地 `npm run build` 成功
- [ ] 本地 `git status` 全部 committed
- [ ] `git push origin main` 成功
- [ ] frontend 目錄有 `index.html` 和其他必要文件

### ✅ GitHub Secrets 配置

- [ ] `NETLIFY_AUTH_TOKEN` 已設置且有效
- [ ] `NETLIFY_SITE_ID` 正確無誤
- [ ] `NETLIFY_BUILD_HOOK_URL` (可選，但建議有)
- [ ] `OPENAI_API_KEY` (為了測試通過)

### ✅ Netlify 設置

- [ ] Build command 正確
- [ ] Publish directory 正確指向前端輸出目錄
- [ ] Deploy branch 設為 `main`
- [ ] Build hooks 存在且有效

### ✅ GitHub Actions 執行

- [ ] Test Job 通過 (95/95 tests)
- [ ] Deploy Job 成功觸發 (Hook 或 API)
- [ ] Poll Status 等到 `ready/published`
- [ ] Smoke Test 返回 200-399

### ✅ Netlify 部署

- [ ] Netlify Deploys 頁面顯示最新部署
- [ ] 部署狀態為 `Published` 或 `Ready`
- [ ] Build log 無錯誤
- [ ] 訪問網址返回 200 OK

---

## 🔍 進階診斷

### 查看 GitHub Actions 完整日誌

```bash
# 下載最新工作流程的完整日誌
gh run view <run-id> --log
```

### 直接測試 Netlify API

```bash
# 測試 Auth Token
curl -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  https://api.netlify.com/api/v1/user

# 測試 Site ID
curl -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  https://api.netlify.com/api/v1/sites/$NETLIFY_SITE_ID

# 測試觸發構建
curl -X POST \
  -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"clear_cache":true}' \
  https://api.netlify.com/api/v1/sites/$NETLIFY_SITE_ID/builds
```

### 本地測試 Smoke Test

```bash
# 驗證網站是否真的返回 404
curl -v https://goodsearch.netlify.app

# 查看完整 HTTP 頭
curl -i https://goodsearch.netlify.app

# 檢查重定向
curl -L https://goodsearch.netlify.app
```

---

## 📞 無法自行解決時

### 聯絡 Netlify 支持

1. **前往 Netlify Support**
   ```
   Netlify Dashboard → Help → Contact Support
   ```

2. **提供以下信息**
   ```
   - Site name: goodsearch
   - Issue: 部署返回 404
   - Latest deploy ID: <從日誌中複製>
   - Build log 截圖
   - GitHub Actions 日誌鏈接
   ```

### 檢查 Netlify Status

```
https://www.netlify.com/status
檢查是否有服務中斷
```

---

## 🎯 快速修復流程

**如果只是遇到 404，按照以下順序嘗試**:

### 第 1 次嘗試 (最可能)
```bash
# 1. 檢查 Netlify 構建日誌中是否有錯誤
# 2. 本地測試構建是否成功
npm run build

# 3. 如果構建失敗，修復後推送
git add .
git commit -m "fix: ..."
git push origin main

# 4. 等待 GitHub Actions 完成
# 5. 訪問網站檢查是否修復
```

### 第 2 次嘗試 (可能是 Hook 問題)
```bash
# 1. 在 Netlify 刪除舊 Build Hook
# 2. 創建新 Build Hook (Branch: main)
# 3. 複製新 URL 到 GitHub Secret NETLIFY_BUILD_HOOK_URL

# 4. 推送空提交以觸發工作流程
git commit --allow-empty -m "test: trigger with new hook"
git push origin main
```

### 第 3 次嘗試 (可能是 Secret 問題)
```bash
# 1. 驗證所有 Secrets
#    - NETLIFY_AUTH_TOKEN (有效)
#    - NETLIFY_SITE_ID (正確)
#    - NETLIFY_BUILD_HOOK_URL (最新)

# 2. 如果有更改，推送空提交
git commit --allow-empty -m "test: re-trigger with verified secrets"
git push origin main
```

### 第 4 次嘗試 (清除緩存)
```bash
# 1. 在 Netlify 手動觸發部署
#    Site → Deploys → Trigger deploy → Deploy site

# 2. 清除 CDN 緩存
#    Site settings → Domain management → Purge cache

# 3. 清除瀏覽器緩存並訪問
#    Ctrl+Shift+Delete → 訪問 https://goodsearch.netlify.app
```

---

## 📈 預防措施

### 1. 定期檢查

- 每周檢查一次最新部署狀態
- 監控 GitHub Actions 執行結果
- 審查 Netlify 構建日誌

### 2. 監控告警

- 設置 GitHub 失敗通知
- 配置 Netlify 部署通知
- 訂閱 Netlify Status 更新

### 3. 文檔維護

- 保持 Secrets 文檔最新
- 記錄 Hook URL 變更
- 定期備份 Token

### 4. 測試流程

- 本地完整測試後再推送
- 先推送到測試分支驗證
- 監控生產部署的成功率

---

## 📝 故障日誌範本

記錄每次出現 404 時：

```
[日期] 404 故障記錄

發現時間: 2025-11-06 14:30
錯誤信息: GET https://goodsearch.netlify.app => HTTP 404

診斷結果:
- Netlify 構建狀態: ✅ Published / ❌ Failed
- GitHub Actions 狀態: ✅ Pass / ❌ Fail
- Hook 狀態: ✅ 200 / ❌ 404/401
- API 狀態: ✅ 200 / ❌ 404/401

根本原因: [記錄原因]

解決方案: [記錄所採取的步驟]

結果: ✅ 已解決 / ⏳ 待進一步診斷

耗時: [時間]
```

---

## 🔗 相關資源

- [Netlify 部署故障排查](https://docs.netlify.com/platform/overview/#connectivity)
- [Netlify API 文檔](https://docs.netlify.com/api/overview/)
- [GitHub Actions 文檔](https://docs.github.com/en/actions)
- [NETLIFY_FALLBACK_UPGRADE.md](./NETLIFY_FALLBACK_UPGRADE.md) - 之前的升級指南

---

## 🎯 本指南使用建議

**何時查看此指南**:
- ❌ 遇到 404 錯誤
- ⚠️ 部署返回非 200 狀態碼
- 🔧 Netlify/GitHub Secrets 出現問題
- 📊 需要診斷部署失敗的原因

**查看順序**:
1. 快速修復流程 - 5 分鐘快速嘗試
2. 常見問題與解決方案 - 針對具體症狀
3. 完整診斷檢查清單 - 系統性排查
4. 進階診斷 - 深入技術細節

---

**最後更新**: 2025年11月6日  
**版本**: 1.0  
**狀態**: 📍 就緒

有問題？查看本指南 → 還是無法解決？聯絡 Netlify 支持

