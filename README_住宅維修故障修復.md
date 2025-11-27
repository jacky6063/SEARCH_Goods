# 住宅維修雲端故障診斷與修復套件

**問題**: 「馬桶嚴重堵塞」查詢在地端測試正常，雲端環境未觸發住宅維修模組  
**根本原因**: Render 環境變數 `ENABLE_REPAIR_SERVICE` 未設定  
**狀態**: 🔴 待修復 → ⏳ 修復中 → 🟢 已修復

---

## 📚 文件導航

### 🚑 立即修復 (< 5 分鐘)
**[快速診斷卡](🚑_快速診斷卡.md)** - 一頁紙問題確認與修復步驟

### 🔧 詳細修復指南
**[雲端修復步驟](🔧_住宅維修雲端修復步驟.md)** - 完整的 3 步驟修復教程，包含:
- Render Dashboard 操作截圖說明
- 瀏覽器驗證方法
- API 測試命令
- 常見問題 Q&A

### 🚨 技術診斷報告
**[未啟用診斷報告](🚨_住宅維修雲端未啟用診斷.md)** - 深度技術分析，包含:
- 根本原因分析
- 代碼層級檢查
- 環境對比表
- 預期修復效果

### ✅ 部署檢查清單
**[雲端部署檢查](✅_住宅維修雲端部署檢查.md)** - 完整檢查清單，包含:
- 逐步操作指引
- 測試案例表格
- 問題診斷樹狀圖
- 成功確認標準

### 📋 問題總結
**[問題總結報告](📋_住宅維修雲端問題總結.md)** - 綜合總結文件，包含:
- 地端 vs 雲端對比
- 建立的文件清單
- 預期效果展示
- 後續追蹤建議

### 🧪 測試工具
**[test_repair_cloud.py](test_repair_cloud.py)** - 自動化測試腳本，功能:
- 後端健康檢查
- 維修端點可用性測試
- 功能完整性驗證
- 詳細測試報告輸出

---

## ⚡ 快速開始（推薦流程）

### Step 1: 閱讀快速診斷卡
```bash
cat 🚑_快速診斷卡.md
```
→ 1 分鐘了解問題和解決方案

### Step 2: 執行修復
```
1. 登入 Render Dashboard
2. 設定環境變數: ENABLE_REPAIR_SERVICE=True
3. 觸發重新部署
```
→ 3 分鐘完成修復

### Step 3: 驗證修復
```bash
# 修改腳本中的後端網址
vim test_repair_cloud.py

# 執行測試
python3 test_repair_cloud.py
```
→ 1 分鐘自動化驗證

---

## 📊 文件使用場景

| 場景 | 推薦文件 | 預計時間 |
|------|---------|---------|
| 🚨 緊急修復 | 快速診斷卡 | 1 分鐘了解 + 5 分鐘修復 |
| 📖 完整教程 | 雲端修復步驟 | 10 分鐘學習 + 操作 |
| 🔬 深度分析 | 未啟用診斷報告 | 15 分鐘技術理解 |
| ✅ 部署驗證 | 雲端部署檢查 | 20 分鐘完整檢查 |
| 📝 團隊分享 | 問題總結報告 | 10 分鐘綜合了解 |
| 🧪 自動化測試 | test_repair_cloud.py | 2 分鐘執行驗證 |

---

## 🎯 修復流程圖

```
問題發現
    ↓
閱讀【快速診斷卡】← 1 分鐘
    ↓
執行【雲端修復步驟】← 3 分鐘
    ↓
運行【test_repair_cloud.py】← 1 分鐘
    ↓
成功？
 ├─ 是 → 完成 ✅
 └─ 否 → 閱讀【未啟用診斷報告】→ 深度排查
```

---

## 🔍 問題根本原因

### 代碼層級
```python
# backend/app.py Line 98
ENABLE_REPAIR_SERVICE = os.getenv("ENABLE_REPAIR_SERVICE", "False")

if ENABLE_REPAIR_SERVICE.lower() in ("1", "true", "yes"):
    # ✅ 載入維修模組
    from repair_search_service import search_repairs
    @app.post("/api/repair/chat")
    def repair_chat_endpoint(...): ...
else:
    # ❌ 跳過（雲端目前狀態）
    pass
```

### 環境差異
| 項目 | 地端 | 雲端 Render |
|------|------|-------------|
| 環境變數 | ✅ `.env`: `ENABLE_REPAIR_SERVICE=True` | ❌ **未設定** |
| 模組載入 | ✅ 正常 | ❌ 跳過 |
| API 端點 | ✅ `/api/repair/chat` (200) | ❌ 404 Not Found |

---

## ✅ 成功標準

修復完成後應滿足:

- [ ] Render 環境變數包含 `ENABLE_REPAIR_SERVICE=True`
- [ ] `test_repair_cloud.py` 測試 3/3 通過
- [ ] `/api/repair/chat` 返回 200（非 404）
- [ ] 瀏覽器測試顯示 🔧 維修建議（非 🛍️ 商品）
- [ ] 商品搜尋功能正常運作（向後相容）

---

## 🧪 測試案例

| 測試輸入 | 預期意圖 | 預期回應類型 | 預期圖示 |
|---------|---------|-------------|---------|
| 馬桶嚴重堵塞 | 維修 | 維修建議 | 🔧 |
| 水龍頭滴水 | 維修 | 維修建議 | 🔧 |
| 跳電維修 | 維修 | 維修建議 | 🔧 |
| 我要買椰子油 | 商品 | 商品推薦 | 🛍️ |
| 推薦堅果 | 商品 | 商品推薦 | 🛍️ |

---

## 📞 技術支援

### 如果修復後仍有問題

請收集以下資訊:

1. **Render 環境變數截圖**
   - Dashboard → Environment → 完整列表

2. **測試腳本輸出**
   ```bash
   python3 test_repair_cloud.py > test_output.txt 2>&1
   ```

3. **Render 部署日誌**
   - Dashboard → Logs → 最近 200 行

4. **瀏覽器 Console 截圖**
   - F12 → Console → 測試時的輸出

5. **API 回應範例**
   ```bash
   curl -X POST https://your-backend/api/repair/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "馬桶堵塞", "history": []}' \
     -v > api_response.txt 2>&1
   ```

---

## 🔗 相關資源

### 內部文件
- [維修服務完整文件](backend/REPAIR_SERVICE_README.md)
- [對話區路由設計](docs/對話區模型路由設計方案.md)
- [環境變數範例](backend/.env.example)

### 外部資源
- [Render 環境變數文件](https://render.com/docs/environment-variables)
- [FastAPI 條件性路由](https://fastapi.tiangolo.com/advanced/conditional-openapi/)

---

## 📝 版本記錄

| 日期 | 版本 | 變更 |
|------|------|------|
| 2025-11-11 | 1.0 | 初版建立 - 問題診斷與修復套件 |

---

## 🎉 預期結果

修復完成後的完整流程:

```
使用者: "馬桶嚴重堵塞"
    ↓
前端意圖識別 → 'repair' ✅
    ↓
路由到 /api/repair/chat ✅
    ↓
後端:
  - ✅ ENABLE_REPAIR_SERVICE=True
  - ✅ 載入維修模組
  - ✅ 搜尋維修資料
  - ✅ 返回維修建議
    ↓
前端顯示:
┌────────────────────────┐
│ 🔧 住宅維修建議         │
│                        │
│ 找到 2 個維修項目      │
│                        │
│ • 馬桶疏通             │
│   類別: 給排水         │
│   緊急度: 中           │
│   建議: 聯絡水電...    │
└────────────────────────┘
```

---

**建立日期**: 2025年11月11日  
**預計修復時間**: < 10 分鐘  
**文件完整性**: 6 個文件 + 1 個測試腳本  
**使用難度**: ⭐⭐☆☆☆ (簡單)
