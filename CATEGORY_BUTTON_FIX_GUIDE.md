# 分類按鈕錯誤修復指南

## 🔍 問題確認

商品卡下方的分類麵包屑按鈕（大分類、中分類、小分類）點擊時顯示：
```
抱歉，系統忙碌或網路異常，請詳查
```

## ✅ 已進行的改進

### 1. 前端錯誤診斷增強

**檔案**: `frontend/index.html`

**改進內容**:

#### 改進 A: 搜尋失敗時提供更詳細的錯誤訊息

原本只顯示「抱歉，系統忙碌或網路異常」，現在根據錯誤類型顯示：

- **網路連線失敗** (TypeError / Failed to fetch)
  ```
  無法連接後端服務，請檢查網路狀態後重試。
  ```

- **後端伺服器錯誤** (HTTP 500)
  ```
  後端伺服器發生錯誤，請稍後重試。
  ```

- **查詢格式錯誤** (HTTP 400)
  ```
  查詢條件格式不正確，請檢查後重試。
  ```

- **其他 HTTP 錯誤** (其他狀態碼)
  ```
  伺服器返回錯誤 (HTTP XXX)，請稍後重試。
  ```

#### 改進 B: 自動重試機制

當搜尋失敗時，系統會自動重試最多 2 次：

```javascript
// 重試邏輯：
// 第 1 次失敗 → 等待 500ms 後重試
// 第 2 次失敗 → 等待 1000ms 後重試
// 第 3 次失敗 → 顯示錯誤訊息
```

這對於**暫時的網路波動**或**後端正在重啟**的情況非常有幫助。

#### 改進 C: 詳細的控制台日誌

現在當搜尋失敗時，會在瀏覽器控制台輸出詳細的診斷信息：

```javascript
🔴 搜尋錯誤詳情：{
  query: "米類",              // 搜尋字詞
  page: 1,                    // 頁碼
  attempt: 1,                 // 第幾次嘗試
  error: "TypeError: Failed to fetch",
  errorName: "TypeError",
  errorMessage: "Failed to fetch",
  timestamp: "2025-11-07T..."
}
```

### 2. 分類搜尋函數增強

**檔案**: `frontend/index.html` Line 1649

新增 try-catch 錯誤處理，捕捉分類搜尋過程中的異常：

```javascript
window.triggerCategorySearch = function(categoryQuery, event) {
  if(event) event.preventDefault();
  const inputEl = getActiveInput();
  if(inputEl) {
    inputEl.value = categoryQuery;
  }
  // 🔧 分類搜尋：添加更好的錯誤處理
  try {
    triggerSearchFromInputs(categoryQuery);
  } catch(err) {
    console.error('❌ 分類搜尋失敗:', err);
    setStatus('分類搜尋發生錯誤，請重試');
  }
}
```

---

## 🔧 故障排除指南

### 症狀 1: 所有分類按鈕都顯示錯誤訊息

#### 可能原因

1. **後端服務未運行** ❌
2. **網路連線異常** ❌
3. **後端 API 崩潰** ❌

#### 檢查步驟

**Step 1: 驗證後端是否運行**

在瀏覽器 DevTools Console 執行：

```javascript
// 測試後端連接
fetch('http://localhost:8000/api/version')
  .then(r => {
    console.log('✅ 後端正常，狀態:', r.status);
    return r.json();
  })
  .then(d => console.log('版本信息:', d))
  .catch(e => {
    console.error('❌ 後端連接失敗:', e);
    console.error('- 是否已啟動後端？');
    console.error('- 是否正確配置 API 地址？');
  });
```

**預期輸出（成功）**:
```
✅ 後端正常，狀態: 200
版本信息: {commit: "...", branch: "main", ...}
```

**預期輸出（失敗）**:
```
❌ 後端連接失敗: TypeError: Failed to fetch
- 是否已啟動後端？
- 是否正確配置 API 地址？
```

**Step 2: 查看瀏覽器控制台完整錯誤**

1. 打開瀏覽器 DevTools (F12)
2. 切換到 **Console** 標籤
3. 點擊分類按鈕
4. 查看是否有 🔴 紅色錯誤訊息
5. 複製完整的錯誤訊息

**Step 3: 查看 Network 請求**

1. 打開瀏覽器 DevTools (F12)
2. 切換到 **Network** 標籤
3. 點擊分類按鈕
4. 查找名稱為 `search` 的 POST 請求
5. 檢查：
   - **Status**: 應該是 200 (如果是 4xx 或 5xx 則有問題)
   - **Response**: 查看後端返回的錯誤訊息

**Step 4: 啟動後端**

如果後端未運行，執行以下命令：

```bash
# 進入後端目錄
cd /Users/huangchangchi/Documents/SEARCH_Goods/backend

# 啟動虛擬環境
source .venv/bin/activate

# 安裝依賴 (如果需要)
pip install -r requirements.txt

# 啟動後端 (開發模式)
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 或啟動生產模式
gunicorn -c gunicorn_conf.py app:app
```

**Step 5: 驗證後端已啟動**

在另一個終端執行：

```bash
curl -s http://localhost:8000/api/version | python3 -m json.tool

# 預期輸出
# {
#   "commit": "...",
#   "branch": "main",
#   "built_at": "...",
#   "short_commit": "..."
# }
```

### 症狀 2: 只有某些分類按鈕出現錯誤

#### 可能原因

1. **該分類下沒有商品** ✓
2. **分類名稱拼寫錯誤** ✓
3. **CSV 資料不完整** ✓

#### 解決方案

**步驟 1: 檢查商品資料**

在後端執行：

```bash
cd /Users/huangchangchi/Documents/SEARCH_Goods

# 查看 CSV 中的分類數據
python3 << 'EOF'
import pandas as pd

df = pd.read_csv('data/VIEW_GOODS_enhanced.csv', encoding='utf-8-sig')
print("CSV 欄位:", df.columns.tolist())
print("\n大分類 (L1):")
print(df['CateName_L1'].value_counts().head(10))
print("\n中分類 (L2):")
print(df['CateName_L2'].value_counts().head(10))
print("\n小分類 (L3):")
print(df['CateName_L3'].value_counts().head(10))
EOF
```

**步驟 2: 測試特定分類查詢**

在瀏覽器 Console 執行：

```javascript
// 測試「米類」搜尋
fetch('http://localhost:8000/api/search', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    query: '米類',
    topn: 30,
    page: 1,
    page_size: 30
  })
})
.then(r => r.json())
.then(d => {
  console.log('搜尋結果:', d);
  if(d.items && d.items.length) {
    console.log(`✅ 找到 ${d.items.length} 項商品`);
  } else {
    console.log('❌ 未找到任何商品');
  }
})
.catch(e => console.error('❌ 查詢失敗:', e));
```

**Step 3: 檢查分類層級過濾邏輯**

後端在 `_filter_by_hierarchy()` 函數中進行層級過濾。如果結果為空，會返回原始搜尋結果：

```python
# backend/app.py Line 607
filtered: List[Dict[str, Any]] = [...]
return filtered or records  # 如果 filtered 為空，返回 records
```

---

## 📊 修復效果評估

### 修復前 ❌

- ❌ 所有錯誤都顯示「系統忙碌」通用訊息
- ❌ 用戶無法判斷是網路問題還是後端問題
- ❌ 沒有自動重試機制
- ❌ 控制台沒有詳細診斷信息

### 修復後 ✅

- ✅ 根據錯誤類型顯示具體訊息
- ✅ 用戶可快速判斷問題原因
- ✅ 自動重試機制提高成功率
- ✅ 詳細的控制台日誌便於調試

---

## 🚀 建議的改進方向

### 1. 添加可視化的重試進度

```javascript
// 在重試時顯示「正在重試 (第 X/Y 次)...」
```

### 2. 添加健康檢查端點

```javascript
// 定期檢查後端是否可用
// 如果不可用，主動提示用戶
```

### 3. 實現智能降級

```javascript
// 如果搜尋失敗，嘗試返回熱門商品
// 如果仍然失敗，顯示本地快取的商品
```

### 4. 添加用戶反饋機制

```javascript
// 允許用戶報告錯誤並提交診斷信息到後端
```

---

## 📝 技術細節

### 改進前的代碼 (Line 1971-1990)

```javascript
} catch(err) {
  // ... 錯誤處理 ...
  setStatus("查詢失敗："+err);
}
```

### 改進後的代碼 (Line 1945-2010)

```javascript
for(let attempt = 0; attempt < MAX_RETRIES; attempt++) {
  try {
    // ... 執行搜尋 ...
    return;  // 成功則立即返回
  } catch(err) {
    lastError = err;
    // 如果還有重試次數，指數退避後重試
    if(attempt < MAX_RETRIES - 1) {
      const delayMs = Math.pow(2, attempt) * 500;  // 500ms, 1000ms
      await new Promise(resolve => setTimeout(resolve, delayMs));
      continue;
    }
    // 所有重試都失敗，顯示詳細錯誤
    // ... 顯示詳細錯誤訊息 ...
  }
}
```

---

## 💡 已知限制

1. **最多重試 2 次**: 避免搜尋過程過長
2. **無網路連線**: 無法通過重試解決永久性網路問題
3. **後端完全崩潰**: 需要手動重啟後端服務

---

## 📞 聯繫支持

如果問題仍未解決，請提供：

1. **瀏覽器控制台的完整錯誤訊息** (F12 → Console)
2. **後端啟動日誌** (如有 `server.log`)
3. **Network 標籤中的 POST /api/search 請求和回應** (F12 → Network)
4. **操作系統和環境信息** (Python 版本、Node 版本等)
