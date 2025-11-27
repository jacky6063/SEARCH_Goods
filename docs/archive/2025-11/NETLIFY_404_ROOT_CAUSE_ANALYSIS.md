# Netlify 404 根本原因分析 & 完整修復指南

**日期**: 2025年11月6日
**狀態**: 🔴 **正在診斷 - Netlify 返回 404**

---

## 1️⃣ 問題現象

```
[10/10] GET https://goodsearch.netlify.app => HTTP 404
❌ Failed: Site still returning 404 after 10 retries (5+ minutes)
```

- **症狀**: Netlify 站點持續返回 HTTP 404
- **測試時間**: 2025年11月6日 06:17 UTC
- **重試次數**: 10 次 × 30 秒間隔 = 5+ 分鐘
- **Netlify 狀態**: 伺服器在線，但無法找到內容

---

## 2️⃣ 環境信息

### 本地環境驗證 ✅

```bash
# 文件存在性檢查
$ file /Users/huangchangchi/Documents/SEARCH_Goods/frontend/index.html
=> HTML document text, Unicode text, UTF-8 text

# 文件大小
$ ls -lah frontend/index.html
=> -rw-rw-r--  1 huangchangchi  staff   108K 11月  6 10:32 index.html

# 目錄結構
$ ls -lah frontend/
total 232
-rw-r--r--@  1 huangchangchi  staff   6.0K 10月 25 17:23 .DS_Store
-rw-rw-r--@  1 huangchangchi  staff   108K 11月  6 10:32 index.html ✅
drwxrwxr-x@  9 huangchangchi  staff   288B 10月 25 17:24 patches
drwxrwxr-x@  3 huangchangchi  staff    96B 10月 25 22:51 public
```

**本地驗證結果**: ✅ 所有文件存在且完整

### Netlify 配置驗證 ✅

**netlify.toml** (檔案路徑: `/netlify.toml`):
```toml
[build]
  publish = "frontend"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

**配置驗證結果**: ✅ 配置正確
- ✅ `publish` 指向 `frontend` 目錄
- ✅ SPA 重定向規則已設定
- ✅ 所有路由導向 `/index.html`

### 遠端部署檢查 ❌

```bash
$ curl -s -I https://goodsearch.netlify.app
HTTP/2 404 
cache-control: private, max-age=0
content-type: text/plain; charset=utf-8
date: Thu, 06 Nov 2025 06:17:17 GMT
server: Netlify
strict-transport-security: max-age=31536000; includeSubDomains; preload
x-nf-request-id: 01K9BWZWT25TYXXKM3NEHV90VC
```

**遠端狀態**: ❌ Netlify 上無法找到內容

---

## 3️⃣ 可能的根本原因 (按優先級排列)

### 🔴 **原因 A: Netlify 上未部署最新代碼** (概率: 90%)

**症狀**:
- 本地 `index.html` 存在並完整 ✅
- Netlify 配置正確 ✅
- Netlify 仍返回 404 ❌

**調查清單**:
- [ ] Netlify 上次部署時間是否在 Git 最後一次推送之後?
- [ ] 最後的推送是否包含 `frontend/index.html` 的變更?
- [ ] Netlify Build Hook 或 API 觸發是否成功?
- [ ] Netlify 構建日誌中是否有錯誤?

**修復方案**:
1. 在 Netlify 網站上手動觸發重新部署
2. 檢查 Netlify 構建日誌
3. 驗證 Build Hook URL 是否正確
4. 如果 Hook 失敗，使用 Netlify API 觸發

---

### 🟡 **原因 B: 推送時文件未被追蹤** (概率: 5%)

**症狀**:
- Git 配置問題阻止了 `frontend/index.html` 的推送

**調查清單**:
```bash
# 檢查 Git 中的文件狀態
git status
git ls-files | grep frontend/

# 檢查 .gitignore
cat .gitignore | grep -i frontend
```

**修復方案**:
```bash
# 強制添加
git add -f frontend/index.html
git commit -m "fix: 確保 frontend/index.html 被推送"
git push origin main
```

---

### 🟠 **原因 C: Netlify 部署腳本問題** (概率: 3%)

**症狀**:
- Build command 執行失敗或未正確發布 `frontend` 目錄

**調查清單**:
- [ ] 在 Netlify 上檢查 "Build & deploy settings"
- [ ] Build command 是否設定正確?
- [ ] Publish directory 是否確實設為 `frontend`?

---

### 🟢 **原因 D: DNS 或 CDN 緩存問題** (概率: 2%)

**修復方案**:
```bash
# 清空 Netlify 緩存並重新部署
curl -s -X POST \
  -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"clear_cache":true}' \
  "https://api.netlify.com/api/v1/sites/$NETLIFY_SITE_ID/builds"
```

---

## 4️⃣ 診斷命令

### 步驟 1: 驗證 Git 狀態

```bash
cd /Users/huangchangchi/Documents/SEARCH_Goods

# 檢查最近的提交
git log --oneline -5

# 檢查 frontend/index.html 是否在版本控制中
git ls-files | grep "frontend/index.html"

# 檢查文件的最後提交時間
git log -1 --format="%ai" -- frontend/index.html
```

### 步驟 2: 驗證文件完整性

```bash
# 確認文件大小和內容
ls -lh frontend/index.html
head -c 100 frontend/index.html | od -c

# 檢查是否有 BOM 或編碼問題
file frontend/index.html
hexdump -C frontend/index.html | head -5
```

### 步驟 3: 檢查 Netlify 部署狀態

```bash
# 使用 Netlify API 查詢最近的部署
curl -s -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  "https://api.netlify.com/api/v1/sites/$NETLIFY_SITE_ID/deploys?per_page=1" \
  | jq '.[0] | {id, state, created_at, updated_at, deploy_ssl_url, error_message}'
```

### 步驟 4: 檢查 Netlify 構建日誌

```bash
# 查詢最近部署的構建日誌
curl -s -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  "https://api.netlify.com/api/v1/sites/$NETLIFY_SITE_ID/deploys?per_page=1" \
  | jq -r '.[0].id' | xargs -I {} \
  curl -s -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  "https://api.netlify.com/api/v1/deploys/{}/logs"
```

---

## 5️⃣ 立即修復步驟

### 選項 A: 使用 Netlify UI 手動部署 (最快 ⚡)

1. 登錄 [Netlify.com](https://app.netlify.com)
2. 進入 "goodsearch" 網站
3. 點擊 **"Deploys"** 標籤
4. 點擊 **"Trigger deploy"** → **"Deploy site"**
5. 等待部署完成（2-3 分鐘）
6. 測試: `curl -I https://goodsearch.netlify.app`

### 選項 B: 使用 Build Hook (如果已配置) 📌

```bash
# 觸發 Build Hook
curl -X POST $NETLIFY_BUILD_HOOK_URL

# 等待部署完成
sleep 120

# 測試
curl -I https://goodsearch.netlify.app
```

### 選項 C: 使用 Netlify API (完整控制) 🔧

```bash
# 設定環境變數
export NETLIFY_AUTH_TOKEN="your-token"
export NETLIFY_SITE_ID="your-site-id"

# 觸發帶有緩存清除的部署
curl -X POST \
  -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"clear_cache":true}' \
  "https://api.netlify.com/api/v1/sites/$NETLIFY_SITE_ID/builds"

# 等待部署
sleep 150

# 驗證
curl -s "https://api.netlify.com/api/v1/sites/$NETLIFY_SITE_ID/deploys?per_page=1" \
  -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" | jq '.[0].state'
```

### 選項 D: 強制推送新代碼 (最終手段) 💪

```bash
cd /Users/huangchangchi/Documents/SEARCH_Goods

# 確保所有文件都已追蹤
git add -f frontend/index.html netlify.toml

# 建立新的提交
git commit -m "fix: 強制重新部署 - 修復 Netlify 404 問題

- 確保 frontend/index.html 被正確部署
- 驗證 netlify.toml 配置
- 觸發 Netlify 完整重新構建

測試: curl https://goodsearch.netlify.app"

# 推送
git push origin main

# Netlify 應該在收到推送後自動部署
```

---

## 6️⃣ 驗證修復

修復後，運行以下檢查：

```bash
#!/bin/bash
echo "🔍 Netlify 404 修復驗證清單"
echo "================================"

# 1. 測試主頁
echo "1️⃣ 測試主頁..."
code=$(curl -s -o /dev/null -w "%{http_code}" https://goodsearch.netlify.app)
echo "主頁狀態碼: $code (應為 200-299)"

# 2. 測試 SPA 路由
echo ""
echo "2️⃣ 測試 SPA 路由 (應重定向到 /index.html)..."
curl -s -I https://goodsearch.netlify.app/search | head -5

# 3. 測試子路由
echo ""
echo "3️⃣ 測試子路由重定向..."
curl -s -o /dev/null -w "狀態: %{http_code}\n" https://goodsearch.netlify.app/unknown-path

# 4. 檢查內容類型
echo ""
echo "4️⃣ 檢查內容類型..."
curl -s -I https://goodsearch.netlify.app | grep -i content-type

# 5. 檢查 HTML 內容
echo ""
echo "5️⃣ 檢查 HTML 內容..."
curl -s https://goodsearch.netlify.app | head -c 500

echo ""
echo "✅ 如果所有檢查都通過，Netlify 已成功恢復!"
```

---

## 7️⃣ 預防措施

為了防止 Netlify 404 問題再次發生，請實施：

### CI/CD 改進 (`.github/workflows/ci.yml`)

```yaml
# 在部署後添加更詳細的驗證
- name: Verify Netlify deployment
  run: |
    # 等待 Netlify 準備好
    for i in {1..20}; do
      status=$(curl -s -o /dev/null -w "%{http_code}" https://goodsearch.netlify.app)
      if [ "$status" -eq 200 ]; then
        echo "✅ Netlify 已準備好 (HTTP $status)"
        exit 0
      fi
      echo "[$i/20] 等待 Netlify... (HTTP $status)"
      sleep 15
    done
    echo "❌ Netlify 仍未準備好"
    exit 1
```

### GitHub Actions 日誌增強

```yaml
# 在部署後輸出更多調試信息
- name: Debug deploy info
  if: always()
  run: |
    echo "📋 Netlify 部署信息"
    echo "===================="
    echo "時間: $(date)"
    echo "Git 提交: $(git rev-parse HEAD)"
    echo "Frontend 文件:"
    ls -lh frontend/
    echo ""
    echo "最近 Git 日誌:"
    git log --oneline -5
```

---

## 8️⃣ 跟進行動

✅ **立即行動**:
1. [ ] 運行診斷命令第 1-4 步
2. [ ] 選擇修復選項 A、B、C 或 D
3. [ ] 運行驗證修復腳本
4. [ ] 確認 Netlify 返回 200 狀態碼

📌 **30 分鐘後**:
- [ ] 重新測試 https://goodsearch.netlify.app
- [ ] 檢查 GitHub Actions 工作流是否成功完成

🔔 **長期監控**:
- [ ] 添加 Uptime 監控 (如 Ping.pea.rs)
- [ ] 設定 Netlify 構建失敗通知
- [ ] 定期測試 API 端點

---

**下一步**: 請執行上述診斷命令，並告訴我們結果。這將幫助我們確定確切的根本原因並應用適當的修復。
