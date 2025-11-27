# YouTube 預覽行為更新說明

**更新日期**: 2025年11月9日  
**版本**: v2.0  
**變更類型**: 功能調整

---

## 📋 變更摘要

**移除「開新視窗」行為，改為直接在左側播放器播放 YouTube 影片**

---

## 🔄 變更內容

### 之前的行為 (v1.0)

點擊聊天室中的 YouTube 連結時：
1. ✅ 開啟新分頁到 YouTube 網站
2. ✅ 同時更新左側播放器

**問題**:
- 使用者會被帶離當前頁面
- 需要切換分頁才能繼續對話
- 體驗不夠流暢

### 現在的行為 (v2.0)

點擊聊天室中的 YouTube 連結時：
1. ✅ **只在左側播放器播放影片**
2. ❌ **不開啟新分頁**

**優點**:
- ✅ 使用者留在當前頁面
- ✅ 可以邊看影片邊繼續對話
- ✅ 更流暢的使用體驗
- ✅ 減少分頁切換

---

## 🔧 技術實作

### 程式碼變更

#### 之前 (v1.0):
```javascript
chatMessagesEl.addEventListener('click', (event)=>{
  const anchor = event.target.closest('a');
  if(!anchor){ return; }
  const href = anchor.getAttribute('href') || "";
  if(!YOUTUBE_LINK_RE.test(href)){ return; }
  // 保留原先開新分頁的行為，同時更新左側播放器
  setTimeout(()=>applyYoutube(href), 0);
  // ⚠️ 沒有 preventDefault()，所以會執行 <a> 的預設行為（開新視窗）
});
```

#### 現在 (v2.0):
```javascript
chatMessagesEl.addEventListener('click', (event)=>{
  const anchor = event.target.closest('a');
  if(!anchor){ return; }
  const href = anchor.getAttribute('href') || "";
  if(!YOUTUBE_LINK_RE.test(href)){ return; }
  // 🚫 阻止開新視窗的預設行為
  event.preventDefault();
  // ✅ 直接在左側播放器播放
  applyYoutube(href);
});
```

### 關鍵變更點

1. **新增 `event.preventDefault()`**:
   - 阻止 `<a>` 標籤的預設行為（開新視窗）
   - 確保點擊連結不會跳轉頁面

2. **移除 `setTimeout()`**:
   - 因為不需要等待新視窗開啟
   - 直接同步執行 `applyYoutube(href)`

3. **更新註釋**:
   - 明確說明「不開新視窗」的設計意圖

---

## 🧪 測試驗證

### 測試場景

#### 場景 1: 點擊 YouTube 連結

**操作步驟**:
1. 在聊天輸入可能產生 YouTube 連結的查詢
2. 點擊回應中的 YouTube 連結

**預期結果**:
- ✅ 左側播放器立即播放點擊的影片
- ✅ 當前頁面不跳轉
- ✅ 沒有開啟新分頁
- ✅ 可以繼續在聊天室對話

#### 場景 2: 點擊多個不同的 YouTube 連結

**操作步驟**:
1. 點擊第一個 YouTube 連結
2. 等待播放器更新
3. 點擊第二個不同的 YouTube 連結

**預期結果**:
- ✅ 每次點擊都更新播放器
- ✅ 沒有開啟任何新分頁
- ✅ 頁面保持在當前狀態

#### 場景 3: 點擊非 YouTube 連結

**操作步驟**:
1. 點擊聊天室中的一般網址連結（非 YouTube）

**預期結果**:
- ✅ 正常開啟新分頁（此行為不受影響）
- ✅ 播放器不變

#### 場景 4: 重新載入頁面

**操作步驟**:
1. 點擊 YouTube 連結後播放影片
2. 重新載入頁面 (Cmd+R)

**預期結果**:
- ✅ 播放器回復到管理面板設定的預設影片
- ✅ 不保留使用者點擊的影片（符合預期）

---

## 📊 使用者體驗比較

| 項目 | v1.0 (開新視窗) | v2.0 (直接播放) |
|-----|----------------|----------------|
| **頁面跳轉** | ❌ 會跳轉到 YouTube | ✅ 保持在當前頁面 |
| **分頁管理** | ❌ 需要管理多個分頁 | ✅ 只有一個分頁 |
| **繼續對話** | ❌ 需要切回分頁 | ✅ 可立即繼續 |
| **影片播放** | ✅ YouTube 網站播放 | ✅ 左側播放器播放 |
| **全螢幕觀看** | ✅ YouTube 提供 | ⚠️ 有限制* |
| **影片控制** | ✅ 完整控制 | ⚠️ 基本控制** |

\* 播放器可以全螢幕，但需要點擊 iframe 內的全螢幕按鈕  
\** iframe 播放器提供基本的播放、暫停、音量控制

---

## 🔄 如何恢復舊行為

如果需要恢復「開新視窗」的行為，請執行以下修改：

### 選項 A: 完全恢復（同時開新視窗和播放）

```javascript
chatMessagesEl.addEventListener('click', (event)=>{
  const anchor = event.target.closest('a');
  if(!anchor){ return; }
  const href = anchor.getAttribute('href') || "";
  if(!YOUTUBE_LINK_RE.test(href)){ return; }
  // ⚠️ 不使用 preventDefault()，保留開新視窗
  setTimeout(()=>applyYoutube(href), 0);
});
```

### 選項 B: 讓使用者選擇

添加一個設定選項：
```javascript
const OPEN_YOUTUBE_IN_NEW_TAB = false; // 設定為 true 可開新視窗

chatMessagesEl.addEventListener('click', (event)=>{
  const anchor = event.target.closest('a');
  if(!anchor){ return; }
  const href = anchor.getAttribute('href') || "";
  if(!YOUTUBE_LINK_RE.test(href)){ return; }
  
  if(!OPEN_YOUTUBE_IN_NEW_TAB){
    event.preventDefault(); // 只在不開新視窗時阻止
  }
  
  applyYoutube(href);
});
```

---

## 💡 未來改進建議

### 1. 添加「在 YouTube 觀看」按鈕

在播放器旁邊添加一個按鈕，讓使用者可以選擇在 YouTube 網站觀看：

```html
<div class="player-controls">
  <button onclick="openInYouTube()">
    🎬 在 YouTube 觀看
  </button>
</div>
```

### 2. 記住使用者偏好

使用 `localStorage` 記住使用者的觀看偏好：

```javascript
const userPreference = localStorage.getItem('youtube_open_behavior') || 'player';
// 'player' = 左側播放器
// 'new_tab' = 開新視窗
```

### 3. 右鍵選單

提供右鍵選單讓使用者選擇：
- 「在播放器觀看」
- 「在 YouTube 觀看」
- 「複製連結」

---

## 📝 相關文檔

- [YOUTUBE_PREVIEW_FIX_REPORT.md](./YOUTUBE_PREVIEW_FIX_REPORT.md) - 語法錯誤修復報告
- [YOUTUBE_PREVIEW_UPDATE_REPORT.md](./YOUTUBE_PREVIEW_UPDATE_REPORT.md) - 原始功能說明

---

## ✅ 變更總結

| 項目 | 狀態 |
|-----|------|
| **移除開新視窗行為** | ✅ 完成 |
| **保留播放器預覽** | ✅ 完成 |
| **更新註釋說明** | ✅ 完成 |
| **測試驗證** | ⏳ 待執行 |
| **文檔更新** | ✅ 完成 |

---

**變更理由**: 提供更流暢的使用體驗，讓使用者無需離開當前頁面即可觀看影片  
**影響範圍**: 只影響聊天室中的 YouTube 連結點擊行為  
**向後相容**: 不影響其他連結的行為，管理面板設定功能保持不變
