# 🔄 Git 同步指南 - 本地與雲端比對更新

**檢查時間**: 2025年11月6日  
**狀態**: ⚠️ **本地落後遠端 1 個提交**

---

## 📊 目前狀況

### 遠端狀態
```
遠端最新提交 (origin/main): 5e5b5ec
提交信息: Fix SITE_URL in CI workflow configuration
時間: 2025-11-06 15:20:32 +0800
改動: .github/workflows/ci.yml (1 行改變)
```

### 本地狀態
```
本地最新提交 (HEAD): 93b7926
提交信息: docs: GitHub 代碼推送完整報告
落後遠端: 1 個提交
未提交更改: frontend/index.html (已修改)
```

---

## 🔍 遠端更新內容

### CI 工作流改變 (.github/workflows/ci.yml)

```diff
- SITE_URL: https://goodsearch.netlify.app   # 替換為你的正式站網址
+ SITE_URL: https://goodssearch.netlify.app   # 替換為你的正式站網址
```

**改變內容**: SITE_URL 環境變數更新  
**舊值**: `https://goodsearch.netlify.app`  
**新值**: `https://goodssearch.netlify.app`  
**原因**: 修正 Netlify 站點 URL

---

## 📋 同步方案

### 方案 A: 快速同步 (推薦) ⭐

#### 步驟 1: 保存本地修改
```bash
# 暫存本地未提交的前端改動
cd /Users/huangchangchi/Documents/SEARCH_Goods
git stash

# 驗證暫存成功
git status  # 應看到: working tree clean
```

#### 步驟 2: 拉取遠端更新
```bash
# 拉取最新的 CI 工作流
git pull origin main

# 驗證更新成功
git log --oneline -3
# 應看到最新提交: 5e5b5ec
```

#### 步驟 3: 恢復本地修改
```bash
# 恢復之前暫存的前端改動
git stash pop

# 檢查狀態
git status
```

#### 步驟 4: 提交本地改動
```bash
# 提交前端改動
git add frontend/index.html
git commit -m "feat: 更新前端邏輯 + 同步遠端 CI 工作流

- 本地前端改進
- 同步遠端 SITE_URL 更新 (5e5b5ec)
- 確保 CI 工作流使用正確的 Netlify URL"

# 推送到遠端
git push origin main
```

---

### 方案 B: 詳細比對同步

#### 步驟 1: 查看完整差異
```bash
# 查看本地 vs 遠端的所有差異
git diff main origin/main

# 查看只有遠端的新提交
git log main..origin/main --oneline

# 查看遠端所有變更
git show origin/main
```

#### 步驟 2: 手動檢查遠端文件
```bash
# 查看遠端版本的 CI 工作流
git show origin/main:.github/workflows/ci.yml | head -20

# 查看本地版本
cat .github/workflows/ci.yml | head -20

# 對比查看
git diff main origin/main -- .github/workflows/ci.yml
```

#### 步驟 3: 選擇更新方式

**選項 A: 快速轉發 (Fast-forward)**
```bash
git merge origin/main
```

**選項 B: 合併並創建新提交**
```bash
git merge --no-ff origin/main -m "Merge remote CI workflow updates"
```

**選項 C: 變基 (Rebase)**
```bash
git rebase origin/main
```

---

### 方案 C: 一鍵完整同步腳本

```bash
#!/bin/bash
cd /Users/huangchangchi/Documents/SEARCH_Goods

echo "🔄 開始同步遠端更新..."
echo "======================"

# 1. 暫存本地修改
echo "✅ 步驟 1: 暫存本地修改"
git stash

# 2. 同步遠端
echo "✅ 步驟 2: 拉取遠端更新"
git fetch origin
git pull origin main

# 3. 恢復本地修改
echo "✅ 步驟 3: 恢復本地修改"
git stash pop

# 4. 查看狀態
echo "✅ 步驟 4: 驗證同步成功"
git status
git log --oneline -3

echo ""
echo "🎉 同步完成！"
echo "下一步: git add . && git commit && git push"
```

---

## 🎯 我推薦的操作步驟

### 快速方案 (5 分鐘完成)

```bash
# 1. 進入項目目錄
cd /Users/huangchangchi/Documents/SEARCH_Goods

# 2. 暫存前端修改
git stash

# 3. 拉取遠端更新 (包含 CI 工作流修改)
git pull origin main

# 4. 恢復前端修改
git stash pop

# 5. 查看同步後的狀態
git status

# 6. 提交所有更改
git add frontend/index.html
git commit -m "sync: 同步遠端 CI 工作流 & 前端改進

- 拉取遠端 SITE_URL 更新 (5e5b5ec)
- 保留本地前端改進
- 準備進行新的部署"

# 7. 推送到遠端
git push origin main
```

---

## 📝 同步後的結果

完成上述步驟後，您將擁有：

✅ **遠端最新的 CI 工作流**
- 正確的 SITE_URL 環境變數
- 最新的部署配置

✅ **本地所有改進**
- frontend/index.html 的熱門分類優化
- 所有文檔更新

✅ **完全同步的代碼庫**
- 本地 = 遠端 = 生產環境
- 無衝突，無落差

---

## 📊 同步前後對比

### 同步前
```
遠端 (origin/main): 5e5b5ec ← 最新
                      ↑
本地 (main):        93b7926 ← 落後
                 + frontend/index.html 未提交

狀態: ❌ 不同步
```

### 同步後
```
遠端 (origin/main): abc1234 (新)
                      ↑
本地 (main):        abc1234 ← 同步
                 + 已提交所有更改

狀態: ✅ 完全同步
```

---

## 🔧 故障排查

### 如果遇到衝突

```bash
# 查看衝突
git status

# 查看衝突內容
git diff

# 手動解決衝突後
git add .
git commit -m "Merge: 解決衝突"
```

### 如果需要放棄本地修改

```bash
# 放棄本地修改，採用遠端版本
git checkout -- frontend/index.html
git pull origin main
```

### 如果需要放棄遠端更新

```bash
# 強制本地版本覆蓋遠端
git push -f origin main
```

---

## 📚 相關 Git 命令速查

| 命令 | 說明 |
|------|------|
| `git fetch origin` | 下載遠端更新（不合併） |
| `git pull origin main` | 下載並合併遠端更新 |
| `git status` | 查看本地狀態 |
| `git diff main origin/main` | 比對本地與遠端 |
| `git stash` | 暫存本地修改 |
| `git stash pop` | 恢復暫存的修改 |
| `git log --oneline -3` | 查看最近 3 個提交 |
| `git show origin/main:.github/workflows/ci.yml` | 查看遠端文件內容 |

---

## ✅ 檢查清單

在執行同步前，確認：

- [ ] 確認本地修改已保存
- [ ] 已閱讀遠端更新內容
- [ ] 選擇合適的同步方案
- [ ] 備份重要文件 (可選)

在執行同步後，確認：

- [ ] `git status` 顯示 working tree clean
- [ ] `git log --oneline -3` 包含遠端最新提交 (5e5b5ec)
- [ ] `.github/workflows/ci.yml` 中 SITE_URL 已更新
- [ ] 所有本地改進仍然保留
- [ ] 無衝突提示

---

**建議**: 執行上述「快速方案」的 7 個步驟，5 分鐘內完成同步！
