# CI/CD Workflow 全面審查報告

## 🔍 審查日期：2025-11-13

## ❌ 發現的邏輯錯誤

### 1. **ci.yml - Line 30 & 37：條件檢查使用 env 而非 secrets**

#### 問題代碼：
```yaml
- name: Supabase connectivity smoke test (anon key)
  if: ${{ env.SUPABASE_URL != '' && env.SUPABASE_KEY != '' }}
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}

- name: Supabase service-role write check
  if: ${{ env.SUPABASE_URL != '' && env.SUPABASE_KEY != '' }}
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
```

#### 錯誤分析：
- ❌ **邏輯錯誤**：`if` 條件檢查 `env.*` 但實際變數在 step 層級的 `env` 中定義
- ❌ **作用域問題**：`if` 條件在 step 執行前評估，此時 step 層級的 `env` 尚未設置
- ❌ **實際行為**：條件永遠為 false（`env.SUPABASE_URL` 不存在於 job/workflow 層級）
- ❌ **後果**：這兩個測試步驟永遠不會執行

#### 正確寫法：
```yaml
- name: Supabase connectivity smoke test (anon key)
  if: ${{ secrets.SUPABASE_URL != '' && secrets.SUPABASE_KEY != '' }}
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}

- name: Supabase service-role write check
  if: ${{ secrets.SUPABASE_URL != '' && secrets.SUPABASE_SERVICE_KEY != '' }}
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
```

#### 影響程度：
- 🔴 **高** - Supabase 測試從未真正執行過
- 🔴 若 Supabase 配置有問題，CI 無法檢測

---

### 2. **ci.yml - Line 40：使用錯誤的 secret 名稱**

#### 問題代碼：
```yaml
- name: Supabase service-role write check
  if: ${{ env.SUPABASE_URL != '' && env.SUPABASE_KEY != '' }}  # 檢查 SUPABASE_KEY
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}  # 實際使用 SERVICE_KEY
```

#### 錯誤分析：
- ❌ **不一致**：條件檢查 `SUPABASE_KEY` 但實際使用 `SUPABASE_SERVICE_KEY`
- ❌ **邏輯缺陷**：即使修復作用域問題，條件仍然檢查錯誤的 secret
- ❌ **應檢查**：`secrets.SUPABASE_SERVICE_KEY` 而非 `secrets.SUPABASE_KEY`

---

### 3. **ci.yml - Line 62：pytest 失敗被忽略**

#### 問題代碼：
```yaml
- name: Run pytest (skip LLM tests if no API key)
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    echo "Running backend tests..."
    pytest -v --maxfail=3 --disable-warnings || true
```

#### 錯誤分析：
- ❌ **|| true 隱藏失敗**：所有測試失敗都會被忽略
- ❌ **CI 失去意義**：測試失敗不會阻止部署
- ❌ **風險**：破壞性代碼可能被部署到生產環境

#### 建議方案：
```yaml
# 方案 A：移除 || true，讓測試失敗阻止部署
run: |
  echo "Running backend tests..."
  pytest -v --maxfail=3 --disable-warnings

# 方案 B：只允許 LLM 測試失敗
run: |
  echo "Running backend tests..."
  pytest -v --maxfail=3 --disable-warnings -m "not llm" || \
  (echo "⚠️ Core tests failed!" && exit 1)
  pytest -v -m "llm" || echo "⚠️ LLM tests skipped/failed (optional)"
```

#### 影響程度：
- 🟡 **中** - CI 無法有效防止破壞性變更
- 🟡 可能部署有 bug 的代碼

---

### 4. **ci.yml - Line 80：frontend/dist 目錄不存在**

#### 問題代碼：
```yaml
- name: Deploy to Netlify
  run: |
    echo "🚀 Starting Netlify deploy..."
    npx netlify deploy --prod --dir=frontend/dist --site=$NETLIFY_SITE_ID --auth=$NETLIFY_AUTH_TOKEN
```

#### 錯誤分析：
- ❌ **目錄不存在**：專案中沒有 `frontend/dist` 目錄
- ❌ **實際結構**：前端是單檔案 `frontend/index.html`
- ❌ **實際行為**：部署可能失敗或部署空目錄

#### 正確寫法：
```yaml
- name: Deploy to Netlify
  run: |
    echo "🚀 Starting Netlify deploy..."
    npx netlify deploy --prod --dir=frontend --site=$NETLIFY_SITE_ID --auth=$NETLIFY_AUTH_TOKEN
```

#### 影響程度：
- 🔴 **高** - 部署可能失敗或部署錯誤內容

---

### 5. **deploy.yml - Line 68：secrets 條件檢查語法錯誤（已修復）**

#### 之前的問題代碼：
```yaml
- name: Trigger Render deployment
  if: env.RENDER_SERVICE_ID && env.RENDER_API_KEY  # ❌ 舊語法
```

#### ✅ 已修復：
```yaml
- name: Trigger Render deployment
  if: ${{ env.RENDER_SERVICE_ID && env.RENDER_API_KEY }}
```

#### 狀態：
- ✅ 已在之前的 commit 中修復

---

## 📊 優先級修復清單

### 🔴 P0 - 立即修復（阻斷性問題）

1. **修復 ci.yml Line 30 & 37 的條件檢查**
   - 從 `env.*` 改為 `secrets.*`
   - Line 37 同時修正檢查 `SUPABASE_SERVICE_KEY`

2. **修復 ci.yml Line 80 的部署目錄**
   - 從 `frontend/dist` 改為 `frontend`

### 🟡 P1 - 高優先級（風險較高）

3. **決策 ci.yml Line 62 的測試失敗處理**
   - 移除 `|| true` 或實施選擇性失敗策略
   - 確保核心測試失敗會阻止部署

### 🟢 P2 - 優化建議（非阻斷）

4. **增加部署前檢查**
   - 確認必要的 secrets 存在
   - 驗證部署目錄結構

5. **改善錯誤報告**
   - 測試失敗時提供更詳細的訊息
   - 部署失敗時記錄詳細錯誤

---

## 🔧 完整修復代碼

### ci.yml 修復方案

```yaml
# 修復 1: Supabase 測試條件（Line 30）
- name: Supabase connectivity smoke test (anon key)
  if: ${{ secrets.SUPABASE_URL != '' && secrets.SUPABASE_KEY != '' }}
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
  run: python scripts/supabase_db_test.py

# 修復 2: Supabase service-role 測試條件（Line 37）
- name: Supabase service-role write check
  if: ${{ secrets.SUPABASE_URL != '' && secrets.SUPABASE_SERVICE_KEY != '' }}
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
    SUPABASE_TABLE: chat_sessions
  run: |
    python - <<'PY'
    import os
    from supabase import create_client
    
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    table = os.environ.get("SUPABASE_TABLE", "chat_sessions")
    client = create_client(url, key)
    row = {
        "module_type": "ci_smoke",
        "status": "ongoing",
        "channel": "ci_workflow",
    }
    resp = client.table(table).insert(row).execute()
    assert resp.data, "Service-role insert returned empty data"
    PY

# 修復 3: pytest 失敗處理（Line 62）
- name: Run pytest (skip LLM tests if no API key)
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    echo "Running backend tests..."
    pytest -v --maxfail=3 --disable-warnings

# 修復 4: Netlify 部署目錄（Line 80）
- name: Deploy to Netlify
  env:
    NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
    NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
  run: |
    echo "🚀 Starting Netlify deploy..."
    npx netlify deploy --prod --dir=frontend --site=$NETLIFY_SITE_ID --auth=$NETLIFY_AUTH_TOKEN
    echo "✅ Deploy command executed. Proceeding to status check..."
```

---

## 📋 測試驗證計劃

### 修復後驗證步驟：

1. **提交修復後觸發 workflow**
   ```bash
   git add .github/workflows/ci.yml
   git commit -m "fix: 修復 CI workflow 邏輯錯誤"
   git push origin main
   ```

2. **檢查 Supabase 測試是否真正執行**
   - 查看 workflow logs
   - 確認 "Supabase connectivity smoke test" 步驟有輸出
   - 確認 "Supabase service-role write check" 步驟有輸出

3. **驗證測試失敗會阻止部署**
   - 故意引入一個測試失敗
   - 確認 workflow 在 test job 失敗
   - 確認 deploy job 不會執行

4. **驗證 Netlify 部署成功**
   - 確認部署到正確目錄
   - 訪問 https://goodsearch.netlify.app 確認內容正確

---

## 🎯 總結

### 發現問題數量：
- 🔴 P0 阻斷問題：2 個（條件檢查、部署目錄）
- 🟡 P1 風險問題：1 個（測試失敗處理）
- 🟢 P2 優化建議：2 個

### 預期影響：
- **修復前**：Supabase 測試從未執行、測試失敗被忽略、部署目錄可能錯誤
- **修復後**：完整的 CI 保護、正確的測試覆蓋、可靠的部署流程

### 建議執行順序：
1. 立即修復 P0 問題（條件檢查 + 部署目錄）
2. 評估並修復 P1 問題（測試失敗處理策略）
3. 逐步實施 P2 優化建議

---

## 📝 相關文檔

- GitHub Actions 條件語法：https://docs.github.com/en/actions/learn-github-actions/expressions
- Secrets vs Environment Variables：https://docs.github.com/en/actions/security-guides/encrypted-secrets
- Netlify CLI 部署：https://docs.netlify.com/cli/get-started/
