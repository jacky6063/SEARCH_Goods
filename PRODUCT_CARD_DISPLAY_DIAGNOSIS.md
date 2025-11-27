# 商品資料卡無法顯示 - 診斷報告

## 🔍 問題描述
用戶查詢「有斜款背包？」後:
- ✅ 後端正確返回 8 款商品
- ✅ structured_products 和 structured_payload 都有資料
- ✅ 聊天回覆文字顯示正確
- ❌ **商品資料卡片未顯示**

## 📊 後端驗證結果

### API 測試輸出
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "有斜款背包", "history": [], "session_id": "test123"}'
```

**返回資料:**
- `structured_products`: 8 款商品 ✅
- `structured_payload.summary`: "8 款商品" ✅
- `suggestion_ids`: 8 個 ID ✅

**商品資料範例:**
```json
{
  "index": 1,
  "商品編號": "V55212D-1150",
  "商品名稱": "前扣式編織麻花肩背包-黃色",
  "商品描述": "前扣式編織麻花肩時尚質感，實用時尚好搭配",
  "商品價格": 2980,
  "購物連結": "https://s1.myqr.com.tw/..."
}
```

## 🔧 前端流程分析

### 關鍵代碼路徑 (frontend/index.html)

#### 1. API 回應處理 (Line 1820-1870)
```javascript
// 解析回應
assistantReplyText = data.reply;
const assistantParsed = stripIntentPayload(assistantReplyText);
const structuredPayload = (assistantParsed.intent && Array.isArray(assistantParsed.intent.items)) 
  ? assistantParsed.intent : null;
let structuredItems = structuredPayload 
  ? structuredPayload.items.map(normalizeStructuredItem).filter(Boolean) 
  : null;
let structuredSummary = structuredPayload?.summary || summaryLineFromReply;

// 🔧 Fallback 到 data.structured_products
if((!structuredItems || !structuredItems.length) && 
   Array.isArray(data.structured_products) && 
   data.structured_products.length){
  structuredItems = data.structured_products.map(normalizeStructuredItem).filter(Boolean);
  if(!structuredSummary && data.structured_payload && data.structured_payload.summary){
    structuredSummary = data.structured_payload.summary;
  }
}
```

**問題點:** 這段邏輯依賴於 `stripIntentPayload()` 先解析回覆文字中的 JSON payload,如果找不到才 fallback 到 `data.structured_products`。

#### 2. 商品顯示邏輯 (Line 1876-1910)
```javascript
if(!isSearchFallback && structuredItems && structuredItems.length){
  // ... 儲存到 latestSuggestCache ...
  
  if(mode !== 'search'){
    // 💡 如果在聊天模式,切換到搜尋模式並顯示商品
    switchToSearch('', structuredIds || [], structuredItems, 
                   data.category_groups, structuredSummary);
  }else if(hasPayloadItems){
    // 💡 如果已在搜尋模式,直接渲染
    renderPlanResults(structuredItems, data.meta || {});
  }
  structuredStored = true;
}
```

**可能問題:**
1. `isSearchFallback` 為 true,導致跳過整個區塊
2. `mode` 狀態不正確
3. `structuredItems` 被過濾成空陣列

## 🎯 診斷步驟

### 前端 Console 檢查清單
在瀏覽器開發者工具 Console 中執行:

```javascript
// 1. 檢查當前模式
console.log('Current mode:', mode);

// 2. 檢查最後一次聊天回應
console.log('Latest chat response:', window.lastChatResponse);

// 3. 檢查 structured cache
console.log('latestSuggestCache:', latestSuggestCache);

// 4. 檢查聊天歷史
console.log('Chat history:', chatHistory);

// 5. 手動觸發商品顯示 (如果有資料)
if(latestSuggestCache[0] && latestSuggestCache[0].items){
  console.log('嘗試手動渲染:', latestSuggestCache[0].items.length, '款商品');
  switchToSearch('', 
                latestSuggestCache[0].ids, 
                latestSuggestCache[0].items, 
                null, 
                latestSuggestCache[0].summary);
}
```

### 後端 Log 檢查
檢查 backend logs 確認:
```bash
# 查看 compose_structured_reply 是否被調用
grep "compose_structured_reply" backend/logs/*

# 查看 structured_payload 生成
grep "structured_payload" backend/logs/*
```

## 🔬 根本原因假設

### 假設 1: stripIntentPayload() 失敗
`stripIntentPayload()` 可能無法正確解析回覆文字中的 JSON,導致 `structuredItems` 為空。

**驗證方法:**
```javascript
// 在 Line 1829 後添加
console.log('🔍 stripIntentPayload result:', assistantParsed);
console.log('🔍 structuredPayload:', structuredPayload);
console.log('🔍 structuredItems before fallback:', structuredItems);
```

### 假設 2: normalizeStructuredItem() 過濾掉所有商品
`normalizeStructuredItem()` 可能因為欄位名稱不匹配而返回 null。

**驗證方法:**
```javascript
// 檢查 normalizeStructuredItem 函數
console.log('Testing normalizeStructuredItem:', 
  normalizeStructuredItem(data.structured_products[0]));
```

### 假設 3: mode 狀態錯誤
當前 `mode` 可能不是 'chat' 也不是 'search'。

**驗證方法:**
```javascript
console.log('Current mode:', mode);
console.log('Mode !== search:', mode !== 'search');
```

### 假設 4: isSearchFallback 標記錯誤
`isSearchFallback` 可能被錯誤設置為 true。

**驗證方法:**
```javascript
// 在 Line 1876 前添加
console.log('🔍 isSearchFallback:', isSearchFallback);
console.log('🔍 structuredItems?.length:', structuredItems?.length);
```

## 🛠️ 快速修復方案

### 方案 A: 強制使用 structured_products
修改 Line 1832-1836,優先使用 `data.structured_products`:

```javascript
// 🔧 修改: 優先使用 API 返回的 structured_products
if(Array.isArray(data.structured_products) && data.structured_products.length){
  structuredItems = data.structured_products.map(normalizeStructuredItem).filter(Boolean);
  if(data.structured_payload && data.structured_payload.summary){
    structuredSummary = data.structured_payload.summary;
  }
} else if(assistantParsed.intent && Array.isArray(assistantParsed.intent.items)){
  // Fallback: 從回覆文字解析
  structuredItems = assistantParsed.intent.items.map(normalizeStructuredItem).filter(Boolean);
  structuredSummary = assistantParsed.intent.summary || summaryLineFromReply;
}
```

### 方案 B: 添加 Debug 日誌
在關鍵位置添加詳細日誌:

```javascript
// Line 1876 之前
console.log('🔍 [PRODUCT_CARD_DEBUG]', {
  isSearchFallback,
  hasStructuredItems: !!(structuredItems && structuredItems.length),
  structuredItemsCount: structuredItems?.length || 0,
  mode,
  hasPayloadItems,
  structuredSummary
});
```

### 方案 C: 移除 isSearchFallback 條件
如果 `isSearchFallback` 標記有誤,臨時移除這個條件:

```javascript
// 修改 Line 1876
// if(!isSearchFallback && structuredItems && structuredItems.length){
if(structuredItems && structuredItems.length){
  // ... 顯示商品 ...
}
```

## 📝 下一步行動

1. **立即檢查:** 在瀏覽器 Console 執行診斷腳本
2. **添加日誌:** 在 Line 1876 前添加 debug console.log
3. **測試修復:** 實施方案 A 或 C
4. **驗證:** 重新載入頁面並測試「有斜款背包」查詢

## 🎯 預期結果

修復後應該看到:
- ✅ 聊天回覆文字顯示
- ✅ 自動切換到搜尋模式 (或在聊天模式顯示商品卡)
- ✅ 顯示 8 張商品卡片,包含圖片、名稱、價格、購買連結
- ✅ 「按 1.原建議商品」提示正常運作
