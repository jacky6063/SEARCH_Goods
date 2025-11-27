# 本地開發環境常見問題排除指南

## 為什麼地端設定常常無法順利設定?

本文檔整理了 SEARCH_Goods 專案在本地開發時最常見的問題和解決方案。

---

## 🔴 常見問題 Top 5

### 1. **ModuleNotFoundError: No module named 'xxx'**

**症狀:**
```python
ModuleNotFoundError: No module named 'supabase'
ModuleNotFoundError: No module named 'backend'
ImportError: attempted relative import with no known parent package
```

**根本原因:**
- ❌ `requirements.txt` 有列出但沒有實際安裝套件
- ❌ Python 模組使用了錯誤的 import 方式 (相對引用 vs 絕對引用)
- ❌ 執行目錄不在 `backend/` 下

**解決方案:**
```bash
# A. 確保安裝所有套件
cd backend
source .venv/bin/activate
pip install -r requirements.txt

# B. 檢查特定套件是否安裝
python -c "import supabase; print('✓ supabase 已安裝')"

# C. 從 backend/ 目錄啟動服務 (重要!)
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**關鍵原則:**
- 所有 Python 模組應使用**絕對引用** (不使用 `.` 開頭)
- 啟動 uvicorn 時必須在 `backend/` 目錄下
- 不要使用 `from backend.xxx import yyy` (會失敗)

---

### 2. **Port 已被佔用**

**症狀:**
```
ERROR:    [Errno 48] Address already in use
OSError: [Errno 48] error while attempting to bind on address ('0.0.0.0', 8000)
```

**解決方案:**
```bash
# 方法 A: 清除特定 port
lsof -ti:8000 | xargs kill -9   # 清除後端 port
lsof -ti:5173 | xargs kill -9   # 清除前端 port

# 方法 B: 查看誰佔用 port
lsof -i :8000

# 方法 C: 使用不同的 port
uvicorn app:app --reload --host 0.0.0.0 --port 8001
```

---

### 3. **環境變數未載入 (.env 問題)**

**症狀:**
```python
KeyError: 'SUPABASE_URL'
SupabaseConfigError: Missing required environment variables
```

**根本原因:**
- ❌ `.env` 檔案不存在
- ❌ `.env` 檔案位置錯誤 (應該在專案根目錄)
- ❌ 使用了 `.env.example` 的佔位符而非真實憑證

**解決方案:**
```bash
# 1. 檢查 .env 是否存在
ls -la .env

# 2. 如果不存在,從範本複製
cp .env.example .env

# 3. 填入真實憑證 (不是 your-project-id!)
cat .env
# SUPABASE_URL=https://abcdefgh.supabase.co  ← 真實 URL
# SUPABASE_KEY=eyJhbG...  ← 真實 anon key

# 4. 確保 backend/app.py 正確載入
# 檢查是否有 load_dotenv()
grep -n "load_dotenv" backend/app.py
```

---

### 4. **uvicorn 自動重載後崩潰**

**症狀:**
```
WARNING: WatchFiles detected changes in 'xxx.py'. Reloading...
ERROR: Error loading ASGI app. Could not import module "app"
```

**根本原因:**
- 檔案變更觸發自動重載
- import 路徑在重載後失效
- 相對引用在重載時會失敗

**解決方案:**
```bash
# A. 停用自動重載模式測試
uvicorn app:app --host 0.0.0.0 --port 8000  # 不加 --reload

# B. 檢查最近修改的檔案
git status

# C. 確認所有 import 使用絕對路徑
# ✓ from chat_logging import xxx
# ✗ from .chat_logging import xxx
# ✗ from backend.chat_logging import xxx
```

---

### 5. **虛擬環境未啟用**

**症狀:**
```bash
python: command not found: uvicorn
pip: No module named 'fastapi'
```

**解決方案:**
```bash
# 1. 檢查虛擬環境是否存在
ls backend/.venv

# 2. 如果不存在,建立虛擬環境
cd backend
python3 -m venv .venv

# 3. 啟用虛擬環境
source .venv/bin/activate

# 4. 確認已啟用 (終端機會顯示 (.venv))
which python  # 應該指向 backend/.venv/bin/python

# 5. 安裝依賴
pip install -r requirements.txt
```

---

## 🛠️ 快速診斷流程

遇到問題時,依照以下順序檢查:

```bash
# ✅ 檢查清單
cd /path/to/SEARCH_Goods

# 1. 確認目錄結構
ls backend/app.py        # 應該存在
ls frontend/index.html   # 應該存在
ls .env                  # 應該存在

# 2. 確認虛擬環境
cd backend
source .venv/bin/activate
which python             # 應該在 .venv 內

# 3. 確認套件安裝
python -c "import fastapi, supabase, openai; print('✓ 核心套件已安裝')"

# 4. 確認環境變數
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(f'SUPABASE_URL: {os.getenv(\"SUPABASE_URL\")[:30]}...')"

# 5. 測試服務啟動
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

---

## 🚀 一鍵啟動腳本 (推薦)

為了避免每次都要手動設定,使用自動化腳本:

```bash
# 使用專案提供的啟動腳本
chmod +x start_local_dev.sh
./start_local_dev.sh
```

這個腳本會自動處理:
- ✅ 清理舊進程
- ✅ 檢查並啟動虛擬環境
- ✅ 安裝缺少的套件
- ✅ 驗證環境變數
- ✅ 啟動前後端服務
- ✅ 健康檢查

---

## 📋 環境需求檢查表

### Python 環境
- [ ] Python 3.9+ 已安裝
- [ ] `python3 -m venv` 可用
- [ ] `backend/.venv` 目錄存在

### 必要套件
- [ ] FastAPI 0.104.1
- [ ] Supabase 2.24.0
- [ ] OpenAI 1.3.5
- [ ] uvicorn (含 uvloop)

### 環境變數 (.env)
- [ ] `SUPABASE_URL` (真實 URL,不是佔位符)
- [ ] `SUPABASE_KEY` (anon key)
- [ ] `SUPABASE_SERVICE_KEY` (service role key)
- [ ] `DATABASE_URL` (含真實密碼)
- [ ] `OPENAI_API_KEY` (如果使用 LLM 功能)

### Port 可用性
- [ ] Port 8000 未被佔用 (後端)
- [ ] Port 5173 未被佔用 (前端)

---

## 🔍 深入問題分析

### 為什麼 Import 路徑這麼容易出錯?

**問題根源:**
Python 的模組系統在不同執行方式下行為不同:

1. **直接執行腳本**: `python backend/app.py`
   - `sys.path` 包含 `backend/` 目錄
   - 可以使用 `from xxx import yyy` (絕對引用)
   - ❌ 但相對引用會失敗

2. **uvicorn 執行**: `uvicorn app:app`
   - 必須在 `backend/` 目錄下執行
   - 只能使用絕對引用 (不含 `backend.` 前綴)
   - ❌ `from backend.xxx` 會失敗

3. **作為套件執行**: `python -m backend.app`
   - 需要 `__init__.py` 檔案
   - 可以使用相對引用 `.xxx`
   - ❌ 但此專案不是套件結構

**解決原則:**
- ✅ **統一使用絕對引用,不含 `backend.` 前綴**
- ✅ **從 `backend/` 目錄啟動 uvicorn**
- ✅ **不要使用相對引用 (`.xxx` 或 `..xxx`)**

### Import 修正範例

❌ **錯誤寫法:**
```python
# backend/chat_logging_bridge.py
from backend.chat_logging import xxx      # ✗ 多了 backend 前綴
from .supabase_client import xxx          # ✗ 相對引用
```

✅ **正確寫法:**
```python
# backend/chat_logging_bridge.py
from chat_logging import xxx              # ✓ 絕對引用
from supabase_client import xxx           # ✓ 絕對引用
```

---

## 🎯 最佳實踐

### 開發流程
1. **每次開發前清理環境**
   ```bash
   lsof -ti:8000 | xargs kill -9
   lsof -ti:5173 | xargs kill -9
   ```

2. **使用虛擬環境**
   ```bash
   cd backend
   source .venv/bin/activate
   ```

3. **確認目錄位置**
   ```bash
   pwd  # 應該在 .../SEARCH_Goods/backend
   ```

4. **查看啟動日誌**
   ```bash
   # 不要用 nohup 背景執行,直接看輸出
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

### 檔案結構規範
```
SEARCH_Goods/
├── .env                    ← 環境變數 (真實憑證)
├── .env.example            ← 範本 (佔位符)
├── backend/
│   ├── .venv/              ← 虛擬環境
│   ├── app.py              ← 主程式
│   ├── requirements.txt    ← 依賴清單
│   └── *.py                ← 其他模組
└── frontend/
    └── index.html
```

### 套件管理
```bash
# 新增套件時更新 requirements.txt
pip freeze | grep supabase >> requirements.txt

# 或手動指定版本
echo "supabase==2.24.0" >> requirements.txt

# 安裝時使用 -r
pip install -r requirements.txt
```

---

## 🆘 緊急救援

如果以上都無法解決,執行完整重置:

```bash
# 1. 停止所有進程
lsof -ti:8000 | xargs kill -9
lsof -ti:5173 | xargs kill -9

# 2. 刪除虛擬環境
rm -rf backend/.venv

# 3. 重新建立虛擬環境
cd backend
python3 -m venv .venv
source .venv/bin/activate

# 4. 重新安裝套件
pip install --upgrade pip
pip install -r requirements.txt

# 5. 驗證安裝
python -c "import fastapi, supabase, openai; print('✓ 套件安裝成功')"

# 6. 重新啟動
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

---

## 📞 尋求協助

如果問題仍然存在,請提供以下資訊:

1. **錯誤訊息完整內容**
   ```bash
   tail -50 backend/backend.log
   ```

2. **環境資訊**
   ```bash
   python --version
   pip list | grep -E "fastapi|supabase|openai"
   pwd
   ls -la .env
   ```

3. **執行指令**
   ```bash
   # 你執行的完整指令
   ```

4. **目錄結構**
   ```bash
   tree -L 2 -I '.venv|node_modules'
   ```

---

## 🔗 相關文檔

- [ADMIN_GUIDE.md](../ADMIN_GUIDE.md) - 系統管理指南
- [DEPLOYMENT_SETUP.md](../DEPLOYMENT_SETUP.md) - 部署設定
- [.github/copilot-instructions.md](../.github/copilot-instructions.md) - 專案架構

---

最後更新: 2025-11-13
