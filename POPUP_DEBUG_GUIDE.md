# 住戶端彈窗除錯指南

## 🐛 問題症狀
1. 彈窗中看不到客服訊息
2. 住戶無法在彈窗中發送訊息

---

## ✅ 後端驗證（已通過）

執行以下命令確認後端正常：
```bash
cd /Users/huangchangchi/Documents/SEARCH_Goods
python3 test_popup_messaging.py
```

預期結果：
```
✅ 住戶訊息已記錄
✅ AI 回覆已記錄
✅ 客服回覆已記錄 (role='Humans')
🎉 所有測試通過！
```

---

## 🌐 前端除錯步驟

### 步驟 1：清除瀏覽器快取

**重要！** 修改後的程式碼可能被快取，請執行以下操作：

#### Chrome/Edge:
1. 按 `Cmd+Shift+Delete` (Mac) 或 `Ctrl+Shift+Delete` (Windows)
2. 選擇「快取的圖片和檔案」
3. 點擊「清除資料」

或者：
1. 開啟開發者工具 (`Cmd+Option+I` 或 `F12`)
2. 右鍵點擊重新整理按鈕
3. 選擇「清空快取並強制重新整理」

---

### 步驟 2：開啟開發者工具

1. 開啟 http://localhost:5173
2. 按 `F12` 或 `Cmd+Option+I` 開啟開發者工具
3. 切換到 **Console** 標籤

---

### 步驟 3：測試完整流程

#### 3.1 發送維修訊息
1. 點擊「維修諮詢」或在網址後加 `#repair`
2. 輸入：「測試：浴室馬桶堵塞」
3. 點擊「送出」
4. 在 Console 中觀察：
   ```
   [Operator] 開始輪詢 session: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```

#### 3.2 模擬客服接手
開啟新分頁：http://localhost:8000/repair_chat_viewer.html

1. 找到剛才的對話
2. 點擊「接手」按鈕，或直接輸入回覆：
   ```
   您好！我已收到您的問題，會儘快處理。
   ```
3. 點擊「發送」

#### 3.3 觀察住戶端彈窗
回到住戶端分頁，觀察：

**預期行為：**
- 3-5 秒內，右下角自動彈出對話視窗
- Console 顯示：
  ```
  [Operator] 檢測到真人客服接手!
  [Operator] 彈窗顯示: 測試客服
  ```

**檢查彈窗內容：**
- ✅ 標題顯示：「客服人員 測試客服 已加入對話」
- ✅ 看到自己的訊息（藍色氣泡）
- ✅ 看到 AI 回覆（灰色氣泡）
- ✅ 看到客服訊息（綠色氣泡帶框線）

#### 3.4 測試發送訊息
在彈窗輸入框中：
1. 輸入：「請問大約多久會到？」
2. 點擊「送出」按鈕或按 `Enter`

**預期行為：**
- 訊息立即顯示在彈窗中（藍色氣泡）
- Console 無錯誤訊息
- 500ms 後收到 AI 回覆（灰色氣泡）

---

## 🔍 常見問題診斷

### 問題 A：彈窗沒有自動彈出

**檢查 Console 訊息：**
```javascript
// 應該看到：
[Operator] 開始輪詢 session: xxx
[Operator] 檢測到真人客服接手!
[Operator] 彈窗顯示: 客服名稱
```

**如果沒有「檢測到真人客服接手」：**
1. 確認客服端有點擊「接手」或發送回覆
2. 檢查 `manual_mode` 是否被設為 `true`：
   ```javascript
   fetch('http://localhost:8000/api/repair/session/你的session_id/status')
     .then(r => r.json())
     .then(d => console.log(d))
   ```
   應該看到 `manual_mode: true`

---

### 問題 B：彈窗中看不到客服訊息

**在 Console 執行：**
```javascript
// 檢查訊息記錄
const sessionId = '你的session_id';
fetch(`http://localhost:8000/api/repair/session/${sessionId}/messages`)
  .then(r => r.json())
  .then(d => {
    console.log('訊息數量:', d.total_count);
    d.messages.forEach(m => console.log(`[${m.role}] ${m.content.substring(0, 30)}...`));
  });
```

**檢查輸出：**
- 應該有 `role: 'Humans'` 的訊息
- 如果有訊息但彈窗中看不到，可能是 CSS 問題

**檢查 CSS 樣式：**
在 Console 執行：
```javascript
document.querySelectorAll('.popup-message').forEach(el => {
  console.log('Class:', el.className, 'Content:', el.textContent.substring(0, 30));
});
```

---

### 問題 C：住戶無法發送訊息

**檢查輸入框和按鈕：**
在 Console 執行：
```javascript
const input = document.getElementById('popupInput');
const btn = document.getElementById('popupSendBtn');
console.log('Input:', input, 'Button:', btn);
console.log('Input value:', input?.value);
console.log('Button has listener:', btn?._listeners || 'unknown');
```

**測試手動發送：**
```javascript
// 模擬發送訊息
const popupInput = document.getElementById('popupInput');
popupInput.value = '測試訊息';

const popupSendBtn = document.getElementById('popupSendBtn');
popupSendBtn.click();
```

觀察 Console 是否有錯誤訊息。

---

### 問題 D：訊息發送後沒有顯示

**檢查 `sendPopupMessage` 函數：**
在 Console 執行：
```javascript
console.log(sendPopupMessage.toString());
```

應該看到包含 `await fetch` 和 `repair/chat` 的程式碼。

**如果看到 `TODO`：**
表示程式碼未正確載入，需要：
1. 清除快取（重要！）
2. 強制重新整理 (`Cmd+Shift+R`)
3. 重新測試

---

## 📋 快速檢查清單

執行以下命令進行快速檢查：

```javascript
// 在瀏覽器 Console 中執行
const checks = {
  '彈窗元素': document.getElementById('operatorPopup') !== null,
  '輸入框': document.getElementById('popupInput') !== null,
  '送出按鈕': document.getElementById('popupSendBtn') !== null,
  '聊天區域': document.getElementById('popupChatArea') !== null,
  'sendPopupMessage 函數': typeof sendPopupMessage === 'function',
  'checkNewMessages 函數': typeof checkNewMessages === 'function',
  'appendPopupMessage 函數': typeof appendPopupMessage === 'function',
  'currentRepairSession': typeof currentRepairSession !== 'undefined',
};

console.table(checks);

// 檢查是否有 async
if (sendPopupMessage.constructor.name === 'AsyncFunction') {
  console.log('✅ sendPopupMessage 是異步函數');
} else {
  console.log('❌ sendPopupMessage 不是異步函數（可能是舊版本）');
}
```

---

## 🔧 緊急修復方案

如果問題持續，執行以下命令重啟服務：

```bash
# 重啟前端
pkill -f "http.server 5173"
cd /Users/huangchangchi/Documents/SEARCH_Goods/frontend
nohup python3 -m http.server 5173 > /tmp/frontend.log 2>&1 &

# 重啟後端
pkill -f "uvicorn app:app"
cd /Users/huangchangchi/Documents/SEARCH_Goods/backend
nohup .venv/bin/uvicorn app:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &

# 等待 3 秒
sleep 3

# 驗證服務
curl http://localhost:8000/health
curl -I http://localhost:5173/index.html | head -n 1
```

---

## 📞 技術支援資訊

- 後端日誌：`tail -f /tmp/backend.log`
- 前端日誌：`tail -f /tmp/frontend.log`
- Session 狀態查詢：`GET /api/repair/session/{session_id}/status`
- 訊息記錄查詢：`GET /api/repair/session/{session_id}/messages`

---

## ✅ 驗證成功標準

1. **彈窗自動彈出** - 客服接手後 3-5 秒內顯示
2. **訊息正確顯示** - 看到住戶（藍）、AI（灰）、客服（綠）三種氣泡
3. **發送功能正常** - 住戶輸入訊息後能立即顯示
4. **輪詢機制運作** - Console 每 3 秒顯示輪詢訊息
5. **無 JavaScript 錯誤** - Console 中沒有紅色錯誤訊息
