# 管理版面 CSV 上傳 - 解決方案

**日期**: 2025年11月4日  
**狀態**: ✅ 已解決  
**問題**: 無法通過管理版面上傳 VIEW_GOODS_enhanced.csv 到 data 目錄

---

## 🎯 問題分析

你遇到的問題是管理版面上傳功能需要**管理員認證**。系統有兩種模式：

| 模式 | 狀態 | 需要 Token | 場景 |
|------|------|-----------|------|
| **開發模式** | ✅ 已啟用 | ❌ 不需要 | 本地開發 |
| **生產模式** | ❌ 未啟用 | ✅ 需要 | 生產部署 |

---

## ✅ 解決方案（已實施）

### 1️⃣ 啟用開發模式

**文件**: `backend/.env`

```env
# 開發模式：繞過 token 檢查，允許直接上傳 CSV
ALLOW_DEV_ADMIN=1
```

**效果**:
- ✅ 不需要輸入管理員 token
- ✅ 直接點擊上傳即可
- ✅ 無需額外配置

### 2️⃣ 驗證配置

```bash
# 確認設置
cat backend/.env | grep ALLOW_DEV_ADMIN
# 輸出: ALLOW_DEV_ADMIN=1
```

### 3️⃣ 重啟後端服務

```bash
# 停止後端 (Ctrl+C)
# 重新啟動
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

---

## 📤 如何上傳 CSV

### 操作步驟

1. **打開前端頁面**
   - 訪問 `http://localhost:5173` (前端)

2. **點擊管理版面按鈕**
   - 在右下角找到 "⚙️ 管理版面" 按鈕
   - 點擊展開管理控制面板

3. **選擇 CSV 檔案**
   - 點擊 "選擇檔案" 按鈕
   - 選擇 `VIEW_GOODS_enhanced.csv`

4. **上傳檔案**
   - 點擊 "上傳 CSV" 按鈕
   - 等待 1-5 秒

5. **確認成功**
   - 狀態欄顯示: "上傳成功: uploaded and replaced csv"
   - 頁面自動清除快取
   - 新商品數據已更新

### 視覺流程

```
前端頁面
  ↓
點擊 "⚙️ 管理版面"
  ↓
展開管理控制面板
  ↓
點擊 "選擇檔案"
  ↓
選擇 CSV 檔案
  ↓
點擊 "上傳 CSV"
  ↓
後端驗證 (ALLOW_DEV_ADMIN=1)
  ↓
原子性替換檔案
  ↓
清除快取
  ↓
返回成功
  ↓
前端顯示 "上傳成功"
```

---

## 🔍 技術細節

### 上傳流程

```python
# app.py 中的上傳端點
@app.post("/api/admin/upload-csv")
def admin_upload_csv(file: UploadFile, x_admin_token: Optional[str]):
    # 1. 檢查認證
    _check_admin(x_admin_token)
    
    # 2. 寫入臨時檔案
    with tempfile.NamedTemporaryFile(dir=DATA_PATH.parent) as tmp:
        shutil.copyfileobj(file.file, tmp)
    
    # 3. 原子性替換
    os.replace(tmp_path, DATA_PATH)
    
    # 4. 清除快取
    catalog_service.reset()
    load_goods_rows(refresh=True)
    
    # 5. 返回成功
    return {"status": "ok"}
```

### 檔案位置

- **上傳目標**: `/Users/huangchangchi/Documents/SEARCH_Goods/data/VIEW_GOODS_enhanced.csv`
- **臨時目錄**: `data/` (與目標相同目錄，保證原子性)
- **快取清除**: 自動清除內存中的 DataFrame

### 安全特性

- ✅ **原子性**: 使用 `os.replace()` 保證交易一致性
- ✅ **驗證**: 檢查檔案大小 > 0
- ✅ **快取清除**: 上傳後自動重新加載
- ✅ **日誌記錄**: 所有上傳記錄
- ✅ **錯誤處理**: 失敗時清理臨時檔案

---

## 🔐 安全考慮

### 開發環境 ✅

配置已啟用：
```env
ALLOW_DEV_ADMIN=1
```

- 適用於: 本地開發、內部測試
- 繞過 token 驗證
- 任何人都可以上傳

### 生產環境 ⚠️

**必須更改配置**：

```env
# 關閉開發模式
ALLOW_DEV_ADMIN=0

# 設置強隨機 token
ADMIN_TOKEN=your_very_secure_random_token_here_min_32_chars
```

**生成安全 Token**:
```bash
# Linux/Mac
openssl rand -base64 32

# 示例輸出
aB3c+D/E5FgHiJkLmNoPqRsTuVwXyZ1234567890ABC=
```

### 生產部署步驟

1. 生成強隨機 token
2. 設置環境變數 `ADMIN_TOKEN`
3. 禁用 `ALLOW_DEV_ADMIN`
4. 在前端管理面板中輸入 token
5. 點擊 "保存 Token"（存儲到 localStorage）
6. 後續上傳自動使用保存的 token

---

## ✨ 新增功能和改進

### 1. 管理指南

文件: `ADMIN_GUIDE.md`

包含以下內容：
- 📋 詳細使用說明
- 📤 分步上傳指南
- 🔧 開發/生產配置
- ❌ 常見問題排查
- 📊 CSV 格式範例
- 🔐 安全建議
- 📝 API 參考

### 2. 改進的 .env

新增配置：
```env
# === 管理端點設定 ===
ALLOW_DEV_ADMIN=1
# ADMIN_TOKEN=your_secure_token_here  # 生產環境
```

### 3. 自動快取清除

上傳後自動執行：
- ✅ 清除 DataFrame 快取
- ✅ 重新加載 CSV 檔案
- ✅ 刷新所有相關快取
- ✅ 無需手動操作

---

## 📋 CSV 檔案格式要求

### 必需欄位

| 欄位 | 類型 | 例子 | 說明 |
|------|------|------|------|
| GoodIden | 字符 | 001 | 商品唯一編號 |
| Name | 字符 | ADIDAS 慢跑鞋 | 商品名稱 |
| CateName | 字符 | 慢跑鞋 | 商品分類 |
| REMARK | 字符 | 男鞋 黑 白 | 商品標籤 |
| Price | 數字 | 3500 | 商品價格 |

### 可選欄位

| 欄位 | 類型 | 例子 | 說明 |
|------|------|------|------|
| SpecialPrice | 數字 | 2999 | 特價 |
| SpecialOffer | 字符 | 優惠中 | 特價標記 |
| BRAND_Name | 字符 | ADIDAS | 品牌 |
| Description | 字符 | 舒適透氣 | 詳細描述 |

### 範例

```csv
GoodIden,Name,CateName,REMARK,Price,SpecialPrice
001,ADIDAS Alphacomfy 慢跑鞋,慢跑鞋,男鞋 黑 白 緩衝 透氣,3500,3150
002,NIKE Nike Jordan Tatum 2 籃球鞋,籃球鞋,籃球鞋 運動 實戰,4200,
003,掀蓋式專利頭層牛皮自動皮帶,男用皮帶,男用皮帶 真皮 自動扣,1200,999
```

---

## 🧪 測試驗證

### 驗證上傳功能

```bash
# 1. 確認 ALLOW_DEV_ADMIN 已設置
grep ALLOW_DEV_ADMIN backend/.env
# 輸出: ALLOW_DEV_ADMIN=1

# 2. 確認 CSV 檔案存在
ls -lh data/VIEW_GOODS_enhanced.csv
# 輸出: 1.1M VIEW_GOODS_enhanced.csv

# 3. 確認目錄可寫
touch data/test.txt && rm data/test.txt && echo "✓ 目錄可寫"
```

### 前端測試

1. 打開瀏覽器開發者工具 (F12)
2. 進入 Network 標籤
3. 點擊上傳按鈕
4. 查看 `/api/admin/upload-csv` 請求
   - 狀態碼應為 200
   - 響應應包含 "status": "ok"

### 後端日誌

```bash
# 查看上傳相關日誌
tail -50 backend.log | grep -i "upload\|replace"

# 應看到類似日誌：
# received upload from 127.0.0.1 size=1234567 -> .../data/VIEW_GOODS_enhanced.csv
# replaced data file at .../data/VIEW_GOODS_enhanced.csv and cleared cache
```

---

## 📞 常見問題

### Q1: 上傳後數據未更新
**A**: 刷新頁面或點擊 "清除快取" 按鈕

### Q2: 上傳失敗 (403 Forbidden)
**A**: 檢查 `.env` 是否有 `ALLOW_DEV_ADMIN=1`

### Q3: 上傳失敗 (401 Unauthorized)
**A**: 生產模式下需要輸入正確的 token

### Q4: CSV 檔案為空錯誤
**A**: 確保上傳的 CSV 檔案大小 > 0

### Q5: 檔案未移動到 data 目錄
**A**: 檢查 `data/` 目錄是否存在且可寫

---

## 📝 提交記錄

```
commit 7a002fe
Author: HUANG CHANG-CHI <116869492+jacky6063@users.noreply.github.com>

docs: 添加管理版面使用指南並啟用開發模式

改進項目：
1. 在 backend/.env 中啟用 ALLOW_DEV_ADMIN=1
   - 允許開發環境中直接上傳 CSV 檔案，無需 token
   - 無需在前端輸入管理員 token

2. 創建詳細的管理版面使用指南 (ADMIN_GUIDE.md)
   - 完整的功能說明
   - 上傳步驟（圖文並茂）
   - 開發/生產環境配置
   - 常見問題排查
   - CSV 格式範例
   - 安全建議
   - API 技術參考
   - 完成檢查清單
```

---

## 🎉 總結

### ✅ 已解決

- ✅ 配置開發模式 (ALLOW_DEV_ADMIN=1)
- ✅ 無需 token 認證
- ✅ 直接上傳 CSV 檔案
- ✅ 自動更新到 data 目錄
- ✅ 自動清除快取

### 📚 新增文檔

- 📖 完整管理指南 (ADMIN_GUIDE.md)
- 📖 本解決方案文檔

### 🚀 立即開始

1. 確認 `backend/.env` 已設置 `ALLOW_DEV_ADMIN=1`
2. 重啟後端服務
3. 點擊管理版面 → 選擇 CSV → 上傳
4. 完成！

---

**最後更新**: 2025年11月4日  
**版本**: 1.0  
**作者**: AI Assistant
