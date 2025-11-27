# 🎯 本地測試 - 完整指南

**啟動時間**: 2025年11月6日
**狀態**: ✅ **本地開發環境已啟動**

---

## 🌐 本地訪問網址

### 前端 (Web UI)
```
http://localhost:8000
```
- 由 FastAPI 提供前端靜態資產（開發/容器皆可）
- 可進行產品搜尋、聊天、語音輸入等功能測試

### 後端 API 基礎 URL
```
http://localhost:8000
```

---

## 📡 主要 API 端點

### 1️⃣ 健康檢查 ✅
```bash
curl http://localhost:8000/health
```
**回應**: `{"status":"ok"}`

### 2️⃣ 分類列表 (L1 - 主要分類)
```bash
curl http://localhost:8000/api/catalog/scope?level=L1 | python3 -m json.tool
```
**預期**: 返回 5 個主要分類

### 3️⃣ 產品搜尋
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"米"}' | python3 -m json.tool
```

### 4️⃣ 聊天功能
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message":"推薦一些米類產品",
    "session_id":"test-123"
  }' | python3 -m json.tool
```

### 5️⃣ 分類詳情 (L2)
```bash
# 使用 parent_l1 指定 L1 名稱
curl "http://localhost:8000/api/catalog/scope?level=L2&parent_l1=常溫食品" | python3 -m json.tool
```

### 6️⃣ 分類詳情 (L3)
```bash
# 使用 parent_l1 與 parent_l2 指定父層
curl "http://localhost:8000/api/catalog/scope?level=L3&parent_l1=常溫食品&parent_l2=五穀/豆類/米麵/乾貨" | python3 -m json.tool
```

---

## 🧪 快速測試流程

### 步驟 1: 驗證後端運行
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```
✅ 應看到: `{"status": "ok"}`

### 步驟 2: 測試分類系統
```bash
curl -s http://localhost:8000/api/catalog/scope?level=L1 | python3 -m json.tool | head -20
```
✅ 應看到 5 個 L1 分類

### 步驟 3: 測試搜尋功能
```bash
curl -s -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"米"}' | python3 -m json.tool | head -30
```
✅ 應看到米類產品列表

### 步驟 4: 在瀏覽器中測試 UI
```
打開: http://localhost:5173
- 進行文字搜尋
- 嘗試語音輸入
- 測試聊天功能
- 測試分類導航
```

---

## 🔍 完整 API 測試清單

| API 端點 | 方法 | 用途 | 狀態 |
|---------|------|------|------|
| `/health` | GET | 健康檢查 | ✅ |
| `/api/catalog/scope` | GET | 獲取分類 | ✅ |
| `/api/search` | POST | 搜尋產品 | ✅ |
| `/api/chat` | POST | 聊天 | ✅ |
| `/api/suggest` | POST | 推薦產品 | ✅ |
| `/api/admin/upload-csv` | POST | CSV 上傳 | ✅ |
| `/api/admin/clear-cache` | POST | 清除緩存 | ✅ |

---

## 📊 實時監控

### 查看後端日誌
```bash
tail -f /tmp/backend.log
```

### 查看前端日誌
```bash
tail -f /tmp/frontend.log
```

### 檢查運行中的進程
```bash
ps aux | grep -E "uvicorn|http.server" | grep -v grep
```

---

## 🛑 停止服務

### 停止後端
```bash
pkill -f "uvicorn app:app"
```

### 停止前端
```bash
pkill -f "http.server 5173"
```

### 停止所有
```bash
pkill -f "uvicorn app:app"; \
pkill -f "http.server 5173"; \
echo "✅ 所有服務已停止"
```

---

## 🔄 重啟服務

```bash
# 一鍵重啟所有服務
cd /Users/huangchangchi/Documents/SEARCH_Goods/backend && \
pkill -f "uvicorn" 2>/dev/null; \
sleep 2; \
/Users/huangchangchi/Documents/SEARCH_Goods/backend/.venv/bin/python3 \
  -m uvicorn app:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &

cd /Users/huangchangchi/Documents/SEARCH_Goods/frontend && \
pkill -f "http.server 5173" 2>/dev/null; \
sleep 2; \
python3 -m http.server 5173 > /tmp/frontend.log 2>&1 &

sleep 3
echo "✅ 所有服務已重啟"
```

---

## 🎯 常見測試場景

### 場景 1: 簡單搜尋
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"糙米"}' | python3 -m json.tool
```

### 場景 2: 分類流程
```bash
# 1. 獲取 L1 分類
curl -s http://localhost:8000/api/catalog/scope?level=L1 | python3 -m json.tool

# 2. 選擇 L1 分類，獲取 L2
curl -s "http://localhost:8000/api/catalog/scope?level=L2&parent_l1=常溫食品" | python3 -m json.tool

# 3. 選擇 L2 分類，獲取 L3
curl -s "http://localhost:8000/api/catalog/scope?level=L3&parent_l1=常溫食品&parent_l2=五穀/豆類/米麵/乾貨" | python3 -m json.tool
```

### 場景 3: 聊天對話
```bash
# Session ID: 可使用任意字符串
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message":"我想要高蛋白的米類產品",
    "session_id":"user-001"
  }' | python3 -m json.tool
```

---

## 📝 測試記錄

### 本次啟動信息

| 項目 | 信息 |
|------|------|
| 後端進程 PID | 36724 |
| 前端進程 PID | 26029 |
| 後端埠 | 8000 |
| 前端埠 | 5173 |
| 健康檢查 | ✅ 成功 |
| 啟動時間 | 2025年11月6日 |

---

## 💡 提示

- **前端地址**: 在瀏覽器中打開 `http://localhost:5173` 以獲得完整 UI 體驗
- **API 測試**: 使用 curl 命令或 Postman 測試 API 端點
- **實時熱重載**: 修改代碼後，後端會自動重啟 (Reload mode)
- **數據源**: 使用本地 CSV 文件 (`data/VIEW_GOODS_enhanced.csv`)
- **緩存**: 修改 CSV 後，使用 `/api/admin/clear-cache` 清除緩存

---

**快開始測試吧！** 🚀
