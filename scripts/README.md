# 自動部署腳本使用指南

## 📁 腳本概覽

本專案提供了完整的自動化部署解決方案，當程式碼有異動時可以自動更新 GitHub 並觸發 Render（後端）和 Netlify（前端）的部署。

### 🚀 腳本清單

| 腳本 | 功能 | 用途 |
|-----|------|------|
| `auto_deploy.sh` | 手動部署 | 檢測變更並執行部署 |
| `watch_deploy.sh` | 自動監控部署 | 監控檔案變更並自動觸發部署 |
| `setup.sh` | 環境設置 | 安裝依賴並配置環境 |

## 🛠️ 快速開始

### 1. 環境設置
```bash
# 執行設置腳本，安裝所有必要依賴
./scripts/setup.sh

# 或使用 npm
npm run setup
```

### 2. 手動部署
```bash
# 基本部署（檢測變更並部署）
./scripts/auto_deploy.sh

# 使用自訂提交訊息
./scripts/auto_deploy.sh -m "feat: add new feature"

# 強制部署（即使沒有變更）
./scripts/auto_deploy.sh --force

# 使用 npm
npm run deploy
npm run deploy:force
```

### 3. 自動監控部署
```bash
# 啟動檔案監控，自動檢測變更並部署
./scripts/watch_deploy.sh

# 使用 npm
npm run deploy:watch
```

## 📖 詳細說明

### auto_deploy.sh - 手動部署腳本

**功能特色：**
- ✅ 自動檢測程式碼變更
- ✅ 執行後端測試（可選）
- ✅ 自動提交到 Git
- ✅ 推送到 GitHub
- ✅ 監控部署狀態
- ✅ 彩色輸出和進度顯示

**使用方法：**
```bash
./scripts/auto_deploy.sh [選項]

選項：
  -m, --message MSG    自訂提交訊息
  -b, --branch BRANCH  指定分支 (預設: main)
  -f, --force          強制部署（即使沒有變更）
  -h, --help           顯示說明

環境變數：
  SKIP_TESTS=true      跳過測試執行
  MONITOR_DEPLOYMENT=false  跳過部署狀態監控
```

**範例：**
```bash
# 基本使用
./scripts/auto_deploy.sh

# 自訂提交訊息
./scripts/auto_deploy.sh -m "fix: resolve search bug"

# 跳過測試並強制部署
SKIP_TESTS=true ./scripts/auto_deploy.sh --force

# 部署到特定分支
./scripts/auto_deploy.sh -b development
```

### watch_deploy.sh - 自動監控部署腳本

**功能特色：**
- 👀 即時監控檔案變更
- 🔄 自動觸發部署流程
- ⏱️ 防抖機制避免頻繁觸發
- 🎯 智能忽略特定檔案類型
- 🌐 跨平台支援（macOS/Linux）

**監控目錄：**
- `backend/` - 後端程式碼
- `frontend/` - 前端程式碼
- `data/` - 資料檔案
- `docs/` - 文件

**忽略檔案：**
- `*.pyc`, `*.log`, `.DS_Store`
- `node_modules`, `.git`, `__pycache__`
- `*.tmp`

**使用方法：**
```bash
./scripts/watch_deploy.sh [選項]

選項：
  -d, --debounce TIME  防抖時間（秒，預設: 5）
  -h, --help           顯示說明
```

**範例：**
```bash
# 基本使用
./scripts/watch_deploy.sh

# 設置防抖時間為 10 秒
./scripts/watch_deploy.sh -d 10
```

### setup.sh - 環境設置腳本

**功能特色：**
- 🔧 自動檢測作業系統
- 📦 安裝必要依賴
- 🐍 設置 Python 虛擬環境
- 🔑 配置腳本執行權限
- ✅ 檢查 Git 配置

**安裝內容：**
- **macOS**: fswatch（透過 Homebrew）
- **Linux**: inotify-tools（透過 apt/yum/dnf）
- **Python**: 虛擬環境和後端依賴
- **權限**: 腳本執行權限

## 🎯 使用場景

### 1. 開發期間的自動部署
```bash
# 在開發時啟動監控，每次儲存檔案都會自動部署
npm run deploy:watch
```

### 2. 功能完成後的手動部署
```bash
# 完成一個功能後手動觸發部署
npm run deploy -m "feat: implement user authentication"
```

### 3. 緊急修復的快速部署
```bash
# 緊急修復，跳過測試快速部署
SKIP_TESTS=true npm run deploy:force -m "hotfix: critical security patch"
```

### 4. 定期維護部署
```bash
# 定期更新，強制重新部署
npm run deploy:force -m "chore: maintenance deployment"
```

## ⚙️ 環境變數配置

在專案根目錄或 shell 配置檔案中設置：

```bash
# 跳過測試執行
export SKIP_TESTS=true

# 跳過部署狀態監控
export MONITOR_DEPLOYMENT=false

# 自訂防抖時間
export DEBOUNCE_TIME=10
```

## 🔧 故障排除

### 1. fswatch/inotify-tools 未安裝
```bash
# macOS
brew install fswatch

# Ubuntu/Debian
sudo apt-get install inotify-tools

# CentOS/RHEL
sudo yum install inotify-tools
```

### 2. 權限錯誤
```bash
# 重新設置權限
chmod +x scripts/*.sh
```

### 3. Git 配置錯誤
```bash
# 設置 Git 用戶信息
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 4. Python 虛擬環境問題
```bash
# 重新創建虛擬環境
cd backend
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 📊 部署狀態監控

腳本會自動監控以下部署平台：

- **GitHub Actions**: https://github.com/jacky6063/SEARCH_Goods/actions
- **Render 控制台**: https://dashboard.render.com/
- **Netlify 控制台**: https://app.netlify.com/

## 💡 最佳實踐

1. **開發時使用監控模式**：`npm run deploy:watch`
2. **重要變更使用手動部署**：`npm run deploy -m "descriptive message"`
3. **緊急修復跳過測試**：`SKIP_TESTS=true npm run deploy:force`
4. **定期檢查部署狀態**：關注 GitHub Actions 和部署平台日誌
5. **使用語義化提交訊息**：便於追蹤和回滾

## 🆘 支援

如遇到問題，請檢查：
1. 腳本執行權限：`ls -la scripts/`
2. 依賴安裝狀態：重新執行 `./scripts/setup.sh`
3. GitHub Actions 日誌：查看具體錯誤訊息
4. 環境變數配置：確認必要的環境變數已設置