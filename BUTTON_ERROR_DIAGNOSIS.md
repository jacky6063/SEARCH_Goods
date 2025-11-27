# 商品卡按鈕錯誤診斷報告

## 問題描述
商品卡上的按鈕（購買、分享等）在點擊時都顯示：
```
抱歉，系統忙碌或網路異常，請詳查
```

## 根本原因分析

### 1️⃣ 目前代碼中的商品卡按鈕

**位置**: `frontend/index.html` Line 1605-1615

```html
// 操作按鈕區域
const actionButtons = [];

// 按鈕 1: 購買按鈕
if(link && link.trim()){
  actionButtons.push(`<a class="action-btn primary" href="${a(link)}" target="_blank" rel="noopener">🛒 購買</a>`);
}

// 按鈕 2: 分享按鈕
actionButtons.push(`<button class="action-btn secondary" onclick="shareProduct('${a(JSON.stringify({name,price,sale,link}).replace(/'/g, "\\'"))}')">📤 分享</button>`);
```

### 2️⃣ 可能導致錯誤的場景

#### 場景 A: 搜尋過程中出現錯誤 ❌

**代碼位置**: `frontend/index.html` Line 1925-1943

```javascript
} catch(err) {
  // 搜尋失敗時顯示錯誤卡片
  clearResults();
  const errorCard = document.createElement("div");
  errorCard.className = "card";
  errorCard.innerHTML = `
    <div class="card-img">
      <div class="card-placeholder">系統忙碌</div>
    </div>
    <div class="card-body">
      <h3 class="card-title">抱歉，系統忙碌或網路異常</h3>
      <p class="card-desc">請稍後再試，或檢查網路連線後重新發送。</p>
    </div>`;
  resultsEl.appendChild(errorCard);
  setStatus("查詢失敗："+err);
}
```

**可能的原因**:
- API 端點無法連接
- 後端服務崩潰或重啟中
- 網路連線中斷
- API 返回錯誤狀態碼

#### 場景 B: API 調用返回 4xx/5xx 錯誤 ❌

**代碼位置**: `frontend/index.html` Line 1393-1396

```javascript
const resp = await fetch(buildBackendUrl('suggest'), {
  method:'POST',
  headers:{'Content-Type':'application/json'},
  body: JSON.stringify({ session_id: payloadSessionId, type })
});
if(!resp.ok){ throw new Error(`HTTP ${resp.status}`); }  // ← 此處會拋出錯誤
```

#### 場景 C: 分享按鈕 JSON 解析失敗 ❌

**代碼位置**: `frontend/index.html` Line 685-711

```javascript
window.shareProduct = function(productDataStr) {
  try {
    const product = JSON.parse(productDataStr);  // ← 如果 JSON 格式錯誤會失敗
    // ...
  } catch(err) {
    console.error('分享失敗:', err);
    setStatus('分享功能發生錯誤');  // ← 顯示錯誤
  }
};
```

---

## 🔍 診斷步驟

### Step 1: 檢查後端連接

在瀏覽器控制台執行：

```javascript
fetch('http://localhost:8000/api/version')
  .then(r => r.json())
  .then(d => console.log('✅ 後端正常:', d))
  .catch(e => console.error('❌ 後端連接失敗:', e));
```

**預期輸出**: 
```json
{"commit": "...", "short_commit": "...", "branch": "main", "built_at": "..."}
```

**實際輸出為錯誤** 👉 **後端未運行或無法連接**

### Step 2: 查看詳細錯誤

在瀏覽器控制台執行：

```javascript
// 查看最近的錯誤訊息
window.debugSearchGoods();
```

**輸出示例**:
```
🔍 SEARCH_GOODS 系統狀態:
- 當前模式: search
- Session ID: ...
- 建議快取: {1: X 商品, X IDs}
- 完整快取資料: ...
```

### Step 3: 檢查 Network 標籤

1. 打開瀏覽器 DevTools → Network 標籤
2. 點擊商品卡按鈕（購買/分享/推薦）
3. 查看 API 請求：
   - 是否有紅色 ❌ 標記（請求失敗）
   - Status Code 是否為 200
   - 回應內容是什麼

**常見的 HTTP 狀態碼**:
- `200` ✅ 成功
- `400` ❌ 請求格式錯誤
- `401`/`403` ❌ 認證/授權失敗
- `404` ❌ API 端點不存在
- `500` ❌ 後端伺服器錯誤
- `503` ❌ 伺服器暫時無法服務

### Step 4: 查看 Console 日誌

1. 打開瀏覽器 DevTools → Console 標籤
2. 點擊商品卡按鈕
3. 查看是否有紅色 🔴 錯誤訊息：

```
❌ 建議請求失敗: ...
查詢失敗: ...
分享失敗: ...
```

---

## 💡 可能的解決方案

### 問題 1: 後端未運行

**症狀**: 
- Network 標籤中 API 請求立即失敗
- Console 顯示 "Failed to fetch" 或 "ERR_CONNECTION_REFUSED"

**解決方案**:

```bash
cd /Users/huangchangchi/Documents/SEARCH_Goods/backend

# 1. 啟動後端（開發模式）
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 2. 或使用 gunicorn（生產模式）
gunicorn -c gunicorn_conf.py app:app
```

### 問題 2: 後端崩潰或錯誤

**症狀**:
- 後端返回 500 Internal Server Error
- 後端日誌顯示 Python 異常

**解決方案**:

1. 查看後端日誌
2. 檢查 `/api/chat` 或 `/api/suggest` 端點是否有異常
3. 驗證 `SESSION_ALIGN_CACHE` 和 `SUGGEST_CACHE` 是否滿了

```bash
# 查看後端日誌（如果已保存）
tail -f server.log

# 或重新啟動後端
pkill -f "uvicorn app:app"
# 然後重新執行上面的啟動命令
```

### 問題 3: CORS 或網路配置錯誤

**症狀**:
- Network 標籤顯示 CORS 錯誤
- Console 顯示 "No 'Access-Control-Allow-Origin' header"

**解決方案**:

驗證 `backend/app.py` 中的 CORS 設置:

```python
# Line 421 附近應該有：
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許所有來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

如果沒有，請確保後端正確配置 CORS。

### 問題 4: 分享按鈕數據格式問題

**症狀**:
- 只有分享按鈕出現錯誤
- Console 顯示 "JSON.parse error"

**解決方案**:

檢查 `shareProduct` 函數中的數據格式：

```javascript
// Line 1612 中的 JSON 格式應該正確
onclick="shareProduct('${a(JSON.stringify({name,price,sale,link}).replace(/'/g, "\\'"))}')">📤 分享</button>

// 驗證數據是否正確序列化
console.log(JSON.stringify({name,price,sale,link}));
```

---

## 🛠️ 修復步驟

### 步驟 1: 驗證後端正常運行

```bash
# 檢查後端進程
ps aux | grep uvicorn

# 如果進程不存在，啟動後端
cd /Users/huangchangchi/Documents/SEARCH_Goods/backend
source .venv/bin/activate
uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
```

### 步驟 2: 驗證 API 端點

```bash
# 測試 /api/version 端點
curl -X GET http://localhost:8000/api/version

# 預期輸出
# {"commit":"...","branch":"main",...}

# 如果無法連接，檢查防火牆或端口佔用
lsof -i :8000
```

### 步驟 3: 查看詳細錯誤

在瀏覽器中打開應用，按 F12 打開 DevTools：

1. **Console 標籤**: 查看錯誤訊息
2. **Network 標籤**: 查看 API 請求和回應
3. **Storage 標籤**: 查看本地快取

### 步驟 4: 清除快取

```javascript
// 在瀏覽器 Console 執行
localStorage.clear();
sessionStorage.clear();
// 重新整理頁面
location.reload();
```

### 步驟 5: 檢查環境變數

```bash
cd /Users/huangchangchi/Documents/SEARCH_Goods/backend

# 檢查 .env 文件
cat .env

# 確保設置了必要的變數
# USE_LLM_EXPAND=True
# USE_LLM_SHORTDESC=True
# OPENAI_API_KEY=...（如果使用 LLM）

# 或複製 .env.example
cp .env.example .env
```

---

## 📋 常見錯誤對照表

| 按鈕 | 錯誤症狀 | 原因 | 解決方案 |
|------|-------|------|--------|
| 購買 | 點擊後無反應或 404 | 商品購物網址為空或無效 | 檢查 CSV 中的購物連結欄位 |
| 分享 | "分享功能發生錯誤" | JSON 格式錯誤或剪貼板權限 | 檢查浏覽器隱私設置 |
| 推薦 | "抱歉，系統忙碌或網路異常" | 後端 `/api/suggest` 失敗 | 檢查後端是否運行，查看日誌 |
| 搜尋 | "抱歉，系統忙碌或網路異常" | 後端 `/api/search` 或 `/api/chat` 失敗 | 同上 |

---

## 🔧 提議的改進

### 改進 1: 更明確的錯誤訊息

```javascript
// 目前：
setStatus("查詢失敗："+err);

// 建議改為：
const errorMsg = err.message || String(err);
if(errorMsg.includes('HTTP 500')) {
  setStatus('後端服務器錯誤，請聯繫管理員');
} else if(errorMsg.includes('Failed to fetch')) {
  setStatus('網路連線失敗，請檢查連接後重試');
} else if(errorMsg.includes('HTTP 4')) {
  setStatus('請求格式錯誤，請稍後重試');
} else {
  setStatus(`查詢失敗：${errorMsg}`);
}
```

### 改進 2: 加入重試機制

```javascript
// 為搜尋、推薦等操作加入自動重試
async function fetchWithRetry(url, options, maxRetries = 3) {
  for(let i = 0; i < maxRetries; i++) {
    try {
      const resp = await fetch(url, options);
      if(resp.ok) return resp;
      if(resp.status >= 500 && i < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1))); // 指數退避
        continue;
      }
      throw new Error(`HTTP ${resp.status}`);
    } catch(err) {
      if(i === maxRetries - 1) throw err;
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
}
```

### 改進 3: 記錄詳細的錯誤信息

```javascript
// 在 window.debugSearchGoods() 中加入網路診斷
window.networkDiagnostics = async function() {
  const tests = {
    backend_health: null,
    search_api: null,
    chat_api: null,
    suggest_api: null,
    network_latency: null
  };
  
  try {
    // 測試各個 API
    const start = performance.now();
    const resp = await fetch('http://localhost:8000/health');
    tests.network_latency = Math.round(performance.now() - start);
    tests.backend_health = resp.ok ? '✅ 正常' : `❌ ${resp.status}`;
  } catch(e) {
    tests.backend_health = `❌ ${e.message}`;
  }
  
  console.table(tests);
  return tests;
};
```

---

## 📞 下一步行動

1. **執行診斷**: 按照上面的診斷步驟檢查
2. **收集日誌**: 提供後端日誌和瀏覽器控制台的詳細錯誤訊息
3. **描述環境**: 說明運行環境（本地/遠端、Docker/裸機等）
4. **檢查網路**: 驗證前端和後端是否在同一網路

---

## 📝 相關代碼位置

| 功能 | 檔案 | 行數 |
|------|------|------|
| 商品卡按鈕 | frontend/index.html | 1605-1615 |
| 錯誤卡片 | frontend/index.html | 1925-1943 |
| 分享功能 | frontend/index.html | 685-711 |
| 推薦 API | frontend/index.html | 1387-1492 |
| 後端搜尋 | backend/app.py | 搜尋相關路由 |
| 後端推薦 | backend/app.py | Line 901-925 |
