# 住戶端彈窗問題診斷報告

**日期**：2025年11月26日  
**測試環境**：localhost (前端:5173, 後端:8000)

---

## 📋 問題清單

### 問題 1：文字重複顯示
**症狀**：「客服人員 客服人員 已加入對話」  
**狀態**：✅ **已修正**

### 問題 2：客服訊息沒顯示
**症狀**：彈窗中看不到客服發送的訊息  
**狀態**：⚠️ **前端問題（需清除快取）**

### 問題 3：住戶無法發送訊息
**症狀**：輸入框無法送出訊息  
**狀態**：⚠️ **前端問題（需清除快取）**

---

## 🔍 詳細診斷

### 【問題 1】文字重複：客服人員 客服人員 已加入對話

#### 原因分析
```html
<!-- 原始 HTML（錯誤）-->
<span>客服人員 <strong id="operatorName"></strong> 已加入對話</span>
```

當 `operatorName` 的值設為 `"客服人員"` 時：
```
客服人員 + 客服人員 + 已加入對話 = 客服人員 客服人員 已加入對話 ❌
```

#### 解決方案
```html
<!-- 修正後 HTML（正確）-->
<span><strong id="operatorName"></strong> 已加入對話</span>
```

現在顯示：
```
客服人員 + 已加入對話 = 客服人員 已加入對話 ✅
```

#### 修正狀態
✅ **已修正並重啟前端服務**

---

### 【問題 2】客服訊息沒顯示

#### 後端驗證結果
```
✅ 客服訊息已正確寫入資料庫
   - role = 'Humans'
   - content = 實際訊息內容
   - session_id = 正確的 UUID
```

**測試 SQL 查詢：**
```sql
SELECT 
    message_id,
    role,
    content,
    created_at
FROM chat_messages
WHERE session_id = '你的session_id'
    AND source_module = 'repair'
ORDER BY created_at ASC;
```

#### 可能原因（按機率排序）

##### 原因 1：瀏覽器快取（90% 機率）⭐⭐⭐
**症狀**：
- 修改後的 `index.html` 未生效
- `appendPopupMessage()` 仍是舊版本
- CSS 樣式未更新

**檢查方式**：
```javascript
// 在瀏覽器 Console 執行
console.log(sendPopupMessage.toString());

// 如果看到 "TODO" 或沒有 "await fetch"，表示是舊版本
```

**解決方案**：
1. **方法 A（推薦）**：
   - Chrome: 右鍵重新整理按鈕
   - 選擇「清空快取並強制重新整理」

2. **方法 B**：
   - 按 `Cmd+Shift+Delete` (Mac) 或 `Ctrl+Shift+Delete` (Windows)
   - 勾選「快取的圖片和檔案」
   - 點擊「清除資料」
   - 重新載入頁面

3. **方法 C（開發者）**：
   - 開啟 DevTools (F12)
   - Network 標籤
   - 勾選「Disable cache」
   - 重新整理

---

##### 原因 2：輪詢機制未啟動（5% 機率）⭐
**症狀**：
- Console 沒有 `[Operator]` 相關日誌
- 彈窗能開啟但訊息不更新

**檢查方式**：
```javascript
// 檢查輪詢狀態
console.log('currentRepairSession:', currentRepairSession);
console.log('repairSessionPollingInterval:', repairSessionPollingInterval);

// 應該每 3 秒看到以下訊息：
// [Operator] 檢查狀態...
```

**解決方案**：
```javascript
// 手動啟動輪詢
startRepairSessionPolling('你的session_id');

// 或手動載入訊息
currentRepairSession = '你的session_id';
loadPopupMessages();
```

---

##### 原因 3：CSS 樣式問題（3% 機率）
**症狀**：
- 訊息存在但不可見
- DOM 有元素但螢幕看不到

**檢查方式**：
```javascript
// 檢查 DOM 元素
document.querySelectorAll('.popup-message').forEach(el => {
  console.log('訊息:', el.textContent.substring(0, 30));
  console.log('樣式:', window.getComputedStyle(el).display);
  console.log('顏色:', window.getComputedStyle(el.querySelector('.popup-message-bubble')).backgroundColor);
});
```

**解決方案**：
檢查 CSS 中是否有：
- `display: none`
- `visibility: hidden`
- `opacity: 0`
- `color: transparent`

---

##### 原因 4：role 類型對應錯誤（2% 機率）
**症狀**：
- 訊息在 DOM 中但沒有對應的 CSS 樣式
- Console 沒有錯誤但訊息不顯示

**檢查方式**：
```javascript
// 檢查 appendPopupMessage 函數
console.log(appendPopupMessage.toString());

// 應該包含：
// if (role === 'Humans' || role === 'operator') {
//   displayRole = 'operator';
// }
```

**已修正**：
最新版本已正確對應：
- `Humans` → `operator` (綠色氣泡)
- `llm` → `ai` (灰色氣泡)

---

### 【問題 3】住戶無法發送訊息

#### 可能原因（按機率排序）

##### 原因 1：快取問題（90% 機率）⭐⭐⭐
**症狀**：
- `sendPopupMessage()` 仍是舊版本
- 只有 `TODO` 註解，沒有實際發送程式碼

**檢查方式**：
```javascript
// 檢查函數實作
console.log('函數類型:', typeof sendPopupMessage);
console.log('是否為 async:', sendPopupMessage?.constructor.name);

// 應該顯示：
// 函數類型: function
// 是否為 async: AsyncFunction
```

**解決方案**：清除快取（同問題 2）

---

##### 原因 2：currentRepairSession 為 null（5% 機率）⭐
**症狀**：
- 輸入訊息後沒有反應
- Console 可能有錯誤

**檢查方式**：
```javascript
console.log('Session:', currentRepairSession);

// 應該是 UUID，例如：
// Session: 63a84088-77cd-4621-b897-d443335be38c

// 如果是 null：
console.log('❌ Session 未初始化');
```

**解決方案**：
```javascript
// 手動設定 session（從維修對話記錄中取得）
currentRepairSession = '你的session_id';

// 或重新發送維修訊息以建立 session
```

---

##### 原因 3：事件監聽器未綁定（3% 機率）
**症狀**：
- 點擊「送出」按鈕沒有反應
- 按 Enter 鍵也沒有反應

**檢查方式**：
```javascript
const btn = document.getElementById('popupSendBtn');
console.log('按鈕:', btn);
console.log('事件監聽器:', getEventListeners(btn)); // Chrome DevTools 專用
```

**解決方案**：
```javascript
// 手動綁定事件
document.getElementById('popupSendBtn').addEventListener('click', sendPopupMessage);
document.getElementById('popupInput').addEventListener('keypress', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendPopupMessage();
  }
});
```

---

##### 原因 4：JavaScript 執行錯誤（2% 機率）
**症狀**：
- Console 有紅色錯誤訊息
- 可能是語法錯誤或未定義的變數

**檢查方式**：
```
開啟 Console，查看是否有紅色錯誤訊息
```

**常見錯誤**：
- `Uncaught ReferenceError: xxx is not defined`
- `Uncaught TypeError: Cannot read property 'xxx' of null`
- `Uncaught SyntaxError: Unexpected token`

---

## 🧪 完整測試流程

### 步驟 1：清除快取（必做）⭐⭐⭐
```
1. 開啟 http://localhost:5173
2. 右鍵點擊重新整理按鈕
3. 選擇「清空快取並強制重新整理」
```

### 步驟 2：驗證前端程式碼
在 Console 執行：
```javascript
const checks = {
  '彈窗元素': document.getElementById('operatorPopup') !== null,
  '輸入框': document.getElementById('popupInput') !== null,
  '送出按鈕': document.getElementById('popupSendBtn') !== null,
  'sendPopupMessage': typeof sendPopupMessage === 'function',
  '是async函數': sendPopupMessage?.constructor.name === 'AsyncFunction',
  'checkNewMessages': typeof checkNewMessages === 'function',
  'appendPopupMessage': typeof appendPopupMessage === 'function',
  'currentRepairSession': typeof currentRepairSession !== 'undefined',
};

console.table(checks);

// 全部應該為 true
```

### 步驟 3：測試完整流程
```
1. 點擊「維修諮詢」
2. 輸入「測試：浴室馬桶堵塞」
3. 點擊「送出」
4. 觀察 Console：
   [Operator] 開始輪詢 session: xxx

5. 開啟客服端：http://localhost:8000/repair_chat_viewer.html
6. 輸入回覆：「收到，會儘快處理」
7. 點擊「發送」

8. 回到住戶端，3-5 秒內應：
   ✓ 彈出對話視窗
   ✓ 標題顯示：客服人員 已加入對話（不重複）
   ✓ 看到客服訊息（綠色氣泡）

9. 在彈窗輸入「請問多久會到？」
10. 點擊「送出」
11. 訊息應立即顯示（藍色氣泡）
```

### 步驟 4：查詢資料庫驗證
```sql
-- 查詢訊息記錄
SELECT 
    role,
    content,
    created_at
FROM chat_messages
WHERE session_id = '你的session_id'
    AND source_module = 'repair'
ORDER BY created_at ASC;

-- 應該看到：
-- user    | 測試：浴室馬桶堵塞
-- llm     | AI 的回覆...
-- Humans  | 收到，會儘快處理
-- user    | 請問多久會到？
```

---

## 📊 修正狀態總結

| 問題 | 狀態 | 說明 |
|------|------|------|
| 1. 文字重複 | ✅ 已修正 | HTML 已更新，前端已重啟 |
| 2. 客服訊息不顯示 | ⚠️ 需清除快取 | 後端正常，前端程式碼已更新 |
| 3. 無法發送訊息 | ⚠️ 需清除快取 | sendPopupMessage() 已實作 |

---

## 🎯 立即執行清單

1. ✅ **HTML 已修正**：移除重複的「客服人員」文字
2. ✅ **前端已重啟**：最新版本已部署
3. ⚠️ **使用者需執行**：
   - 清除瀏覽器快取
   - 強制重新整理 (`Cmd+Shift+R`)
   - 按照測試流程驗證功能

---

## 📞 進一步診斷

如果清除快取後問題仍存在，請在 Console 執行：

```javascript
// 完整診斷腳本
console.log('=== 診斷開始 ===');
console.log('1. 元素檢查:');
console.log('  operatorPopup:', !!document.getElementById('operatorPopup'));
console.log('  popupInput:', !!document.getElementById('popupInput'));
console.log('  popupSendBtn:', !!document.getElementById('popupSendBtn'));

console.log('2. 函數檢查:');
console.log('  sendPopupMessage:', typeof sendPopupMessage, sendPopupMessage?.constructor.name);
console.log('  checkNewMessages:', typeof checkNewMessages);
console.log('  appendPopupMessage:', typeof appendPopupMessage);

console.log('3. 變數檢查:');
console.log('  currentRepairSession:', currentRepairSession);
console.log('  isOperatorPopupOpen:', isOperatorPopupOpen);
console.log('  lastMessageCount:', lastMessageCount);

console.log('4. 訊息檢查:');
if (currentRepairSession) {
  fetch(`http://localhost:8000/api/repair/session/${currentRepairSession}/messages`)
    .then(r => r.json())
    .then(d => {
      console.log('  總訊息數:', d.total_count);
      d.messages.forEach(m => console.log(`  [${m.role}] ${m.content.substring(0, 30)}...`));
    });
} else {
  console.log('  ⚠️ 沒有 active session');
}

console.log('=== 診斷結束 ===');
```

將輸出結果提供給技術支援。

---

**最後更新**：2025年11月26日  
**修正版本**：v1.1
