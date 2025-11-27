# 商品資料卡顯示問題 - 快速修復指南

## 🎯 問題定位

經過代碼審查,發現問題可能在於前端的商品資料處理邏輯。

### 可能原因
1. `stripIntentPayload()` 無法解析後端返回的 structured_products
2. `mode` 狀態導致商品渲染邏輯被跳過
3. `isSearchFallback` 標記錯誤

## 🛠️ 即時修復方案

### 方案 1: 在瀏覽器 Console 手動觸發顯示

如果後端資料正確,可以在瀏覽器開發者工具 Console 中執行:

```javascript
// 1. 檢查最後一次聊天回應
console.log('Latest response:', window.lastChatData);

// 2. 手動觸發顯示 (如果 latestSuggestCache 有資料)
if(latestSuggestCache && latestSuggestCache[0]){
  const cache = latestSuggestCache[0];
  console.log('Cache found:', cache);
  if(cache.items && cache.items.length > 0){
    switchToSearch('', cache.ids || [], cache.items, null, cache.summary || '商品推薦');
  }
}

// 3. 如果沒有 cache,從最後回應重建
if(window.lastChatData && window.lastChatData.structured_products){
  const products = window.lastChatData.structured_products;
  const ids = products.map(p => p['商品編號'] || p.GoodIden).filter(Boolean);
  console.log('Rebuilding from lastChatData:', products.length, '商品');
  switchToSearch('', ids, products, null, '為您找到的商品');
}
```

### 方案 2: 修改前端代碼 (永久修復)

編輯 `frontend/index.html`,在 Line 1832 附近修改:

**原代碼 (Line 1828-1836):**
```javascript
const structuredPayload = (assistantParsed.intent && Array.isArray(assistantParsed.intent.items)) ? assistantParsed.intent : null;
let structuredItems = structuredPayload ? structuredPayload.items.map(normalizeStructuredItem).filter(Boolean) : null;
let structuredSummary = structuredPayload?.summary || summaryLineFromReply;

if((!structuredItems || !structuredItems.length) && Array.isArray(data.structured_products) && data.structured_products.length){
  structuredItems = data.structured_products.map(normalizeStructuredItem).filter(Boolean);
  if(!structuredSummary && data.structured_payload && data.structured_payload.summary){
    structuredSummary = data.structured_payload.summary;
  }
}
```

**修改為 (優先使用 API 返回的 structured_products):**
```javascript
// 🔧 修復: 優先使用 API 直接返回的 structured_products
let structuredItems = null;
let structuredSummary = summaryLineFromReply;

if(Array.isArray(data.structured_products) && data.structured_products.length > 0){
  // 優先: 使用 API 返回的 structured_products
  console.log('✅ 使用 API structured_products:', data.structured_products.length);
  structuredItems = data.structured_products.map(normalizeStructuredItem).filter(Boolean);
  if(data.structured_payload && data.structured_payload.summary){
    structuredSummary = data.structured_payload.summary;
  }
} else if(assistantParsed.intent && Array.isArray(assistantParsed.intent.items)){
  // Fallback: 從回覆文字中解析
  console.log('⚠️ Fallback: 從回覆文字解析商品');
  structuredItems = assistantParsed.intent.items.map(normalizeStructuredItem).filter(Boolean);
  structuredSummary = assistantParsed.intent.summary || summaryLineFromReply;
}

console.log('🔍 structuredItems 結果:', structuredItems?.length || 0);
```

### 方案 3: 移除 isSearchFallback 條件檢查

找到 Line 1876 附近:

**原代碼:**
```javascript
if(!isSearchFallback && structuredItems && structuredItems.length){
```

**修改為:**
```javascript
if(structuredItems && structuredItems.length){
  console.log('✅ 準備顯示商品卡片:', structuredItems.length);
```

然後在 Line 1896-1900 添加更多日誌:

```javascript
if(mode !== 'search'){
  console.log('🔄 切換到搜尋模式並顯示商品');
  switchToSearch('', structuredIds || [], structuredItems, data.category_groups, structuredSummary);
}else if(hasPayloadItems){
  console.log('🔄 在搜尋模式直接渲染');
  renderPlanResults(structuredItems, data.meta || {});
}
```

## 🧪 測試步驟

### 1. 應用修復
選擇上述任一方案並應用。

### 2. 清除快取並重新載入
```bash
# 在瀏覽器按 Cmd+Shift+R (Mac) 或 Ctrl+Shift+R (Windows)
# 或者
# 開發者工具 > Application > Clear storage > Clear site data
```

### 3. 測試查詢
在聊天介面輸入:
```
有斜款背包
```

### 4. 檢查 Console
開啟開發者工具 Console,應該看到:
```
✅ 使用 API structured_products: 8
🔍 structuredItems 結果: 8
✅ 準備顯示商品卡片: 8
🔄 切換到搜尋模式並顯示商品
```

### 5. 驗證顯示
應該看到:
- ✅ 商品卡片顯示 (8 張)
- ✅ 每張卡片包含圖片、名稱、價格、購買按鈕
- ✅ 「按 1.原建議商品」提示正常

## 📊 預期 Console 輸出

**正常流程:**
```
[sendChat] 發送訊息: 有斜款背包
✅ 使用 API structured_products: 8
🔍 structuredItems 結果: 8
✅ 準備顯示商品卡片: 8
🔄 切換到搜尋模式並顯示商品
✅ switchToSearch: 直接渲染商品列表
[renderList] 渲染 8 款商品
```

**異常流程 (如果仍失敗):**
```
[sendChat] 發送訊息: 有斜款背包
⚠️ Fallback: 從回覆文字解析商品
🔍 structuredItems 結果: 0
❌ 沒有商品資料可顯示
```

## 🔧 額外除錯工具

### 儲存 lastChatData 以供檢查
在 `sendChat` 函數中 (Line 1815 附近),添加:

```javascript
async function sendChat(message) {
  try {
    // ... existing code ...
    const data = await response.json();
    
    // 🔧 儲存最後一次回應以供除錯
    window.lastChatData = data;
    console.log('📦 已儲存 lastChatData:', data);
    
    // ... rest of code ...
  }
}
```

### 手動觸發商品顯示的快捷函數
在 Console 中定義:

```javascript
window.debugShowProducts = function() {
  if(!window.lastChatData) {
    console.error('❌ 沒有 lastChatData');
    return;
  }
  const data = window.lastChatData;
  if(!data.structured_products || !data.structured_products.length) {
    console.error('❌ lastChatData 沒有 structured_products');
    return;
  }
  console.log('✅ 強制顯示', data.structured_products.length, '款商品');
  const ids = data.structured_products.map(p => p['商品編號'] || p.GoodIden).filter(Boolean);
  switchToSearch('', ids, data.structured_products, null, '除錯: 商品推薦');
};

// 使用方式:
// debugShowProducts();
```

## ✅ 成功指標

修復成功後應該看到:
1. **聊天介面**: AI 回覆文字正常顯示
2. **自動切換**: 自動從聊天模式切換到搜尋模式
3. **商品卡片**: 顯示 8 張商品卡片網格
4. **完整資訊**: 每張卡片有圖片、名稱、描述、價格、購買連結
5. **互動提示**: 底部顯示「按 1.原建議商品 or 對話區 輸入 1 按送出」

## 📝 長期解決方案

建議在下一個版本中:
1. 統一商品資料來源邏輯,避免多重 fallback
2. 添加更完整的錯誤處理和用戶提示
3. 實施前端資料流追蹤 (Redux/Vuex/狀態管理)
4. 添加 E2E 測試覆蓋商品卡片顯示流程
