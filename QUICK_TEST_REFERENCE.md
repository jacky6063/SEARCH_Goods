# 🧪 本地測試環境 - 快速參考

## ⚡ 快速啟動

```bash
# 啟動測試環境
./scripts/test_local.sh

# 啟動並自動測試
./scripts/test_local.sh --test
```

## 🎯 常用指令

```bash
# 執行所有測試
./scripts/quick_test.sh all

# 只執行 E2E 測試
./scripts/quick_test.sh e2e

# 只執行後端測試
./scripts/quick_test.sh backend

# 查看後端日誌
tail -f logs/backend.log

# 查看前端日誌
tail -f logs/frontend.log
```

## 🌐 服務端點

| 服務 | URL | 說明 |
|------|-----|------|
| 前端 | http://localhost:5173 | 使用者介面 |
| 後端 API | http://localhost:8000 | REST API |
| API 文檔 | http://localhost:8000/docs | Swagger UI |
| 健康檢查 | http://localhost:8000/health | Health check |

## 🛑 停止服務

```bash
# 停止所有服務
pkill -f uvicorn
pkill -f "python.*http.server"

# 或使用 Ctrl+C 停止 test_local.sh
```

## 🔧 故障排除

```bash
# 端口被佔用
lsof -i :8000  # 檢查後端
lsof -i :5173  # 檢查前端

# 殺掉佔用的進程
kill -9 $(lsof -t -i:8000)
kill -9 $(lsof -t -i:5173)

# 清理測試產物
rm -rf logs/*.log playwright-report test-results
```

## 📊 測試結果

**最後測試：** 2025-11-10 19:23

```
✅ 139 個測試通過
⚠️  37 個警告（可忽略）
⏱️  執行時間：8.91 秒
```

---

**完整文檔：** [docs/LOCAL_TEST_ENVIRONMENT.md](./LOCAL_TEST_ENVIRONMENT.md)
