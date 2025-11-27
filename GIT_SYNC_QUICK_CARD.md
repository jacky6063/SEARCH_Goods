# ⚡ 雲端同步 - 快速決策卡

**版本**: 1.0  
**適用**: SEARCH_Goods 項目  
**最後更新**: 2025年11月6日

---

## 🎯 快速決策 (只看這個！)

### Q: 雲端有新更新，我該怎麼辦？

```
檢查本地狀態
    ↓
git status
    ↓
「nothing to commit」?
    ├─ ✅ 是 → 執行: git pull origin main
    │          完成！
    │
    └─ ❌ 否 → 執行:
              git stash
              git pull origin main
              git stash pop
              git add .
              git commit -m "sync: ..."
              git push origin main
              完成！
```

---

## 💡 3 個必知命令

### 1️⃣ 查看雲端是否有新更新
```bash
git fetch origin
git log main..origin/main --oneline
```
✅ 如果有輸出 → 雲端比較新

### 2️⃣ 自動同步 (無本地修改)
```bash
git pull origin main
```
✅ 最快最安全，95% 情況適用

### 3️⃣ 手動同步 (有本地修改)
```bash
git stash                    # 暫存本地修改
git pull origin main         # 同步遠端
git stash pop                # 恢復本地修改
git add . && git commit      # 提交
git push origin main         # 推送
```
✅ 最安全，適合有本地改動

---

## ✨ 5 秒快速同步

```bash
# 複製下方整段，一鍵執行
cd /Users/huangchangchi/Documents/SEARCH_Goods && \
git stash && \
git pull origin main && \
git stash pop && \
git add . && \
git commit -m "sync: 同步遠端更新" && \
git push origin main && \
echo "✅ 同步完成！"
```

---

## ⚠️ 常見情況

| 情況 | 命令 | 時間 |
|------|------|------|
| **本地無修改** | `git pull origin main` | 2 秒 |
| **本地有修改** | 見上方 3 秒快速同步 | 10 秒 |
| **只查看遠端新提交** | `git log main..origin/main --oneline` | 1 秒 |
| **只同步某個文件** | `git checkout origin/main -- 文件路徑` | 3 秒 |
| **放棄本地改動用遠端** | `git checkout -- .` + `git pull` | 5 秒 |

---

## 🚨 出現衝突怎麼辦？

```bash
# 1. 查看衝突
git status

# 2. 查看衝突詳情
git diff

# 3. 手動編輯衝突文件 (用編輯器打開)
code 衝突文件名

# 4. 解決後提交
git add .
git commit -m "resolve: 解決合併衝突"

# 5. 如果太複雜，回滾
git merge --abort
```

---

## 📋 三種方案速查表

### 方案 A: 快速同步 (推薦)
```
情況: 本地無修改
命令: git pull origin main
時間: 2 秒
風險: 低
```

### 方案 B: 標準同步
```
情況: 本地有小修改
命令: 
  git stash
  git pull origin main
  git stash pop
  git add . && git commit && git push
時間: 10 秒
風險: 低
```

### 方案 C: 手動同步
```
情況: 本地有大改動
命令:
  git fetch origin
  git log main..origin/main  # 查看
  git diff main origin/main   # 查看
  git pull origin main
  # 解決衝突
  git add . && git commit && git push
時間: 1-5 分鐘
風險: 低
```

---

## ✅ 驗證同步成功

執行任何同步後，驗證：

```bash
# 1. 查看狀態
git status
# 期望: working tree clean

# 2. 查看日誌
git log --oneline -3
# 期望: 包含遠端最新提交

# 3. 查看分支
git branch -v
# 期望: main = origin/main
```

---

## 🎯 我的 30 秒建議

對於 SEARCH_Goods：

**每次開始工作時:**
```bash
git pull origin main
```

**完成工作後:**
```bash
git add .
git commit -m "feat/fix: 描述"
git push origin main
```

**就這麼簡單！** ✅

---

## 🔗 完整文檔

詳細內容請查看：`GIT_SYNC_STRATEGY.md`

包含：
- 詳細的決策樹
- 每種策略的完整步驟
- 故障排查指南
- 推薦最佳實踐
- 自動同步腳本

---

## 💭 記住這句話

> **「遠端代碼已測試，本地改進已暫存，自動同步最安全。」**

🎉 **就這麼簡單！**
