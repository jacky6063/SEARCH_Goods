# 管理版面使用指南

## 📋 概述

SEARCH_Goods 提供了一個管理版面，用於上傳和管理商品數據 CSV 檔案。本指南將指導你如何使用它。

---

## 🔓 開啟管理版面

### 方式 1：通過按鈕（推薦）

在前端頁面右下角找到 **"⚙️ 管理版面"** 按鈕，點擊即可展開管理控制面板。

### 方式 2：通過快捷鍵

- **快捷鍵**: `Ctrl+Shift+M` (Windows) 或 `Cmd+Shift+M` (Mac)
- 立即展開管理版面

---

## 📤 上傳 CSV 檔案步驟

### 前置要求

在上傳前，確保以下條件滿足：

1. **後端服務運行**
   - 確保後端已啟動（通常 `http://localhost:8000`）
   - 檢查 .env 文件中 `ALLOW_DEV_ADMIN=1` 已設置（開發模式）

2. **CSV 檔案格式**
   - 文件名: `VIEW_GOODS_enhanced.csv`
   - 編碼: UTF-8
   - 包含必要欄位（見下方）

### 必要欄位

CSV 文件必須包含以下欄位（按優先順序）：

| 欄位名 | 類型 | 說明 |
|-------|------|------|
| `GoodIden` | 字符 | 商品編號（唯一標識符）|
| `Name` / `商品名稱` | 字符 | 商品名稱 |
| `CateName` / `分類名稱` | 字符 | 商品分類 |
| `REMARK` | 字符 | 商品標籤（如"男鞋"、"女鞋"等）|
| `Price` | 數字 | 商品價格 |
| `SpecialPrice` | 數字 | 特價（可選） |
| `SpecialOffer` | 字符 | 特價標記（可選） |

### 上傳步驟

1. **打開管理版面**
   - 點擊 "⚙️ 管理版面" 按鈕

2. **選擇 CSV 檔案**
   - 點擊 "選擇檔案" 按鈕
   - 在文件選擇對話框中選擇 `VIEW_GOODS_enhanced.csv`

3. **檢查上傳提示**
   - 狀態欄應顯示 "已選擇檔案" 或檔案名

4. **執行上傳**
   - 點擊 "上傳 CSV" 按鈕
   - 等待上傳完成（通常 1-5 秒）

5. **確認成功**
   - 狀態欄應顯示 "上傳成功: ok"
   - 頁面會自動清除快取並重新加載數據

---

## 🔧 開發環境配置

### 啟用開發者模式

編輯 `backend/.env` 文件，添加以下配置：

```env
# === 管理端點設定 ===
ALLOW_DEV_ADMIN=1
# ADMIN_TOKEN=your_secure_token_here  # 生產環境請設置
```

**ALLOW_DEV_ADMIN=1** 的含義：
- ✅ 在開發環境中繞過 token 驗證
- ✅ 允許任何人上傳 CSV
- ❌ **只在開發環境使用！** 生產環境必須設置 ADMIN_TOKEN

### 生產環境配置

生產環境中，**必須**設置強隨機的 ADMIN_TOKEN：

```env
# 生產環境 - 使用強隨機 token
ALLOW_DEV_ADMIN=0
ADMIN_TOKEN=your_very_secure_random_token_here_with_32_chars_min
```

Token 應該是：
- ✅ 至少 32 個字符
- ✅ 混合大小寫字母、數字、特殊字符
- ✅ 隨機生成
- ✅ 定期更換

**生成安全 Token 的方法**：
```bash
# Linux/Mac
openssl rand -base64 32

# Windows PowerShell
[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Random -SetSeed $null).ToString())) | ForEach-Object { $_ -replace '[^a-zA-Z0-9+/=]', 'x' }
```

---

## ❌ 常見問題

### 1. 上傳失敗：403 Forbidden

**原因**: ADMIN_TOKEN 未配置，且 ALLOW_DEV_ADMIN 未啟用

**解決**:
```bash
# 檢查 .env 文件
cat backend/.env | grep -i "allow_dev_admin\|admin_token"

# 添加以下行
echo "ALLOW_DEV_ADMIN=1" >> backend/.env

# 重新啟動後端
# (Ctrl+C 停止，然後重新運行 uvicorn)
```

### 2. 上傳失敗：401 Unauthorized

**原因**: 提供的 token 不正確（生產環境）

**解決**:
- 檢查 localStorage 中保存的 token 是否正確
- 在管理版面中重新輸入正確的 token
- 點擊 "保存 Token" 按鈕

### 3. 上傳後數據未更新

**原因**: 快取未清除

**解決**:
1. 點擊管理版面中的 "清除快取" 按鈕
2. 刷新瀏覽器 (F5)
3. 重新查詢商品

### 4. 無法選擇檔案

**原因**: 前端表單未正確渲染

**解決**:
- 清除瀏覽器快取: `Ctrl+Shift+Delete`
- 硬重載頁面: `Ctrl+Shift+R` (Windows) 或 `Cmd+Shift+R` (Mac)

### 5. 上傳成功但檔案未改變

**原因**: 
- CSV 格式不正確
- 欄位名稱不符
- 文件編碼錯誤

**解決**:
1. 檢查 CSV 文件編碼是否為 UTF-8
2. 驗證所有必要欄位都存在
3. 檢查檔案大小是否 > 0
4. 查看後端日誌尋求更多信息

---

## 📊 CSV 檔案範例

### 最小必需格式

```csv
GoodIden,Name,CateName,REMARK,Price
001,ADIDAS Alphacomfy 慢跑鞋,慢跑鞋,男鞋 黑 白 緩衝 透氣 運動鞋 愛迪達,3500
002,NIKE Nike Jordan Tatum 2 籃球鞋,籃球鞋,籃球鞋 運動 實戰 球鞋 訓練 耐磨 白灰黑,4200
003,掀蓋式專利頭層牛皮自動皮帶,男用皮帶,男用皮帶 真皮 自動扣,1200
```

### 完整格式

```csv
GoodIden,Name,CateName,REMARK,Price,SpecialPrice,SpecialOffer
001,ADIDAS Alphacomfy 慢跑鞋,慢跑鞋,男鞋 黑 白 緩衝 透氣 運動鞋 愛迪達,3500,3150,優惠中
002,NIKE Nike Jordan Tatum 2 籃球鞋,籃球鞋,籃球鞋 運動 實戰 球鞋 訓練 耐磨 白灰黑,4200,,
003,掀蓋式專利頭層牛皮自動皮帶,男用皮帶,男用皮帶 真皮 自動扣,1200,999,特價
```

---

## 🔐 安全建議

### 開發環境

✅ **可以使用** `ALLOW_DEV_ADMIN=1`：
- 本地開發機
- 內部開發網絡
- 測試環境（封閉網絡）

❌ **不要使用** 於生產環境

### 生產環境

✅ **必須**：
- 設置強隨機 ADMIN_TOKEN
- 使用 HTTPS 連接
- 定期輪換 token
- 監控上傳日誌
- 限制 IP 訪問
- 備份原始 CSV 文件

❌ **不要**：
- 使用弱密碼
- 將 token 放在代碼中
- 在公開網絡上使用
- 與他人分享 token

---

## 📝 API 詳情（技術參考）

### 上傳 CSV 端點

```
POST /api/admin/upload-csv
```

**請求頭**:
```
x-admin-token: [your-admin-token]  (開發模式可省略)
```

**請求體** (multipart/form-data):
```
file: [CSV 檔案]
```

**成功響應** (200):
```json
{
  "status": "ok",
  "message": "uploaded and replaced csv"
}
```

**錯誤響應**:
- `400 Bad Request`: 檔案為空
- `401 Unauthorized`: Token 不正確
- `403 Forbidden`: 管理端點已禁用
- `500 Internal Server Error`: 處理錯誤

### 清除快取端點

```
POST /api/admin/clear-cache
```

**請求頭**:
```
x-admin-token: [your-admin-token]  (開發模式可省略)
```

**成功響應** (200):
```json
{
  "status": "ok",
  "message": "cache cleared"
}
```

---

## 💡 使用提示

1. **定期備份**: 上傳新 CSV 前，務必備份現有檔案
2. **測試驗證**: 在小規模測試後再上傳完整數據
3. **監控日誌**: 查看後端日誌了解上傳詳情
4. **分批更新**: 對於大型數據集，考慮分批上傳
5. **版本控制**: 在 Git 中跟蹤 CSV 版本歷史

---

## 📞 故障排除

如果遇到問題，請檢查以下信息：

1. **後端日誌**
   ```bash
   # 查看最近 50 行日誌
   tail -50 backend.log
   ```

2. **瀏覽器控制台**
   - 打開: F12 或右鍵 → 檢查
   - 查看 "Console" 標籤的錯誤信息

3. **網絡請求**
   - 打開: F12 → Network 標籤
   - 上傳 CSV
   - 查看 `/api/admin/upload-csv` 請求的狀態和響應

4. **.env 檔案驗證**
   ```bash
   # 確認設置
   grep -E "ALLOW_DEV_ADMIN|ADMIN_TOKEN|DATA_PATH" backend/.env
   ```

---

## ✅ 完成檢查清單

上傳前，確保：

- [ ] 後端服務正在運行
- [ ] `.env` 已配置 `ALLOW_DEV_ADMIN=1` (開發) 或 `ADMIN_TOKEN` (生產)
- [ ] CSV 檔案編碼為 UTF-8
- [ ] CSV 檔案包含所有必要欄位
- [ ] CSV 檔案大小 > 0
- [ ] 網絡連接正常
- [ ] 沒有防火牆/代理阻擋

上傳後，確保：

- [ ] 狀態提示顯示 "上傳成功"
- [ ] 後端日誌無錯誤
- [ ] 清除快取成功
- [ ] 頁面重新加載正常
- [ ] 新商品數據已顯示

---

**最後更新**: 2025年11月4日
**版本**: 1.0
