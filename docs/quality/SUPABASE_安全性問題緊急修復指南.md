# Supabase 安全性問題緊急修復指南

**建立日期**: 2025-11-13  
**優先級**: 🔴 **P0 - 立即修復 (24 小時內)**  
**問題**: `.env.example` 洩漏真實生產憑證

---

## 🚨 問題確認

### 洩漏的憑證

從 `.env.example` (Line 2-5):
```bash
SUPABASE_URL=https://jyflluhapfmbrqjlnjwy.supabase.co
SUPABASE_KEY=eyJhbGci...（完整 anon JWT token）
SUPABASE_SERVICE_KEY=sb_secret_pl7tj5DkqlDQkXLpclgr6g_cmK74DDb
DATABASE_URL=postgresql://postgres:<CWpY2nSj1IaZRmcC>@db.jyflluhapfmbrqjlnjwy.supabase.co:5432/postgres
```

### 風險等級

| 憑證類型 | 風險 | 影響範圍 |
|---------|------|---------|
| **SUPABASE_SERVICE_KEY** | 🔴 極高 | 可繞過所有 RLS 規則,讀取/修改/刪除所有資料 |
| **DATABASE_URL 密碼** | 🔴 極高 | 可直接連線 PostgreSQL,執行任意 SQL |
| **SUPABASE_KEY (anon)** | 🟡 中等 | 受 RLS 規則限制,但可能洩漏商業邏輯 |
| **SUPABASE_URL** | 🟢 低 | 公開資訊,但暴露專案 ID |

---

## 🛠️ 緊急修復步驟 (按順序執行)

### 步驟 1: 立即更換所有憑證 (30 分鐘內)

#### 1.1 更換 Service Role Key

1. 登入 [Supabase Dashboard](https://supabase.com/dashboard)
2. 選擇專案: `search_goods` (`jyflluhapfmbrqjlnjwy`)
3. 前往 **Settings** → **API**
4. 找到 **Service Role Key** 區塊
5. 點擊 **Reset Service Role Key**
6. ⚠️ **確認重置後,複製新的 key 並儲存到安全位置**

#### 1.2 更換 Database Password

1. 在 Supabase Dashboard
2. 前往 **Settings** → **Database**
3. 找到 **Database Settings** → **Reset Database Password**
4. 輸入新密碼 (建議使用密碼管理器生成 32 位隨機密碼)
5. 點擊 **Reset Password**
6. ⚠️ **更新 `DATABASE_URL` 環境變數中的密碼**

#### 1.3 更換 Anon Key (選用)

> ⚠️ 注意: 更換 Anon Key 會影響所有前端應用

1. 在 Supabase Dashboard → **Settings** → **API**
2. 找到 **Anon Key** → **Reset Anon Key**
3. 更新前端的 `SUPABASE_KEY` 環境變數

---

### 步驟 2: 修改 `.env.example` (5 分鐘)

**目標**: 移除真實憑證,改用佔位符

執行以下修改:

```bash
# 備份當前版本
cp .env.example .env.example.backup-$(date +%Y%m%d)

# 編輯 .env.example
```

**修改內容**:

```bash
# Supabase (search_goods)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here_eyJ...
SUPABASE_SERVICE_KEY=your_service_role_key_here
DATABASE_URL=postgresql://postgres:<YOUR_PASSWORD>@db.your-project.supabase.co:5432/postgres
```

**提交變更**:

```bash
git add .env.example
git commit -m "security: Replace real credentials with placeholders in .env.example"
git push origin main
```

---

### 步驟 3: 清理 Git 歷史記錄 (1 小時)

⚠️ **重要**: 即使修改了 `.env.example`,舊的憑證仍存在於 Git 歷史中

#### 選項 A: 使用 BFG Repo-Cleaner (推薦)

```bash
# 1. 安裝 BFG (macOS)
brew install bfg

# 2. 克隆完整倉庫 (包含 mirror)
cd ~/Documents
git clone --mirror https://github.com/jacky6063/SEARCH_Goods.git SEARCH_Goods-mirror.git

# 3. 清除敏感資料
cd SEARCH_Goods-mirror.git
bfg --replace-text ../passwords.txt

# 4. 清理並推送
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force

# 5. 通知團隊成員重新克隆倉庫
```

**`passwords.txt` 內容**:
```text
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp5ZmxsdWhhcGZtYnJxamxuand5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI5NTM5NjEsImV4cCI6MjA3ODUyOTk2MX0.nnAALXteChGTpjf8UWuh9mPIU-GPW9Slx_gAZGKTGx8===>REMOVED_ANON_KEY
sb_secret_pl7tj5DkqlDQkXLpclgr6g_cmK74DDb===>REMOVED_SERVICE_KEY
<CWpY2nSj1IaZRmcC>===>YOUR_PASSWORD
```

#### 選項 B: 使用 git-filter-repo (替代方案)

```bash
# 1. 安裝 git-filter-repo
pip install git-filter-repo

# 2. 在倉庫根目錄執行
cd /Users/huangchangchi/Documents/SEARCH_Goods
git filter-repo --path .env.example --invert-paths --force

# 3. 重新推送
git remote add origin https://github.com/jacky6063/SEARCH_Goods.git
git push --force --all
```

---

### 步驟 4: 更新部署環境變數 (30 分鐘)

#### 4.1 Render (Backend)

1. 登入 [Render Dashboard](https://render.com)
2. 選擇 `SEARCH_Goods` 服務
3. 前往 **Environment** 設定
4. 更新以下變數:
   ```
   SUPABASE_SERVICE_KEY=<新的 service role key>
   DATABASE_URL=postgresql://postgres:<新密碼>@...
   ```
5. 點擊 **Save** (會自動觸發重新部署)

#### 4.2 Netlify (Frontend)

1. 登入 [Netlify Dashboard](https://netlify.com)
2. 選擇 `SEARCH_Goods` 站點
3. 前往 **Site settings** → **Build & deploy** → **Environment**
4. 更新:
   ```
   SUPABASE_KEY=<新的 anon key>
   ```
5. 觸發重新部署: **Deploys** → **Trigger deploy**

#### 4.3 GitHub Actions Secrets

1. 前往 GitHub 倉庫
2. **Settings** → **Secrets and variables** → **Actions**
3. 更新:
   ```
   SUPABASE_URL (保持不變)
   SUPABASE_KEY (新 anon key)
   SUPABASE_SERVICE_KEY (新 service role key)
   ```

---

### 步驟 5: 更新本地開發環境 (10 分鐘)

```bash
# 1. 更新本地 .env 檔案
cd /Users/huangchangchi/Documents/SEARCH_Goods
nano .env

# 2. 更新為新憑證
SUPABASE_SERVICE_KEY=<新的 service role key>
DATABASE_URL=postgresql://postgres:<新密碼>@...

# 3. 重啟服務
lsof -ti:8000 | xargs kill -9
source backend/.venv/bin/activate
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 4. 驗證連線
python scripts/supabase_db_test.py
```

---

## ✅ 驗證修復

### 檢查清單

- [ ] **Supabase Service Role Key 已更換**
- [ ] **Database Password 已更換**
- [ ] **`.env.example` 已修改為佔位符**
- [ ] **Git 歷史已清理** (使用 BFG 或 git-filter-repo)
- [ ] **Render 環境變數已更新**
- [ ] **Netlify 環境變數已更新**
- [ ] **GitHub Secrets 已更新**
- [ ] **本地 `.env` 已更新**
- [ ] **服務正常運作** (執行 smoke test)

### 驗證腳本

```bash
# 執行 Supabase 連線測試
cd /Users/huangchangchi/Documents/SEARCH_Goods
source backend/.venv/bin/activate
python scripts/supabase_db_test.py

# 預期輸出: [] 或包含資料的陣列
# 若報錯 "Invalid API key",表示憑證尚未更新完成
```

---

## 🔒 預防措施 (長期)

### 1. 設定 Pre-commit Hooks

```bash
# 安裝 pre-commit
pip install pre-commit

# 創建 .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: package.lock.json
EOF

# 初始化
pre-commit install
pre-commit run --all-files
```

### 2. 使用 git-secrets

```bash
# 安裝 (macOS)
brew install git-secrets

# 在倉庫中設定
cd /Users/huangchangchi/Documents/SEARCH_Goods
git secrets --install
git secrets --register-aws

# 新增自訂規則
git secrets --add 'SUPABASE_SERVICE_KEY=sb_secret_[a-zA-Z0-9_]+'
git secrets --add 'postgresql://postgres:[^@]+@'
```

### 3. 啟用 GitHub Secret Scanning

1. 前往 GitHub 倉庫 **Settings**
2. **Code security and analysis**
3. 啟用:
   - ✅ **Secret scanning**
   - ✅ **Push protection** (阻止推送包含密鑰的提交)

### 4. 建立憑證管理規範

創建 `docs/security/CREDENTIAL_MANAGEMENT.md`:

```markdown
# 憑證管理規範

## 原則
1. ❌ 絕不將真實憑證提交到版本控制
2. ✅ 使用環境變數管理敏感資訊
3. ✅ `.env` 加入 `.gitignore`
4. ✅ `.env.example` 只包含佔位符

## 檢查清單
- [ ] 新增環境變數前檢查是否為敏感資訊
- [ ] 提交前執行 `git secrets --scan`
- [ ] 定期輪換 Service Role Key (每季)
- [ ] 監控 Supabase 存取日誌
```

---

## 📞 緊急聯絡

如遇到問題:
1. **Supabase 支援**: https://supabase.com/support
2. **GitHub 支援**: https://support.github.com
3. **內部聯絡**: [填寫團隊負責人資訊]

---

## 📊 執行時間線

| 時間 | 任務 | 負責人 | 狀態 |
|------|------|--------|------|
| T+0h | 更換 Supabase 憑證 | [DevOps] | ⚪ 待執行 |
| T+1h | 修改 `.env.example` 並提交 | [Dev] | ⚪ 待執行 |
| T+2h | 清理 Git 歷史 | [DevOps] | ⚪ 待執行 |
| T+4h | 更新所有部署環境 | [DevOps] | ⚪ 待執行 |
| T+24h | 驗證修復並產出報告 | [QA] | ⚪ 待執行 |
| T+1週 | 實施預防措施 | [Dev + DevOps] | ⚪ 待執行 |

---

**修復完成後請更新**: `docs/quality/SUPABASE_整合品管審查報告_v3.md` (標記 P0 問題已解決)
