# 🧪 本地測試環境使用指南

## 📋 目錄

1. [快速開始](#快速開始)
2. [測試環境架構](#測試環境架構)
3. [使用方式](#使用方式)
4. [故障排除](#故障排除)
5. [進階設定](#進階設定)

---

## 🚀 快速開始

### **方式 1: 使用測試腳本（推薦）**

```bash
# 啟動完整測試環境
./scripts/test_local.sh

# 啟動並自動執行測試
./scripts/test_local.sh --test
```

### **方式 2: 使用 Docker Compose**

```bash
# 啟動測試環境
docker-compose -f docker-compose.test.yml up

# 在背景執行
docker-compose -f docker-compose.test.yml up -d

# 停止環境
docker-compose -f docker-compose.test.yml down
```

### **方式 3: 手動啟動**

```bash
# 1. 啟動後端
cd backend
source .venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000 &

# 2. 啟動前端
cd ../frontend
python3 -m http.server 5173 &

# 3. 執行測試
npm run test:e2e
```

---

## 🏗️ 測試環境架構

```
┌─────────────────────────────────────────┐
│          本地測試環境                    │
├─────────────────────────────────────────┤
│                                          │
│  ┌──────────────┐    ┌──────────────┐  │
│  │   後端服務   │◄───┤   前端服務   │  │
│  │ Port 8000    │    │ Port 5173    │  │
│  └──────┬───────┘    └──────────────┘  │
│         │                                │
│         │ API 請求                       │
│         ▼                                │
│  ┌──────────────┐    ┌──────────────┐  │
│  │   資料檔案   │    │  測試套件    │  │
│  │   CSV 檔     │    │  E2E + Unit  │  │
│  └──────────────┘    └──────────────┘  │
│                                          │
└─────────────────────────────────────────┘
```

### **端口配置**

| 服務 | 端口 | 用途 |
|------|------|------|
| 後端 API | 8000 | 商品搜尋、聊天、管理 |
| 前端頁面 | 5173 | 使用者介面 |
| API 文檔 | 8000/docs | Swagger UI |

---

## 📖 使用方式

### **1. 執行特定測試**

```bash
# 只執行 E2E 測試
./scripts/quick_test.sh e2e

# 只執行後端測試
./scripts/quick_test.sh backend

# 執行所有測試
./scripts/quick_test.sh all
```

### **2. 監控日誌**

```bash
# 查看後端日誌
tail -f logs/backend.log

# 查看前端日誌
tail -f logs/frontend.log

# 同時查看兩個日誌
tail -f logs/*.log
```

### **3. 手動測試**

#### **測試後端 API**

```bash
# 健康檢查
curl http://localhost:8000/health

# 商品搜尋
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "有機米", "topn": 10}'

# 聊天功能
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "推薦有機米", "history": []}'
```

#### **測試前端頁面**

```bash
# 在瀏覽器中打開
open http://localhost:5173

# 或使用 curl 檢查
curl -I http://localhost:5173
```

### **4. 測試特定功能**

#### **測試管理面板**

```bash
# 啟動測試環境
./scripts/test_local.sh

# 在瀏覽器中打開並測試
open http://localhost:5173

# 點擊「管理」按鈕，測試：
# - API 端點設定
# - Logo/YouTube 設定
# - 語音模式開關
# - CSV 上傳功能
```

#### **測試語音功能**

```bash
# 確認語音模式已啟用
curl http://localhost:8000/api/branding | jq '.voice_mode_enabled'

# 在前端測試：
# 1. 點擊麥克風圖示
# 2. 說出查詢內容
# 3. 檢查是否正確轉換並搜尋
```

---

## 🔧 故障排除

### **問題 1: 後端啟動失敗**

```bash
# 檢查端口是否被佔用
lsof -i :8000

# 終止佔用端口的進程
kill -9 $(lsof -t -i:8000)

# 檢查 Python 虛擬環境
cd backend
source .venv/bin/activate
pip list | grep fastapi
```

### **問題 2: 前端無法訪問**

```bash
# 檢查端口是否被佔用
lsof -i :5173

# 終止佔用端口的進程
kill -9 $(lsof -t -i:5173)

# 檢查文件是否存在
ls -la frontend/index.html
```

### **問題 3: 測試失敗**

```bash
# 清除測試快取
rm -rf playwright-report test-results .pytest_cache

# 重新安裝測試依賴
npm install
cd backend && pip install -r requirements.txt

# 重新執行測試
./scripts/quick_test.sh all
```

### **問題 4: CSV 資料載入失敗**

```bash
# 檢查資料檔案
ls -lh data/VIEW_GOODS_enhanced.csv

# 檢查檔案格式
head -5 data/VIEW_GOODS_enhanced.csv

# 檢查後端日誌
grep "CSV" logs/backend.log
```

---

## ⚙️ 進階設定

### **1. 自訂端口**

編輯 `scripts/test_local.sh`：

```bash
# 修改後端端口（預設 8000）
python3 -m uvicorn app:app --port 8001

# 修改前端端口（預設 5173）
python3 -m http.server 5174
```

### **2. 啟用 Debug 模式**

```bash
# 後端 Debug 模式
cd backend
source .venv/bin/activate
uvicorn app:app --reload --log-level debug

# 前端 Debug（開啟瀏覽器開發工具）
# 按 F12 或 Cmd+Option+I
```

### **3. 測試覆蓋率報告**

```bash
# 後端測試覆蓋率
cd backend
pytest --cov=. --cov-report=html
open htmlcov/index.html

# E2E 測試報告
npm run test:e2e
npx playwright show-report
```

### **4. 性能測試**

```bash
# 使用 Apache Bench
ab -n 100 -c 10 http://localhost:8000/health

# 使用 wrk
wrk -t4 -c100 -d30s http://localhost:8000/health
```

---

## 📊 測試檢查清單

### **每次提交前**

- [ ] ✅ 執行 E2E 測試：`./scripts/quick_test.sh e2e`
- [ ] ✅ 執行後端測試：`./scripts/quick_test.sh backend`
- [ ] ✅ 檢查無 JavaScript 錯誤
- [ ] ✅ 檢查無 Python 錯誤
- [ ] ✅ 測試管理面板功能
- [ ] ✅ 測試搜尋功能
- [ ] ✅ 測試聊天功能

### **每週一次**

- [ ] ✅ 更新測試依賴：`npm update` 和 `pip list --outdated`
- [ ] ✅ 檢查測試覆蓋率
- [ ] ✅ 清理測試日誌：`rm -rf logs/*.log`
- [ ] ✅ 檢查 Docker 映像更新

---

## 🎯 快速指令參考

```bash
# 啟動測試環境
./scripts/test_local.sh

# 執行所有測試
./scripts/quick_test.sh all

# 查看後端日誌
tail -f logs/backend.log

# 查看前端日誌
tail -f logs/frontend.log

# 停止所有服務
pkill -f uvicorn
pkill -f "python.*http.server"

# 清理環境
rm -rf logs/*.log playwright-report test-results

# 重新啟動
./scripts/test_local.sh --test
```

---

## 📚 相關文檔

- [E2E 測試指南](./E2E_TEST_GUIDE.md)
- [後端測試指南](../backend/README.md#testing)
- [部署指南](./DEPLOYMENT_SETUP.md)
- [故障排除](./TROUBLESHOOTING.md)

---

## 💡 最佳實踐

1. **每次開發前**啟動測試環境
2. **頻繁執行測試**（建議每 30 分鐘）
3. **監控日誌**以便及時發現問題
4. **定期清理**測試產生的臨時文件
5. **保持測試更新**與代碼同步

---

**建立日期：** 2025-11-10  
**最後更新：** 2025-11-10  
**維護者：** GitHub Copilot
