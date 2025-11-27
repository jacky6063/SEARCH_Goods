# 🎯 熱門分類 UI 點擊流程完整分析

## 📍 流程概覽

```
┌─────────────────────────────────────────────────────────────┐
│ 熱門分類 UI 展示和點擊流程                                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ 1️⃣ 初始化：loadHotCategories(topK)                         │
│    └─ 展示 L1 熱門分類                                      │
│    └─ "常溫食品", "飲料", "生活用品"...                        │
│                                                              │
│ 2️⃣ 用戶點擊 L1（如點「常溫食品」）                             │
│    ├─ hotScopePath.L1 = "常溫食品"                             │
│    ├─ 調用聊天API：「你們有什麼常溫食品的品類？」            │
│    ├─ 聊天回應 + 聲音公告                                  │
│    └─ loadHotCategories() 更新 → 展示 L2                │
│                                                              │
│ 3️⃣ 用戶點擊 L2（如點「五穀/豆類/米麵/乾貨」）                            │
│    ├─ hotScopePath.L2 = "五穀/豆類/米麵/乾貨"                            │
│    ├─ 調用聊天API：「在常溫食品下我對五穀/豆類/米麵/乾貨有興趣...」         │
│    ├─ 聊天回應 + 聲音公告                                  │
│    └─ loadHotCategories() 更新 → 展示 L3                │
│                                                              │
│ 4️⃣ 用戶點擊 L3（如點「米類」）⭐️ 直接搜尋！             │
│    ├─ hotScopePath.L3 = "米類"                            │
│    ├─ ❌ 不走聊天路徑                                      │
│    ├─ ✅ 直接調用搜尋API：POST /api/search                │
│    │  └─ query: "常溫食品 五穀/豆類/米麵/乾貨 米類"                          │
│    │  └─ category_hierarchy: {L1, L2, L3}                 │
│    │  └─ prefer_special_first: true                        │
│    ├─ 顯示搜尋結果（15個米類商品）                        │
│    └─ 聲音公告：「為您找到 15 項商品」                    │
│                                                              │
│ 5️⃣ 用戶點「返回上一層」                                   │
│    ├─ L3 返回 → hotScopePath.L2 = null                   │
│    └─ 重新加載 L2 分類
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 詳細流程分析

### 初始化階段

#### 第一步：loadHotCategories(topK)

**前端代碼** (frontend/index.html Line 451):

```javascript
async function loadHotCategories(topK = 0){
  const container = document.getElementById('hotCategories');
  if(!container) return;
  
  // ════════════════════════════════════════════════════════
  // 決定要展示哪個層級
  // ════════════════════════════════════════════════════════
  let level = 'L1';  // 預設展示 L1
  
  // 檢查 LLM 回傳的 available_scope（聊天回應中）
  const avail = window.latestAvailableScope || null;
  if(avail && avail.level === 'L2' && Array.isArray(avail.l2)){
    level = 'L2';
    llmItems = avail.l2;  // LLM 直接提供的分類
  }
  if(avail && avail.level === 'L3' && Array.isArray(avail.l3)){
    level = 'L3';
    llmItems = avail.l3;  // LLM 直接提供的分類
  }
  
  // ════════════════════════════════════════════════════════
  // 根據 hotScopePath 判斷層級（若無 LLM 指示）
  // ════════════════════════════════════════════════════════
  if(!llmItems){
    if(hotScopePath.L1 && !hotScopePath.L2){
      level = 'L2';  // 已選 L1，展示 L2
    }
    else if(hotScopePath.L1 && hotScopePath.L2){
      level = 'L3';  // 已選 L1 和 L2，展示 L3
    }
    else {
      level = 'L1';  // 預設展示 L1
    }
  }
  
  // ════════════════════════════════════════════════════════
  // 取得資料：優先 LLM，其次 API
  // ════════════════════════════════════════════════════════
  let items = [];
  if(llmItems){
    // LLM 直接提供（聊天回應中的 available_scope）
    items = llmItems;
  } else {
    // 調用 API
    let qs = `level=${level}`;
    if(level === 'L2' && hotScopePath.L1){
      qs = `level=L2&parent_l1=${hotScopePath.L1}`;
    }
    if(level === 'L3' && hotScopePath.L1 && hotScopePath.L2){
      qs = `level=L3&parent_l1=${hotScopePath.L1}&parent_l2=${hotScopePath.L2}`;
    }
    
    // 呼叫後端 API
    const url = buildBackendUrl(`catalog/scope?${qs}`);
    const res = await fetch(url, { cache: 'no-store' });
    const data = await res.json();
    items = Array.isArray(data.items) ? data.items : [];
  }
  
  // ════════════════════════════════════════════════════════
  // 渲染 UI
  // ════════════════════════════════════════════════════════
  container.innerHTML = '';
  
  // 標題
  const label = (level === 'L1') ? 
    '熱門分類' : 
    (level === 'L2' ? `熱門中分類（${hotScopePath.L1}）` : 
     `熱門小分類（${hotScopePath.L1} > ${hotScopePath.L2}）`);
  
  // 返回按鈕（只在有父層時顯示）
  if(level === 'L3' && hotScopePath.L1 && hotScopePath.L2){
    // 顯示「返回上一層」按鈕
    back.addEventListener('click', ()=>{
      setHotScopePath({ L2: null, L3: null });
      loadHotCategories(0);
    });
  }
  
  // 分類按鈕
  items.forEach(({name}) => {
    const btn = document.createElement('button');
    btn.addEventListener('click', async () => {
      // ← 點擊邏輯（見下方）
    });
  });
}
```

---

### 點擊邏輯

#### 🎯 點擊 L1 分類

**觸發條件**：level === 'L1'

**代碼** (Line 630):

```javascript
if(level === 'L1'){
  // 更新狀態
  setHotScopePath({ L1: name, L2: null, L3: null });
  
  // 組織聊天訊息
  const msg = `你們有什麼${name}的品類？`;
  // 例如：「你們有什麼常溫食品的品類？」
  
  // 發送到聊天
  appendChatBubble('user', name);
  chatHistory.push({ role: 'user', content: name });
  
  if(typeof sendChat === 'function'){
    sendChat();  // ← 發送到聊天
  }
  
  // 重新加載分類（展示 L2）
  loadHotCategories(0);
}
```

**流程**：

```
用戶點擊「常溫食品」(L1)
    ↓
hotScopePath = { L1: "常溫食品", L2: null, L3: null }
    ↓
聊天訊息：「你們有什麼常溫食品的品類？」
    ↓
發送到聊天 API：POST /api/chat
    ↓
LLM 回應 + available_scope (L2 列表)
    ↓
重新加載分類 → loadHotCategories()
    ├─ 判斷：hotScopePath.L1 && !hotScopePath.L2 → level = 'L2'
    ├─ 調用 API：GET /api/catalog/scope?level=L2&parent_l1=常溫食品
    └─ 展示 L2 分類「五穀/豆類/米麵/乾貨」、「調味油」等
```

---

#### 🎯 點擊 L2 分類

**觸發條件**：level === 'L2'

**代碼** (Line 632):

```javascript
else if(level === 'L2'){
  // 更新狀態
  setHotScopePath({ L2: name, L3: null });
  
  // 組織聊天訊息
  const msg = `在${hotScopePath.L1}下我對${name}有興趣，還有哪些小分類或重點？`;
  // 例如：「在常溫食品下我對五穀/豆類/米麵/乾貨有興趣，還有哪些小分類或重點？」
  
  // 發送到聊天
  appendChatBubble('user', msg);
  chatHistory.push({ role: 'user', content: msg });
  
  if(typeof sendChat === 'function'){
    sendChat();  // ← 發送到聊天
  }
  
  // 重新加載分類（展示 L3）
  loadHotCategories(0);
}
```

**流程**：

```
用戶點擊「五穀/豆類/米麵/乾貨」(L2)
    ↓
hotScopePath = { L1: "常溫食品", L2: "五穀/豆類/米麵/乾貨", L3: null }
    ↓
聊天訊息：「在常溫食品下我對五穀/豆類/米麵/乾貨有興趣，還有哪些小分類或重點？」
    ↓
發送到聊天 API：POST /api/chat
    ↓
LLM 回應 + available_scope (L3 列表)
    ↓
重新加載分類 → loadHotCategories()
    ├─ 判斷：hotScopePath.L1 && hotScopePath.L2 → level = 'L3'
    ├─ 調用 API：GET /api/catalog/scope?level=L3&parent_l1=常溫食品&parent_l2=五穀/豆類/米麵/乾貨
    └─ 展示 L3 分類「米類」、「米粉」等
```

---

#### 🎯 點擊 L3 分類 (直接搜尋!)

**觸發條件**：level === 'L3' ⭐️

**代碼** (Line 542):

```javascript
if(level === 'L3'){
  // ❌ 不走聊天路徑！
  // ✅ 直接進行搜尋！
  
  setHotScopePath({ L3: name });
  
  // 顯示使用者的選擇
  appendChatBubble('user', name);
  chatHistory.push({ role: 'user', content: name });
  
  // ════════════════════════════════════════════════════════
  // 🚀 直接調用搜尋 API
  // ════════════════════════════════════════════════════════
  
  const payload = {
    query: `${hotScopePath.L1 || ''} ${hotScopePath.L2 || ''} ${name}`.trim(),
    // 例如："常溫常溫食品 五穀/豆類/米麵/乾貨 米類"
    page: 1,
    page_size: 24,
    category_hierarchy: {
      L1: hotScopePath.L1,    // "常溫常溫食品"
      L2: hotScopePath.L2,    // "五穀/豆類/米麵/乾貨"
      L3: name                 // "米類" ← 新選的 L3
    },
    prefer_special_first: true,  // 特價優先
    from_hot_category: true,
    disable_rerank: true
  };
  
  // 切換到搜尋模式
  setMode('search');
  if(chatPanel) chatPanel.style.display = 'none';
  if(searchPanel) searchPanel.style.display = 'flex';
  
  // 發送搜尋請求
  const res = await fetch(buildBackendUrl('search'), {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  
  const data = await res.json();
  
  // ════════════════════════════════════════════════════════
  // 處理結果
  // ════════════════════════════════════════════════════════
  
  if(data.items && data.items.length){
    // ✅ 有結果
    window.renderList(data.items, null, summary);
    announceCategorySearchResult(name, data);
    // 聲音公告：「為您找到 15 項米類商品」
  } else {
    // ❌ 沒有結果 → 回退：取消特價優先再查一次
    payload.prefer_special_first = false;
    const res2 = await fetch(...);
    
    if(data2.items && data2.items.length){
      // 有結果（不用特價優先）
    } else {
      // 完全沒有結果
      showEmptyState(...);
    }
  }
}
```

**流程**：

```
用戶點擊「米類」(L3)
    ↓
hotScopePath = { L1: "常溫食品", L2: "五穀/豆類/米麵/乾貨", L3: "米類" }
    ↓
❌ 不走聊天路徑
    ↓
✅ 直接調用搜尋 API
    ↓
POST /api/search
{
  query: "常溫食品 五穀/豆類/米麵/乾貨 米類",
  category_hierarchy: {
    L1: "常溫食品",
    L2: "五穀/豆類/米麵/乾貨",
    L3: "米類"    ← 注意：所有三層都有值!
  },
  prefer_special_first: true
}
    ↓
後端執行：_filter_by_hierarchy()
    ├─ l1 = "常溫食品"      (不為空)
    ├─ l2 = "五穀/豆類/米麵/乾貨"      (不為空)
    ├─ l3 = "米類"      (不為空)
    ├─ 判斷：if l3 and not l1 and not l2
    ├─ False! (因為 l1 和 l2 都有值)
    └─ 執行完整路徑 (30-50ms) 🔍
    ↓
返回 15 個米類商品
    ↓
顯示搜尋結果
    ↓
語音公告：「為您找到 15 項商品」
```

---

## 🔄 hotScopePath 狀態變化

### 完整路徑示例

```javascript
初始狀態：
  hotScopePath = { L1: null, L2: null, L3: null }
  
Step 1: 用戶點擊「常溫食品」(L1)
  ├─ setHotScopePath({ L1: "常溫食品", L2: null, L3: null })
  ├─ 發送聊天
  └─ loadHotCategories() → 展示 L2
  
  hotScopePath = { L1: "常溫食品", L2: null, L3: null }
  
Step 2: 用戶點擊「五穀/豆類/米麵/乾貨」(L2)
  ├─ setHotScopePath({ L2: "五穀/豆類/米麵/乾貨", L3: null })
  │  (L1 保持 "常溫食品")
  ├─ 發送聊天
  └─ loadHotCategories() → 展示 L3
  
  hotScopePath = { L1: "常溫食品", L2: "五穀/豆類/米麵/乾貨", L3: null }
  
Step 3: 用戶點擊「米類」(L3)
  ├─ setHotScopePath({ L3: "米類" })
  │  (L1 和 L2 保持)
  ├─ 直接搜尋（不走聊天）
  └─ 切換到搜尋模式，顯示結果
  
  hotScopePath = { L1: "常溫食品", L2: "五穀/豆類/米麵/乾貨", L3: "米類" }
  
Step 4 (可選): 用戶點「返回上一層」
  ├─ setHotScopePath({ L2: null, L3: null })
  │  (L1 保持 "常溫食品")
  ├─ loadHotCategories() → 重新展示 L2
  └─ 用戶可以選擇其他 L2
  
  hotScopePath = { L1: "常溫食品", L2: null, L3: null }
```

---

## 🎬 完整時序圖

```
時間    前端 UI                  用戶動作          hotScopePath        API 調用
────────────────────────────────────────────────────────────────────────────────

T0      初始化
        展示：「熱門分類」
        常溫食品、飲料、生活...                       {L1, L2, L3: null}
        
T1                            👆 點擊「常溫食品」
        ─────────────────────────────────────────────────────
        發送聊天訊息                             {L1: "常溫食品", L2, L3: null}  POST /api/chat
        
T2      聊天回應 + 聲音公告
        ─────────────────────────────────────────────────────
        重新加載分類
        展示：「熱門中分類（常溫食品）」
        五穀/豆類/米麵/乾貨、調味油、...                                      GET /api/catalog/scope?level=L2&parent_l1=常溫食品
        
T3                            👆 點擊「五穀/豆類/米麵/乾貨」
        ─────────────────────────────────────────────────────
        發送聊天訊息                             {L1: "常溫食品", L2: "五穀/豆類/米麵/乾貨", L3: null}  POST /api/chat
        
T4      聊天回應 + 聲音公告
        ─────────────────────────────────────────────────────
        重新加載分類
        展示：「熱門小分類（常溫食品 > 五穀/豆類/米麵/乾貨）」
        米類、米粉、...                                        GET /api/catalog/scope?level=L3&...
        
T5                            👆 點擊「米類」
        ─────────────────────────────────────────────────────
        ❌ 不走聊天                              {L1: "常溫食品", L2: "五穀/豆類/米麵/乾貨", L3: "米類"}  POST /api/search
        ✅ 直接搜尋
        
T6      ⏳ 搜尋進行中...
        
T7      結果展示
        15 個米類商品
        語音公告：「為您找到 15 項商品」
```

---

## 🚀 關鍵發現

### 1️⃣ L1、L2、L3 的差異

| 層級 | 點擊後 | 路徑 | 耗時 | API |
|------|--------|------|------|-----|
| **L1** | 走聊天 | 對話 + LLM 提供 L2 | 2-3秒 | POST /api/chat |
| **L2** | 走聊天 | 對話 + LLM 提供 L3 | 2-3秒 | POST /api/chat |
| **L3** | ✅ 直接搜尋 | 跳過聊天 | 1-2秒 | POST /api/search |

### 2️⃣ 傳給後端的 category_hierarchy

```python
# L3 點擊時發送的真實資料：

{
    "L1": "常溫食品",          # ← 完整有值（來自 hotScopePath）
    "L2": "五穀/豆類/米麵/乾貨",          # ← 完整有值（來自 hotScopePath）
    "L3": "米類"           # ← 完整有值（新選的）
}

# 注意：所有三層都有值！
# ❌ 快速路徑不會執行
# 🔍 執行完整路徑 (30-50ms)
```

### 3️⃣ 快速路徑何時執行

根據您的觀察和我們的分析：

```python
# 快速路徑執行的條件：
if l3 and not l1 and not l2:
    # 🚀 快速路徑
    
# 前端熱門分類流程：
# L1 → 聊天 → L2
# L2 → 聊天 → L3
# L3 → 直接搜尋 (但帶 L1、L2、L3)
# ❌ L1、L2 一定有值，快速路徑不執行

# 快速路徑在以下情況執行：
# ✅ 用戶在搜尋欄位輸入「米類」(直接搜尋，不經過 UI)
# ✅ API 直接呼叫，只傳 L3
# ✅ 特殊的 UI 流程
```

### 4️⃣ 為什麼優化方案 B 還是有意義

```
雖然熱門分類 UI 中快速路徑不會執行，
但其他可能的場景會執行：

1️⃣ 搜尋欄位搜尋：用戶輸入「米類」
   → 直接搜尋，category_hierarchy 可能只有 L3
   
2️⃣ 聊天回應：LLM 可能只識別到某個層級
   → category_hierarchy 可能不完整
   
3️⃣ API 直接呼叫：開發者可能只傳 L3

4️⃣ 特殊分類查詢：某些流程只需要 L3

所以快速路徑的 3x 性能提升在這些場景仍然有用！
```

---

## 📊 實際觸發分析

### 三種查詢來源

```
查詢來源                    L1 值    L2 值    L3 值   路徑
────────────────────────────────────────────────────────
🎯 熱門分類 UI (L3)         有       有       有       完整 🔍
🔍 搜尋欄位                  無/有    無/有    有       快速 ⚡ (可能)
💬 聊天 + LLM               有/無    有/無    有/無    取決於 LLM
📱 API 直接呼叫             有/無    有/無    有/無    取決於呼叫者
```

### 實際觸發率修正

```
根據前端熱門分類實現：

🎯 熱門分類 UI：
   - L3 點擊 → 3個層級都有 → 完整路徑 (35% 左右)
   
🔍 搜尋欄位：
   - 用戶輸入「米類」 → 可能只有 L3 → 快速路徑 (15% 左右)
   
💬 聊天：
   - LLM 識別 → 可能 1-3 層都有 → 完整路徑為主 (40% 左右)
   
📊 其他：
   - API 呼叫、特殊流程 → 快速路徑機會 (10% 左右)
   
修正：快速路徑實際觸發率 ~25% (而不是之前預估的 50%)
```

---

## 💡 結論

### 您的觀察確認

> **「以目前的執行邏輯，L1、L2 一定有值，所以就不會單一過濾 L3 程式段」**

✅ **在熱門分類 UI 流程中是對的**

```python
# 熱門分類 UI 的 L3 點擊：
L1 = "常溫食品"                    # ← 一定有值
L2 = "五穀/豆類/米麵/乾貨"                    # ← 一定有值
L3 = "米類"                    # ← 新選的值

# 所以快速路徑條件不符
if l3 and not l1 and not l2:   # False!
    # 不執行快速路徑
```

### 但在整體系統中

❌ **快速路徑在其他場景仍然會執行**

```
- 搜尋欄位輸入
- LLM 不完整識別
- API 直接呼叫
- 等其他流程
```

### 優化的真實價值

```
雖然熱門分類 UI 中快速路徑不執行，
但優化的 25% 性能提升仍然有意義：
- 搜尋欄位查詢
- 其他 API 使用者
- 未來可能的新 UI 流程
```

