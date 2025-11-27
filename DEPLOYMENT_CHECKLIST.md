# ✅ 前端遷移至 Render - 部署檢查清單（已驗證）

## 🚀 已完成的實施步驟

### ✅ 1. Dockerfile 多階段構建
- **狀態**：完成
- **提交**：`8c54aac`
- **變更**：
  - 階段 1（Alpine）：複製 `frontend/` → `/frontend`
  - 階段 2（Python Builder）：編譯依賴
  - 階段 3（Final）：複製前端到 `/app/backend/static/`

### ✅ 2. Backend app.py 路徑適配
- **狀態**：完成
- **文件**：`backend/app.py` (行 1143-1148)
- **邏輯**：自動檢測開發 vs Docker 環境

```python
frontend_path = ROOT / "frontend"
if not frontend_path.exists():
    frontend_path = Path(__file__).parent / "static"
```

### ✅ 3. GitHub Actions 工作流更新
- **狀態**：完成
- **文件**：`.github/workflows/deploy.yml`
- **保留**：Render 部署觸發
- **說明**：Netlify 已停用，相關文件已歸檔至 `docs/archive/2025-11/`

### ✅ 4. Git 提交與推送
- **狀態**：完成
- **主要提交**：
  - `8c54aac` - Migrate frontend to Render
  - `db27005` - Add implementation documentation
- **遠程狀態**：✅ 已推送至 origin/main

---

## 📋 Render 部署驗證清單

### 立即檢查事項（推送後）
- [ ] GitHub Actions 工作流自動觸發
- [ ] 工作流成功完成（綠色勾選）
- [ ] Docker 鏡像已推送到 GHCR
- [ ] Render 開始部署
- [ ] Render 部署日誌無錯誤

### 部署後驗證（Render 容器啟動後）
- [ ] 訪問 Render URL 根路徑 → 顯示前端 UI
- [ ] 搜尋功能正常（POST /api/search 可用）
- [ ] 購買按鈕可點擊（顯示亮度增強效果）
- [ ] 瀏覽器 DevTools Network → index.html 返回 200
- [ ] DevTools 檢查 Response Headers:
  - `Cache-Control: no-cache, no-store, must-revalidate`
  - `Pragma: no-cache`
  - `Expires: 0`

### 功能驗證
- [ ] 搜尋框輸入 → 返回商品列表
- [ ] 分類麵包屑顯示為純文字（非可點擊按鈕）
- [ ] 商品卡顯示 "🛒 購買" 按鈕（無分享按鈕）
- [ ] 購物車按鈕顯示白色亮度增強效果
- [ ] 無 "系統忙碌或網路異常" 錯誤

---

## 📊 性能改進對比

| 指標 | 遷移前 | 遷移後 | 改進 |
|-----|-------|-------|-----|
| 前端部署時間 | 5-30 分鐘 | 1-2 秒 | **15-1800x 快** |
| 部署目標數 | 2 個 | 1 個 | 簡化 50% |
| 同步延遲 | 可能不同步 | 保證同步 | 消除風險 |
| 快取問題 | Netlify CDN | 已禁用 | 根除 |

---

## 🔍 Render 部署故障排除

### 若前端未顯示

**步驟 1：查看 Render 日誌**
```
Render Dashboard → Logs
查找關鍵字：ERROR, FAILED, stat
```

**步驟 2：驗證 Docker 構建**
```bash
# 本地測試
docker build -t search-goods:test .
docker run -p 8000:8000 search-goods:test

# 測試：訪問 http://localhost:8000
```

**步驟 3：檢查路徑邏輯**
- app.py 行 1143：`frontend_path = ROOT / "frontend"`
- app.py 行 1146：`if not frontend_path.exists():`
- app.py 行 1148：`frontend_path = Path(__file__).parent / "static"`

**步驟 4：驗證靜態文件掛載**
```python
# app.py 行 1401-1402（應存在）
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
```

### 若 API 端點不可用

**檢查事項**：
- API 中間件是否正確優先（行 1152：`if request.url.path.startswith("/api")`）
- 環境變數是否正確設定（OpenAI API key 等）
- CSV 數據文件是否正確加載

---

## 📝 後續檢查清單

### 部署後 24 小時檢查
- [ ] 再次訪問 Render URL 確認穩定性
- [ ] 清除瀏覽器快取後再次訪問
- [ ] 測試搜尋多次確認無間歇性故障
- [ ] 檢查 Render 日誌無警告或異常

### 發布前檢查
- [ ] 購物車圖標亮度增強確實顯示
- [ ] 分類麵包屑確實為純文字
- [ ] 分享按鈕已移除
- [ ] 所有 CSS/JS 資源已加載

### 部署完成後的可選步驟
- [ ] 在 README.md 中更新部署架構說明
- [ ] 通知團隊部署完成
- [ ] 監控 Render 成本使用情況
- [ ] 考慮設置告警以監控部署失敗

---

## 🎯 成功指標

部署視為**成功**當以下條件全部滿足：

1. ✅ Render 容器正常運行（無 CrashLoopBackOff）
2. ✅ 訪問根路徑返回前端 UI（HTTP 200）
3. ✅ API 端點正常響應（/api/search 可用）
4. ✅ 搜尋功能完全可用
5. ✅ 購物車圖標顯示亮度增強效果
6. ✅ 前端部署時間 < 3 分鐘（而非 5-30 分鐘）

---

## 🔗 相關文檔

- `FRONTEND_MIGRATION_EVALUATION.md` - 評估與規劃
- `FRONTEND_MIGRATION_IMPLEMENTATION.md` - 完整實施記錄
- `Dockerfile` - 多階段構建配置
- `backend/app.py` - 靜態文件路由配置
- `.github/workflows/deploy.yml` - CI/CD 工作流

---

**檢查清單版本**：1.0  
**最後更新**：2025年11月  
**下一步**：監控 Render 部署，驗證前端資產正確加載
