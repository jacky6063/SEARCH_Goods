# 🔍 上傳失敗診斷報告

**診斷日期**: 2025年11月4日  
**狀態**: ⚠️ 已識別多個可能原因

---

## ❌ 無法上傳的原因分析

### 原因 1️⃣：後端服務未運行 ⚠️ **最可能**

**症狀**:
- 管理版面顯示錯誤
- 上傳按鈕無反應
- 網絡請求超時

**驗證**:
```bash
# 檢查後端是否運行
ps aux | grep uvicorn

# 結果: 空 (未運行)
```

**解決方案**:

```bash
# 1. 進入後端目錄
cd /Users/huangchangchi/Documents/SEARCH_Goods/backend

# 2. 啟動後端服務
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 預期輸出:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

---

### 原因 2️⃣：瀏覽器快取

**症狀**:
- 後端已啟動，但前端還是顯示舊配置
- 管理版面加載不正常

**解決方案**:

```
按 Ctrl+Shift+Delete 打開快取清除對話框
選擇：
  - 時間範圍: 所有時間
  - Cookie: ✓
  - 快取: ✓
點擊 "清除數據"
```

**或硬重載頁面**:
- Windows: `Ctrl+Shift+R`
- Mac: `Cmd+Shift+R`

---

### 原因 3️⃣：ALLOW_DEV_ADMIN 未生效

**症狀**:
- 後端已啟動
- 管理版面要求輸入 token

**可能原因**:
- 後端啟動時沒有重新讀取 .env
- .env 文件格式錯誤

**驗證**:
```bash
# 檢查 .env 內容
grep ALLOW_DEV_ADMIN backend/.env
# 應該輸出: ALLOW_DEV_ADMIN=1
```

**解決方案**:

```bash
# 停止後端 (Ctrl+C)
# 確認 .env 正確:
cat backend/.env | head -20

# 重新啟動後端
uvicorn app:app --reload
```

---

### 原因 4️⃣：CSV 檔案路徑錯誤

**症狀**:
- 上傳成功但數據未更新
- 後端日誌顯示路徑錯誤

**驗證**:
```bash
# 檢查 CSV 檔案
ls -lh data/VIEW_GOODS_enhanced.csv
# 應該輸出: -rw-rw-r--@ 1 ... 1.1M
```

**檢查結果**: ✅ CSV 檔案存在且正常 (1.1M)

---

### 原因 5️⃣：CSV 檔案編碼

**症狀**:
- 上傳時顯示"檔案處理錯誤"
- 後端日誌出現 Unicode 錯誤

**驗證**:
```bash
file data/VIEW_GOODS_enhanced.csv
# 應該輸出: ... text
```

**檢查結果**: ✅ 檔案編碼正常 (CSV text)

---

## 🚀 快速修復步驟

### 步驟 1：啟動後端

```bash
cd /Users/huangchangchi/Documents/SEARCH_Goods/backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**看到以下輸出表示成功**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 步驟 2：驗證後端運行

打開新終端：
```bash
curl http://localhost:8000/health
# 應該返回: {"status":"ok"}
```

### 步驟 3：清除瀏覽器快取

- 按 `Ctrl+Shift+Delete` (Windows) 或 `Cmd+Shift+Delete` (Mac)
- 清除所有快取數據
- 重新加載頁面

### 步驟 4：訪問前端

```
http://localhost:5173
```

**或**

```
http://localhost:8000  (如果前端託管在後端)
```

### 步驟 5：上傳 CSV

1. 點擊 "⚙️ 管理版面"
2. 選擇 CSV 檔案
3. 點擊 "上傳 CSV"
4. 看到 "上傳成功" 提示

---

## 📋 檢查清單

上傳前確保：

- [ ] 後端服務正在運行 (`uvicorn app:app --reload`)
- [ ] 可以訪問 `http://localhost:8000/health` (返回 200)
- [ ] 瀏覽器快取已清除
- [ ] CSV 檔案存在且大小 > 0
- [ ] `.env` 中 `ALLOW_DEV_ADMIN=1` 已設置
- [ ] 沒有防火牆阻擋 8000 端口

上傳後確保：

- [ ] 看到 "上傳成功" 提示
- [ ] 後端日誌無錯誤
- [ ] 新商品數據已顯示
- [ ] 查詢功能正常

---

## 🔧 進階故障排查

### 查看後端日誌

```bash
# 後端輸出應包含上傳日誌：
# received upload from 127.0.0.1 size=1234567
# replaced data file at .../data/VIEW_GOODS_enhanced.csv
# cache cleared
```

### 檢查瀏覽器控制台

1. 打開 F12 (開發者工具)
2. 進入 "Console" 標籤
3. 上傳 CSV
4. 查看是否有 JavaScript 錯誤

### 檢查網絡請求

1. 打開 F12 (開發者工具)
2. 進入 "Network" 標籤
3. 上傳 CSV
4. 找 `/api/admin/upload-csv` 請求
5. 查看狀態碼和響應

**預期**:
- 狀態碼: 200
- 響應: `{"status":"ok","message":"uploaded and replaced csv"}`

### 檢查 .env 格式

```bash
cat backend/.env | head -15

# 應該看到:
# DATA_PATH=../data/VIEW_GOODS_enhanced.csv
# ALLOW_DEV_ADMIN=1
```

---

## 💡 常見錯誤

| 錯誤信息 | 原因 | 解決方案 |
|---------|------|---------|
| 連接被拒絕 | 後端未運行 | 啟動 uvicorn |
| 403 Forbidden | token 驗證失敗 | 重啟後端使 .env 生效 |
| 401 Unauthorized | token 不正確 | 生成新 token (生產環境) |
| 400 Bad Request | 檔案為空 | 確保上傳非空 CSV |
| 500 Internal Error | 處理錯誤 | 查看後端日誌 |
| 上傳成功但無效 | 路徑或權限問題 | 檢查 `data/` 目錄權限 |

---

## ✨ 完整工作流

```
1. 啟動後端
   ↓
2. 清除瀏覽器快取
   ↓
3. 訪問前端管理版面
   ↓
4. 點擊 "⚙️ 管理版面"
   ↓
5. 選擇 CSV 檔案
   ↓
6. 點擊 "上傳 CSV"
   ↓
7. 看到 "上傳成功"
   ↓
✅ 完成！數據已更新
```

---

## 📞 如果仍然無法上傳

請收集以下信息：

1. **後端日誌**
   ```bash
   # 複製完整的後端輸出
   ```

2. **瀏覽器控制台錯誤**
   - 打開 F12 → Console
   - 複製錯誤信息

3. **網絡請求詳情**
   - 打開 F12 → Network
   - 上傳後尋找 `/api/admin/upload-csv` 請求
   - 複製 Status 和 Response

4. **系統信息**
   ```bash
   echo $HOME
   ls -lh backend/.env
   ls -lh data/VIEW_GOODS_enhanced.csv
   ```

---

**最後更新**: 2025年11月4日  
**版本**: 1.0
