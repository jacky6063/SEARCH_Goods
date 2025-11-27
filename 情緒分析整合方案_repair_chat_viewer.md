# 情緒分析整合方案 - repair_chat_viewer.html

## 📋 專案資訊

- **目標系統**：`frontend/repair_chat_viewer.html`
- **整合功能**：使用者對話訊息的情緒分析顯示
- **實施策略**：漸進式整合（保留所有現有功能）
- **預計工時**：5-6 天
- **風險等級**：中等

---

## 🎯 整合目標

### 核心目標
1. ✅ 在對話記錄中顯示情緒標籤（不安/急迫/生氣）
2. ✅ 新增情緒統計卡片
3. ✅ 提供情緒篩選功能
4. ✅ 保持 100% 向後相容（不破壞現有功能）

### 非功能性目標
- 🎨 視覺風格統一（沿用現有漸層紫色系）
- ⚡ 效能不衰減（渲染時間增加 < 30%）
- 📱 響應式設計支援
- 🔄 API 向後相容
- 🧪 Mock/實際資料一致（mockData 含 emotion_data，便於本地驗證）

---

## 📦 任務卡清單

### Phase 1：基礎整合（2 天）

#### 任務 1.1：新增 CSS 樣式
**檔案**：`frontend/repair_chat_viewer.html`  
**位置**：`<style>` 區塊末端（第 770 行之前）  
**工作內容**：
```css
/* ==================== 情緒分析樣式 ==================== */

/* 情緒標籤容器 */
.emotion-badges {
    display: inline-flex;
    gap: 6px;
    margin-left: 10px;
    flex-wrap: wrap;
}

/* 情緒標籤基礎樣式 */
.emotion-badge {
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    cursor: help;
    transition: transform 0.2s;
    white-space: nowrap;
}

.emotion-badge:hover {
    transform: scale(1.05);
}

/* 不安程度樣式 */
.emotion-badge.anxiety-high {
    background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%);
    color: white;
}

.emotion-badge.anxiety-medium {
    background: #fff3cd;
    color: #856404;
    border: 2px solid #ffc107;
}

/* 急迫感樣式 */
.emotion-badge.urgency-high {
    background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%);
    color: white;
    animation: pulse-urgency 2s infinite;
}

.emotion-badge.urgency-medium {
    background: #ffe0e0;
    color: #cc0000;
    border: 2px solid #ff4444;
}

@keyframes pulse-urgency {
    0%, 100% { 
        opacity: 1; 
        box-shadow: 0 2px 4px rgba(255, 68, 68, 0.3); 
    }
    50% { 
        opacity: 0.85; 
        box-shadow: 0 4px 12px rgba(255, 68, 68, 0.6); 
    }
}

/* 生氣指數樣式 */
.emotion-badge.anger-high {
    background: linear-gradient(135deg, #e91e63 0%, #c2185b 100%);
    color: white;
}

.emotion-badge.anger-medium {
    background: #fce4ec;
    color: #c2185b;
    border: 2px solid #e91e63;
}

/* 情緒統計卡片特殊樣式 */
.stat-card.emotion-stat {
    background: white;
}

.stat-card.emotion-stat .label {
    font-size: 14px;
    color: #999;
    margin-bottom: 10px;
}

.stat-card.emotion-stat .value {
    font-size: 36px;
    font-weight: bold;
    margin-bottom: 8px;
}

.stat-card.emotion-stat.anxiety .value {
    background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.stat-card.emotion-stat.urgency .value {
    background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.stat-card.emotion-stat.anger .value {
    background: linear-gradient(135deg, #e91e63 0%, #c2185b 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.stat-card.emotion-stat .description {
    font-size: 12px;
    color: #666;
    line-height: 1.4;
}

/* 情緒篩選器 */
.emotion-filter {
    display: flex;
    align-items: center;
    gap: 8px;
}

.emotion-filter label {
    font-size: 14px;
    color: #666;
    font-weight: 500;
}

.emotion-filter select {
    padding: 8px 12px;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    font-size: 14px;
    color: #333;
    background: white;
    cursor: pointer;
    transition: border-color 0.3s;
}

.emotion-filter select:focus {
    outline: none;
    border-color: #667eea;
}

/* 響應式調整 */
@media (max-width: 768px) {
    .emotion-badges {
        margin-left: 0;
        margin-top: 8px;
    }
    
    .emotion-badge {
        font-size: 11px;
        padding: 3px 10px;
    }
}
```

**驗收標準**：
- [ ] CSS 樣式不與現有樣式衝突
- [ ] 在瀏覽器開發者工具中檢查無錯誤
- [ ] 響應式斷點正常運作

---

#### 任務 1.2：新增 JavaScript 輔助函數
**檔案**：`frontend/repair_chat_viewer.html`  
**位置**：`<script>` 區塊內，`formatTime()` 函數之後  
**工作內容**：

```javascript
// ==================== 情緒分析輔助函數 ====================

/**
 * 渲染情緒標籤
 * @param {Object} emotionData - 情緒資料物件
 * @returns {String} HTML 字串
 */
function renderEmotionBadges(emotionData) {
    if (!emotionData) return '';
    
    const badges = [];
    const { anxiety_level, urgency_level, anger_level } = emotionData;
    
    // 不安程度標籤（≥7 顯示）
    if (anxiety_level >= 7) {
        const level = anxiety_level >= 9 ? 'high' : 'medium';
        badges.push(`
            <span class="emotion-badge anxiety-${level}" 
                  title="不安程度: ${anxiety_level}/10&#13;${emotionData.reasoning || ''}">
                😰 不安 ${anxiety_level}
            </span>
        `);
    }
    
    // 急迫感標籤（≥8 顯示）
    if (urgency_level >= 8) {
        const level = urgency_level >= 9 ? 'high' : 'medium';
        badges.push(`
            <span class="emotion-badge urgency-${level}" 
                  title="急迫感: ${urgency_level}/10&#13;${emotionData.reasoning || ''}">
                ⚡ 緊急 ${urgency_level}
            </span>
        `);
    }
    
    // 生氣指數標籤（≥6 顯示）
    if (anger_level >= 6) {
        const level = anger_level >= 8 ? 'high' : 'medium';
        badges.push(`
            <span class="emotion-badge anger-${level}" 
                  title="生氣指數: ${anger_level}/10&#13;${emotionData.reasoning || ''}">
                😠 不滿 ${anger_level}
            </span>
        `);
    }
    
    return badges.length > 0 
        ? `<div class="emotion-badges">${badges.join('')}</div>` 
        : '';
}

/**
 * 安全編碼 emotion_data 供 data-* 使用（避免換行/引號破壞 DOM）
 */
function encodeEmotionData(emotionData) {
    try {
        return encodeURIComponent(JSON.stringify(emotionData));
    } catch (e) {
        return '';
    }
}

/**
 * 還原 data-* 中的 emotion_data
 */
function decodeEmotionData(encoded) {
    if (!encoded) return null;
    try {
        return JSON.parse(decodeURIComponent(encoded));
    } catch (e) {
        return null;
    }
}

/**
 * 計算情緒統計資料
 * @param {Array} messages - 訊息陣列
 * @returns {Object} 統計物件
 */
function calculateEmotionStats(messages) {
    const userMessages = messages.filter(m => m.role === 'user' && m.emotion_data);
    
    if (userMessages.length === 0) {
        return {
            avg_anxiety: 0,
            avg_urgency: 0,
            avg_anger: 0,
            high_emotion_count: 0,
            max_anxiety: 0,
            max_urgency: 0,
            max_anger: 0
        };
    }
    
    let totalAnxiety = 0, totalUrgency = 0, totalAnger = 0;
    let maxAnxiety = 0, maxUrgency = 0, maxAnger = 0;
    let highEmotionCount = 0;
    
    userMessages.forEach(msg => {
        const { anxiety_level, urgency_level, anger_level } = msg.emotion_data;
        
        totalAnxiety += anxiety_level || 0;
        totalUrgency += urgency_level || 0;
        totalAnger += anger_level || 0;
        
        maxAnxiety = Math.max(maxAnxiety, anxiety_level || 0);
        maxUrgency = Math.max(maxUrgency, urgency_level || 0);
        maxAnger = Math.max(maxAnger, anger_level || 0);
        
        // 高情緒：任一指標 ≥8
        if (anxiety_level >= 8 || urgency_level >= 8 || anger_level >= 8) {
            highEmotionCount++;
        }
    });
    
    const count = userMessages.length;
    
    return {
        avg_anxiety: (totalAnxiety / count).toFixed(1),
        avg_urgency: (totalUrgency / count).toFixed(1),
        avg_anger: (totalAnger / count).toFixed(1),
        high_emotion_count: highEmotionCount,
        max_anxiety: maxAnxiety,
        max_urgency: maxUrgency,
        max_anger: maxAnger,
        analyzed_count: count
    };
}

/**
 * 更新情緒統計卡片
 * @param {Object} stats - 統計資料
 */
function updateEmotionStats(stats) {
    // 更新平均不安程度
    const anxietyEl = document.getElementById('avgAnxiety');
    if (anxietyEl) {
        anxietyEl.textContent = stats.avg_anxiety;
    }
    
    // 更新平均急迫感
    const urgencyEl = document.getElementById('avgUrgency');
    if (urgencyEl) {
        urgencyEl.textContent = stats.avg_urgency;
    }
    
    // 更新平均生氣指數
    const angerEl = document.getElementById('avgAnger');
    if (angerEl) {
        angerEl.textContent = stats.avg_anger;
    }
    
    // 更新高情緒訊息數
    const highEmotionEl = document.getElementById('highEmotionCount');
    if (highEmotionEl) {
        highEmotionEl.textContent = stats.high_emotion_count;
    }
}

/**
 * 情緒篩選功能
 * @param {String} filterType - 篩選類型 ('all', 'high', 'urgent', 'angry')
 */
function filterByEmotion(filterType) {
    const messageCards = document.querySelectorAll('.message-card.user');
    
    messageCards.forEach(card => {
        const emotionDataAttr = card.dataset.emotion;
        
        if (filterType === 'all') {
            card.style.display = 'block';
            return;
        }
        
        if (!emotionDataAttr) {
            card.style.display = 'none';
            return;
        }
        
        try {
            const emotionData = decodeEmotionData(emotionDataAttr);
            let shouldShow = false;
            
            switch (filterType) {
                case 'high':
                    // 高風險：任一指標 ≥8
                    shouldShow = (
                        emotionData.anxiety_level >= 8 ||
                        emotionData.urgency_level >= 8 ||
                        emotionData.anger_level >= 8
                    );
                    break;
                case 'urgent':
                    // 極緊急：急迫感 = 10
                    shouldShow = emotionData.urgency_level === 10;
                    break;
                case 'angry':
                    // 生氣：生氣指數 ≥7
                    shouldShow = emotionData.anger_level >= 7;
                    break;
            }
            
            card.style.display = shouldShow ? 'block' : 'none';
        } catch (e) {
            card.style.display = 'none';
        }
    });
}
```

**驗收標準**：
- [ ] 所有函數可正常呼叫
- [ ] 傳入 null/undefined 不會報錯（容錯處理）
- [ ] console 無錯誤訊息
- [ ] 篩選閾值與後端記錄閾值一致（避免前後判定不一致）

---

#### 任務 1.3：修改訊息渲染邏輯（列表頁）
**檔案**：`frontend/repair_chat_viewer.html`  
**位置**：`searchMessagesReal()` 函數內的訊息渲染區塊（約第 1260-1290 行）  
**修改方式**：

**原始碼（第 1272-1276 行）：**
```javascript
const displayRole = msg.role === 'user' ? 'user' : (isOperatorReply ? 'Humans' : 'llm');
const roleIcon = displayRole === 'user' ? '👤' : (displayRole === 'Humans' ? '👩‍💼' : '🤖');
const roleText = displayRole === 'user' ? '使用者' : (displayRole === 'Humans' ? operatorName : '系統回覆');
```

**修改為：**
```javascript
const displayRole = msg.role === 'user' ? 'user' : (isOperatorReply ? 'Humans' : 'llm');
const roleIcon = displayRole === 'user' ? '👤' : (displayRole === 'Humans' ? '👩‍💼' : '🤖');
const roleText = displayRole === 'user' ? '使用者' : (displayRole === 'Humans' ? operatorName : '系統回覆');

// ✨ 新增：渲染情緒標籤（只針對使用者訊息）
const emotionBadges = (displayRole === 'user' && msg.emotion_data) 
    ? renderEmotionBadges(msg.emotion_data) 
    : '';

// ✨ 新增：安全編碼 emotion_data 供 data-* 使用
const emotionDataAttr = msg.emotion_data ? encodeEmotionData(msg.emotion_data) : '';
```

**原始碼（第 1285 行）：**
```javascript
return `
<div class="message-card ${msg.role}">
    <div class="message-header">
        <div class="message-role">
            <span class="icon">${roleIcon}</span>
            <span>${roleText}</span>
        </div>
```

**修改為：**
```javascript
return `
<div class="message-card ${msg.role}" 
     data-emotion='${emotionDataAttr}'>
    <div class="message-header">
        <div class="message-role">
            <span class="icon">${roleIcon}</span>
            <span>${roleText}</span>
            ${emotionBadges}
        </div>
```

**驗收標準**：
- [ ] 有情緒資料的訊息正確顯示標籤
- [ ] 無情緒資料的訊息不顯示標籤
- [ ] 非使用者訊息（llm/Humans）不顯示標籤
- [ ] data-emotion 屬性正確儲存（用於篩選）

---

#### 任務 1.4：修改訊息渲染邏輯（Modal 對話視窗）
**檔案**：`frontend/repair_chat_viewer.html`  
**位置**：`renderChatMessages()` 函數（約第 1463-1530 行）  
**修改方式**：

**原始碼（第 1463-1471 行）：**
```javascript
messagesList.innerHTML = messages.map(msg => {
    if (msg.role === 'user') {
        return `
            <div class="chat-message user-msg">
                <div class="chat-message-content">
                    <div class="chat-bubble">${escapeHtml(msg.content)}</div>
                    <div class="chat-timestamp">${formatTimeShort(msg.created_at)}</div>
                </div>
            </div>
        `;
```

**修改為：**
```javascript
messagesList.innerHTML = messages.map(msg => {
    if (msg.role === 'user') {
        // ✨ 新增：渲染情緒標籤
        const emotionBadgesHtml = msg.emotion_data 
            ? renderEmotionBadges(msg.emotion_data) 
            : '';
        
        return `
            <div class="chat-message user-msg">
                <div class="chat-message-content">
                    ${emotionBadgesHtml ? `<div style="margin-bottom: 8px;">${emotionBadgesHtml}</div>` : ''}
                    <div class="chat-bubble">${escapeHtml(msg.content)}</div>
                    <div class="chat-timestamp">${formatTimeShort(msg.created_at)}</div>
                </div>
            </div>
        `;
```

**驗收標準**：
- [ ] Modal 內的使用者訊息顯示情緒標籤
- [ ] 標籤位置在氣泡上方
- [ ] 不影響對話流暢性

---

### Phase 2：統計功能（1 天）

#### 任務 2.1：擴充統計卡片區 HTML
**檔案**：`frontend/repair_chat_viewer.html`  
**位置**：`.stats-section` 區塊（約第 860-880 行）  
**修改方式**：

**原始碼：**
```html
<div class="stats-section" id="statsSection" style="display: none;">
    <div class="stats-grid">
        <div class="stat-card">
            <div class="label">總訊息數</div>
            <div class="value" id="totalCount">0</div>
        </div>
        <div class="stat-card">
            <div class="label">使用者訊息</div>
            <div class="value" id="userCount">0</div>
        </div>
        <div class="stat-card">
            <div class="label">系統回覆</div>
            <div class="value" id="llmCount">0</div>
        </div>
        <div class="stat-card">
            <div class="label">涉及會話</div>
            <div class="value" id="sessionCount">0</div>
        </div>
    </div>
</div>
```

**修改為：**
```html
<div class="stats-section" id="statsSection" style="display: none;">
    <div class="stats-grid">
        <!-- 現有統計卡片 -->
        <div class="stat-card">
            <div class="label">總訊息數</div>
            <div class="value" id="totalCount">0</div>
        </div>
        <div class="stat-card">
            <div class="label">使用者訊息</div>
            <div class="value" id="userCount">0</div>
        </div>
        <div class="stat-card">
            <div class="label">系統回覆</div>
            <div class="value" id="llmCount">0</div>
        </div>
        <div class="stat-card">
            <div class="label">涉及會話</div>
            <div class="value" id="sessionCount">0</div>
        </div>
        
        <!-- ✨ 新增：情緒統計卡片 -->
        <div class="stat-card emotion-stat anxiety">
            <div class="label">😰 平均不安</div>
            <div class="value" id="avgAnxiety">-</div>
            <div class="description">分析 <span id="analyzedCount">0</span> 則訊息</div>
        </div>
        <div class="stat-card emotion-stat urgency">
            <div class="label">⚡ 平均急迫</div>
            <div class="value" id="avgUrgency">-</div>
            <div class="description">高風險 <span id="highEmotionCount">0</span> 則</div>
        </div>
        <div class="stat-card emotion-stat anger">
            <div class="label">😠 平均生氣</div>
            <div class="value" id="avgAnger">-</div>
            <div class="description">最高值 <span id="maxAnger">0</span></div>
        </div>
    </div>
</div>
```

**驗收標準**：
- [ ] 統計卡片排列整齊（響應式）
- [ ] 新增卡片與現有卡片樣式一致
- [ ] 手機版排版正常（2x4 或 1x7）

---

#### 任務 2.2：整合統計計算邏輯
**檔案**：`frontend/repair_chat_viewer.html`  
**位置**：`searchMessagesReal()` 函數內（約第 1215 行）  
**修改方式**：

**原始碼：**
```javascript
// 更新統計資訊
document.getElementById('totalCount').textContent = result.total_count || data.length;
document.getElementById('userCount').textContent = result.user_count || 0;
document.getElementById('llmCount').textContent = result.llm_count || 0;
document.getElementById('sessionCount').textContent = result.session_count || 0;
statsSection.style.display = 'block';
```

**修改為：**
```javascript
// 更新統計資訊
document.getElementById('totalCount').textContent = result.total_count || data.length;
document.getElementById('userCount').textContent = result.user_count || 0;
document.getElementById('llmCount').textContent = result.llm_count || 0;
document.getElementById('sessionCount').textContent = result.session_count || 0;

// ✨ 新增：計算並更新情緒統計
const emotionStats = calculateEmotionStats(data);
updateEmotionStats(emotionStats);
document.getElementById('analyzedCount').textContent = emotionStats.analyzed_count;
document.getElementById('maxAnger').textContent = emotionStats.max_anger;

statsSection.style.display = 'block';
```

**驗收標準**：
- [ ] 情緒統計數據正確計算
- [ ] 無情緒資料時顯示 "-" 或 "0"
- [ ] 統計卡片即時更新

---

### Phase 3：篩選功能（1 天）

#### 任務 3.1：新增篩選器 HTML
**檔案**：`frontend/repair_chat_viewer.html`  
**位置**：`.query-section` 區塊內（約第 856 行）  
**修改方式**：

**原始碼：**
```html
<div class="query-controls">
    <label for="queryDate">📅 查詢日期：</label>
    <input type="date" id="queryDate" value="2025-11-21">
    <button class="btn-search" onclick="searchMessages()">🔍 查詢</button>
</div>
```

**修改為：**
```html
<div class="query-controls">
    <label for="queryDate">📅 查詢日期：</label>
    <input type="date" id="queryDate" value="2025-11-21">
    
    <!-- ✨ 新增：情緒篩選器 -->
    <div class="emotion-filter">
        <label for="emotionFilter">🎭 情緒篩選：</label>
        <select id="emotionFilter" onchange="filterByEmotion(this.value)">
            <option value="all">全部訊息</option>
            <option value="high">高風險 (≥8)</option>
            <option value="urgent">極緊急 (=10)</option>
            <option value="angry">生氣客戶 (≥7)</option>
        </select>
    </div>
    
    <button class="btn-search" onclick="searchMessages()">🔍 查詢</button>
</div>
```

**驗收標準**：
- [ ] 下拉選單正常運作
- [ ] 響應式設計下不換行混亂
- [ ] 預設選項為"全部訊息"

---

#### 任務 3.2：整合篩選器重置邏輯
**檔案**：`frontend/repair_chat_viewer.html`  
**位置**：`searchMessages()` 函數末端  
**修改方式**：

**在函數末端新增：**
```javascript
async function searchMessagesReal() {
    // ... 現有查詢邏輯 ...
    
    // 查詢完成後，重置篩選器
    const filterSelect = document.getElementById('emotionFilter');
    if (filterSelect) {
        filterSelect.value = 'all';
    }
}
```

**驗收標準**：
- [ ] 每次新查詢時篩選器重置為"全部"
- [ ] 篩選後再查詢不會保留舊篩選狀態

---

### Phase 4：容錯與優化（1 天）

#### 任務 4.1：API 向後相容處理
**檔案**：`frontend/repair_chat_viewer.html`  
**位置**：`renderEmotionBadges()` 函數  
**修改方式**：

```javascript
function renderEmotionBadges(emotionData) {
    // ✅ 容錯：檢查資料有效性
    if (!emotionData || typeof emotionData !== 'object') {
        return '';
    }
    
    // ✅ 容錯：檢查必要欄位
    const anxiety = emotionData.anxiety_level || 0;
    const urgency = emotionData.urgency_level || 0;
    const anger = emotionData.anger_level || 0;
    
    // 如果所有值都是 0，不渲染
    if (anxiety === 0 && urgency === 0 && anger === 0) {
        return '';
    }
    
    // ... 其餘邏輯
}
```

**驗收標準**：
- [ ] 舊版 API 無 emotion_data 欄位不報錯
- [ ] emotion_data 為 null 不報錯
- [ ] emotion_data 格式錯誤不報錯

---

#### 任務 4.2：效能優化
**工作內容**：

1. **減少 DOM 操作**
```javascript
// 使用 DocumentFragment 批次插入
function renderMessages(messages) {
    const fragment = document.createDocumentFragment();
    // ... 渲染邏輯
    messageList.appendChild(fragment);
}
```

2. **延遲渲染情緒標籤**
```javascript
// 只在可視區域內渲染
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            renderEmotionBadges(entry.target);
        }
    });
});
```

3. **快取統計計算結果**
```javascript
let cachedEmotionStats = null;

function getEmotionStats(messages) {
    if (cachedEmotionStats) return cachedEmotionStats;
    cachedEmotionStats = calculateEmotionStats(messages);
    return cachedEmotionStats;
}
```

**驗收標準**：
- [ ] 100 則訊息渲染時間 < 300ms
- [ ] Chrome DevTools Performance 無警告
- [ ] Memory Leak 檢測通過

---

#### 任務 4.3：響應式測試與修正
**測試裝置**：
- iPhone SE (375px)
- iPad (768px)
- Desktop (1200px)

**檢查項目**：
- [ ] 統計卡片排列正常
- [ ] 情緒標籤不換行混亂
- [ ] 篩選器不被遮擋
- [ ] 觸控操作流暢

**修正範例**：
```css
@media (max-width: 480px) {
    .stats-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    
    .emotion-filter {
        width: 100%;
    }
    
    .emotion-filter select {
        width: 100%;
    }
}
```

---

### Phase 5：測試與文件（1 天）

#### 任務 5.1：單元測試
**測試案例**：

```javascript
// 測試案例 1：renderEmotionBadges()
function testRenderEmotionBadges() {
    // Case 1: 有效資料
    const result1 = renderEmotionBadges({
        anxiety_level: 9,
        urgency_level: 10,
        anger_level: 3
    });
    console.assert(result1.includes('不安 9'), 'Case 1 失敗');
    console.assert(result1.includes('緊急 10'), 'Case 1 失敗');
    
    // Case 2: null 資料
    const result2 = renderEmotionBadges(null);
    console.assert(result2 === '', 'Case 2 失敗');
    
    // Case 3: 未達閾值
    const result3 = renderEmotionBadges({
        anxiety_level: 3,
        urgency_level: 5,
        anger_level: 2
    });
    console.assert(result3 === '', 'Case 3 失敗');
    
    console.log('✅ renderEmotionBadges 測試通過');
}

// 測試案例 2：calculateEmotionStats()
function testCalculateEmotionStats() {
    const messages = [
        { role: 'user', emotion_data: { anxiety_level: 9, urgency_level: 10, anger_level: 3 } },
        { role: 'user', emotion_data: { anxiety_level: 5, urgency_level: 6, anger_level: 2 } },
        { role: 'llm', content: '系統回覆' }
    ];
    
    const stats = calculateEmotionStats(messages);
    
    console.assert(stats.analyzed_count === 2, 'analyzed_count 錯誤');
    console.assert(stats.avg_anxiety === '7.0', 'avg_anxiety 錯誤');
    console.assert(stats.high_emotion_count === 1, 'high_emotion_count 錯誤');
    
    console.log('✅ calculateEmotionStats 測試通過');
}

// 測試案例 3：filterByEmotion()
function testFilterByEmotion() {
    // 模擬 DOM
    document.body.innerHTML = `
        <div class="message-card user" data-emotion='{"anxiety_level":9,"urgency_level":10,"anger_level":3}'>高風險</div>
        <div class="message-card user" data-emotion='{"anxiety_level":3,"urgency_level":5,"anger_level":2}'>低風險</div>
    `;
    
    filterByEmotion('high');
    
    const cards = document.querySelectorAll('.message-card.user');
    console.assert(cards[0].style.display === 'block', '高風險應顯示');
    console.assert(cards[1].style.display === 'none', '低風險應隱藏');
    
    console.log('✅ filterByEmotion 測試通過');
}
```

**驗收標準**：
- [ ] 所有測試案例通過
- [ ] Console 無錯誤訊息
- [ ] 邊界條件測試通過

---

#### 任務 5.2：整合測試
**測試流程**：

1. **基本查詢流程**
   - [ ] 選擇日期 → 點擊查詢
   - [ ] 統計卡片正確顯示
   - [ ] 訊息列表正確渲染
   - [ ] 情緒標籤正確顯示

2. **情緒篩選流程**
   - [ ] 選擇"高風險" → 只顯示高風險訊息
   - [ ] 選擇"全部" → 顯示所有訊息
   - [ ] 切換篩選器不影響會話分組

3. **Modal 對話視窗**
   - [ ] 點擊"接手對話" → Modal 開啟
   - [ ] Modal 內訊息顯示情緒標籤
   - [ ] 關閉 Modal → 列表頁狀態不變

4. **容錯測試**
   - [ ] API 回傳無 emotion_data → 不報錯
   - [ ] 網路斷線 → 顯示錯誤訊息
   - [ ] 空資料 → 顯示"查無資料"

---

#### 任務 5.3：撰寫使用者文件
**文件內容**：

```markdown
# 情緒分析功能使用說明

## 功能概述
系統會自動分析使用者訊息的情緒狀態，並以標籤形式顯示：
- 😰 **不安程度** (0-10)：焦慮、擔心、害怕
- ⚡ **急迫感** (0-10)：緊急、需立即處理
- 😠 **生氣指數** (0-10)：憤怒、不滿、抱怨

## 如何查看情緒標籤
1. 選擇查詢日期，點擊"🔍 查詢"
2. 在訊息卡片的使用者名稱旁，會顯示情緒標籤
3. 將滑鼠移到標籤上，可查看詳細分析理由

## 情緒篩選
使用"🎭 情緒篩選"下拉選單，可快速篩選：
- **全部訊息**：顯示所有對話
- **高風險 (≥8)**：任一指標達 8 分以上
- **極緊急 (=10)**：急迫感滿分的訊息
- **生氣客戶 (≥7)**：生氣指數 7 分以上

## 統計資訊
統計卡片會顯示：
- **平均不安**：該日期所有使用者的平均不安程度
- **平均急迫**：平均急迫感 + 高風險訊息數量
- **平均生氣**：平均生氣指數 + 最高值

## 注意事項
- 只有達到閾值的訊息才會記錄情緒資料
- 系統回覆和客服訊息不顯示情緒標籤
- 情緒分析結果僅供內部參考
```

---

## 📊 整合檢查清單

### 功能檢查
- [ ] 情緒標籤正確顯示（列表頁）
- [ ] 情緒標籤正確顯示（Modal）
- [ ] 統計卡片數據正確
- [ ] 篩選功能正常運作
- [ ] 容錯處理完善

### 相容性檢查
- [ ] Chrome 最新版
- [ ] Safari 最新版
- [ ] Firefox 最新版
- [ ] 手機瀏覽器（iOS/Android）

### 效能檢查
- [ ] 100 則訊息渲染 < 300ms
- [ ] 無 Memory Leak
- [ ] 無 Console 錯誤

### 設計檢查
- [ ] 視覺風格統一
- [ ] 響應式設計正常
- [ ] 無排版錯位

### 文件檢查
- [ ] 程式碼註解完整
- [ ] 使用者文件撰寫
- [ ] 技術文件更新

---

## 🔄 回滾計畫

### 如果整合失敗，回滾步驟：
1. 備份整合前的檔案：`cp repair_chat_viewer.html repair_chat_viewer.html.backup`
2. 使用 Git 還原：`git checkout repair_chat_viewer.html`
3. 檢查備份檔案可用性
4. 分析失敗原因，調整方案

### 分階段回滾：
- **Phase 1 失敗**：移除新增的 CSS 和 JS 函數
- **Phase 2 失敗**：隱藏情緒統計卡片（`display: none`）
- **Phase 3 失敗**：移除篩選器 HTML

---

## 📈 後續優化方向

### 短期（1-2 週）
1. 新增情緒趨勢圖表（Chart.js）
2. 即時情緒提醒（WebSocket）
3. 匯出情緒報表（CSV）

### 中期（1-2 月）
1. 訓練專屬情緒分類模型
2. 情緒分析 API 優化（批次處理）
3. 客服績效評估整合

### 長期（3-6 月）
1. 多維度情緒分析（困惑度、感激度）
2. 語音情緒分析整合
3. 預測模型（提前預警高風險對話）

---

## 📞 技術支援

- **整合問題**：Backend Team
- **UI/UX 調整**：Frontend Team
- **API 問題**：API Team
- **緊急問題**：Slack #repair-ai-support

---

**文件版本**：v1.0  
**建立日期**：2025-11-27  
**負責人**：AI Development Team  
**預計完成**：2025-12-03
