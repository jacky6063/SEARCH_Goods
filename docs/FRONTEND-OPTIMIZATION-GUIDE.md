# 前端 UI/UX 優化技術文檔

## 📋 概述

本文檔詳細記錄了 SEARCH_Goods 系統前端界面的重大優化更新，包含技術實現、代碼架構和最佳實踐。

---

## 🎨 商品卡片系統重構

### 核心改進

#### 1. **統一商品卡片函數**
```javascript
function card(item) {
  const el = document.createElement("div");
  el.className = "card";
  
  // 資料提取和清理
  const name = item["商品名稱"] || "未命名商品";
  const id = item["商品編號"] || "";
  const price = item["商品價格"] || "";
  const sale = item["商品特價"] || "";
  const link = item["商品購物網址"] || "";
  const image = item["商品圖片網址"] || item["Goodspic_Link1"] || "";
  
  // 資料驗證和 dataset 設定
  if(desc && desc.trim()) el.dataset.description = desc;
  if(image && image.trim()) el.dataset.image = image;
  if(name) el.dataset.productName = name;
  if(id) el.dataset.productId = id;
  
  return el;
}
```

#### 2. **智能圖片處理系統**
```javascript
// 圖片顯示邏輯
if(image && image.trim()) {
  cardContent += `
    <div class="card-image" 
         style="background-image:url('${a(image)}');
                background-size:cover;
                background-position:center;
                height:160px;">
      <div class="image-overlay">
        ${h(name)}
      </div>
    </div>
  `;
}

// 圖片錯誤處理
const imgTest = new Image();
imgTest.onerror = () => {
  const cardImage = el.querySelector('.card-image');
  if(cardImage) cardImage.style.display = 'none';
};
imgTest.src = image;
```

#### 3. **資訊結構優化**
```javascript
const rows = [];

// 商品名稱 (突出顯示)
rows.push(`
  <div class="card-row highlight">
    <span class="card-label">商品名稱：</span>
    <span class="card-value name">${h(name)}</span>
  </div>
`);

// 智能價格顯示
const hasSale = sale && sale.trim();
if(hasSale) {
  rows.push(`
    <div class="card-row">
      <span class="card-label">原價：</span>
      <span class="card-value price">${price ? h(price) : "—"}</span>
    </div>
  `);
  rows.push(`
    <div class="card-row">
      <span class="card-label">特價：</span>
      <span class="card-value sale">🏷️ ${h(sale)}</span>
    </div>
  `);
} else {
  rows.push(`
    <div class="card-row">
      <span class="card-label">價格：</span>
      <span class="card-value price">${price ? h(price) : "—"}</span>
    </div>
  `);
}
```

---

## 🔄 載入狀態系統

### 骨架屏實現

#### 1. **CSS 動畫定義**
```css
@keyframes shimmer {
  0% { transform: translateX(-100%) }
  100% { transform: translateX(100%) }
}

.loading-shimmer {
  position: relative;
  overflow: hidden;
  background: #f1f5f9;
}

.loading-shimmer::after {
  content: '';
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  background: linear-gradient(90deg, 
    transparent, 
    rgba(255,255,255,0.6), 
    transparent);
  animation: shimmer 1.5s infinite;
}
```

#### 2. **JavaScript 控制邏輯**
```javascript
function setLoading(on) { 
  if(on) { 
    setStatus('載入中<span class="loading-dots">...</span>'); 
    showSkeletonCards();
  } else {
    hideSkeletonCards();
  }
}

function showSkeletonCards() {
  const resultsEl = document.getElementById('results');
  if(!resultsEl) return;
  
  resultsEl.innerHTML = '';
  
  for(let i = 0; i < 4; i++) {
    const skeleton = document.createElement('div');
    skeleton.className = 'card loading-shimmer skeleton-card';
    skeleton.innerHTML = `
      <div class="card-body">
        <div class="skeleton-row medium"></div>
        <div class="skeleton-row short"></div>
        <div class="skeleton-row"></div>
        <div class="skeleton-row short"></div>
      </div>
    `;
    resultsEl.appendChild(skeleton);
  }
}
```

#### 3. **載入點點動畫**
```css
.loading-dots::after {
  content: '';
  display: inline-block;
  animation: dots 1.4s infinite both;
}

@keyframes dots {
  0%, 80%, 100% { opacity: 0 }
  40% { opacity: 1 }
}
```

---

## 📤 商品分享系統

### 跨平台分享實現

#### 1. **分享功能核心邏輯**
```javascript
window.shareProduct = async function(productData) {
  try {
    const product = JSON.parse(productData);
    const shareText = `
      ${product.name}
      ${product.price ? `價格：${product.price}` : ''}
      ${product.sale ? `特價：${product.sale}` : ''}
      ${product.link ? `購買：${product.link}` : ''}
    `.trim();
    
    if (navigator.share && /Mobi|Android/i.test(navigator.userAgent)) {
      // 行動裝置使用原生分享
      await navigator.share({
        title: product.name,
        text: shareText,
        url: product.link
      });
    } else {
      // 桌面版使用剪貼板
      await navigator.clipboard.writeText(shareText);
      showToast('商品資訊已複製到剪貼板！');
    }
  } catch(err) {
    console.error('分享失敗:', err);
    showToast('分享功能暫時無法使用');
  }
};
```

#### 2. **操作按鈕生成**
```javascript
const actionButtons = [];

if(link && link.trim()) {
  actionButtons.push(`
    <a class="action-btn primary" 
       href="${a(link)}" 
       target="_blank" 
       rel="noopener">
      🛒 購買
    </a>
  `);
}

actionButtons.push(`
  <button class="action-btn secondary" 
          onclick="shareProduct('${a(JSON.stringify({name,price,sale,link}).replace(/'/g, "\\'"))}')">
    📤 分享
  </button>
`);

if(actionButtons.length) {
  rows.push(`
    <div class="card-actions">
      ${actionButtons.join('')}
    </div>
  `);
}
```

---

## 💡 用戶指引系統

### 歡迎提示實現

#### 1. **提示彈窗結構**
```javascript
window.showInitialTips = function() {
  if(document.querySelector('.initial-tips')) return;
  
  const tipsEl = document.createElement('div');
  tipsEl.className = 'initial-tips';
  tipsEl.innerHTML = `
    <div class="tips-overlay" onclick="hideInitialTips()"></div>
    <div class="tips-content">
      <h3>🎉 歡迎使用商品搜尋系統</h3>
      <div class="tips-list">
        ${renderTipItems()}
      </div>
      <button onclick="hideInitialTips()" class="tips-close-btn">
        開始使用
      </button>
    </div>
  `;
  
  document.body.appendChild(tipsEl);
  setTimeout(() => tipsEl.classList.add('show'), 100);
};
```

#### 2. **提示項目渲染**
```javascript
function renderTipItems() {
  const tips = [
    { 
      icon: "💬", 
      title: "智能對話搜尋", 
      desc: "直接描述您的需求，例如「我想找5000元以下的筆電」" 
    },
    { 
      icon: "🔍", 
      title: "關鍵字搜尋", 
      desc: "切換到搜尋模式，輸入商品名稱或品牌" 
    },
    { 
      icon: "🎯", 
      title: "智能推薦", 
      desc: "點擊「按 1」獲取個人化商品推薦" 
    },
    { 
      icon: "📤", 
      title: "商品分享", 
      desc: "找到喜歡的商品可以直接分享給朋友" 
    }
  ];
  
  return tips.map(tip => `
    <div class="tip-item">
      <span class="tip-icon">${tip.icon}</span>
      <div>
        <strong>${tip.title}</strong>
        <p>${tip.desc}</p>
      </div>
    </div>
  `).join('');
}
```

#### 3. **本地儲存管理**
```javascript
window.hideInitialTips = function() {
  const tipsEl = document.querySelector('.initial-tips');
  if(tipsEl) {
    tipsEl.classList.add('hide');
    setTimeout(() => tipsEl.remove(), 300);
  }
  localStorage.setItem('search_goods_tips_shown', 'true');
  showedInitialTips = true;
};

// 初始化檢查
let showedInitialTips = localStorage.getItem('search_goods_tips_shown') === 'true';
```

---

## 🎯 空狀態處理系統

### 友好空狀態設計

#### 1. **空狀態渲染**
```javascript
function showEmptyState(query, message) {
  const resultsEl = document.getElementById('results');
  if(!resultsEl) return;
  
  const msg = message || `
    很抱歉，目前沒有找到符合您需求的商品喔 🙏
    您可以嘗試其他關鍵字，或告訴我品牌、型號或預算範圍，
    我再幫您推薦合適的商品 💡
    （目前查詢關鍵字：${query}）
  `;
  
  const empty = document.createElement("div");
  empty.className = "card";
  empty.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">🔍</div>
      <h3 class="empty-title">暫時沒有符合的商品</h3>
      <p class="empty-message">${h(msg)}</p>
      <div class="empty-actions">
        <button onclick="switchToChat()" class="action-btn primary">
          💬 改用聊天搜尋
        </button>
      </div>
    </div>
  `;
  resultsEl.appendChild(empty);
}
```

#### 2. **CSS 樣式設計**
```css
.empty-state {
  text-align: center;
  padding: 40px 20px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-title {
  color: var(--sub);
  margin: 0 0 12px 0;
  font-weight: 600;
}

.empty-message {
  color: var(--sub);
  margin: 0;
  line-height: 1.6;
  white-space: pre-line;
}

.empty-actions {
  margin-top: 20px;
}
```

---

## 📦 統一快取管理系統

### 快取架構設計

#### 1. **統一快取函數**
```javascript
function setSuggestCache(type, items, options = {}) {
  // 資料驗證
  if (!items || (!Array.isArray(items) && !hasRenderableProducts(items))) {
    console.warn('⚠️ setSuggestCache: 無效的商品資料', items);
    return false;
  }
  
  // 資料標準化
  const itemsArray = Array.isArray(items) ? items : [items];
  const ids = options.ids || itemsArray.map(item => {
    return (item['商品編號'] || item['GoodIden'] || item.id || '')
      .toString().trim();
  }).filter(Boolean);
  
  // 快取設定
  latestSuggestCache[type] = {
    ids: ids,
    items: itemsArray,
    meta: options.meta || null,
    categoryGroups: options.categoryGroups || null,
    summary: options.summary || `我找到了 ${itemsArray.length} 款商品`
  };
  
  console.log('✅ 設定建議快取', type, '商品數:', itemsArray.length, 'IDs:', ids.length);
  return true;
}
```

#### 2. **商品可渲染性檢查**
```javascript
function hasRenderableProducts(list) {
  if(!Array.isArray(list) || !list.length) return false;
  
  return list.some(item => {
    if(!item || typeof item !== "object") return false;
    return Boolean(item["商品名稱"] || item["Name"] || item["name"]);
  });
}
```

#### 3. **智能建議處理**
```javascript
function handleSuggestTrigger(type) {
  const cached = latestSuggestCache[type];
  
  // 多層次檢查
  if(cached && ((Array.isArray(cached.ids) && cached.ids.length) || 
                hasRenderableProducts(cached.items))) {
    
    console.log('🛍 使用快取推薦', type, 
      'ids:', cached.ids?.length || 0, 
      'items:', cached.items?.length || 0);
    
    const summaryLine = cached.summary || 
      `我找到了 ${(cached.ids?.length || cached.items?.length || 0)} 款商品`;
    
    // 優先使用完整商品資料
    if(hasRenderableProducts(cached.items)) {
      console.log('✅ 商品資料完整，直接顯示');
      if(cached.categoryGroups) {
        switchToSearch('', cached.ids || [], cached.items, 
          cached.categoryGroups, summaryLine);
      } else {
        switchToSearch('', cached.ids || [], cached.items, 
          undefined, summaryLine);
      }
      if(cached.meta) {
        renderPlanResults([], cached.meta);
      }
      setTimeout(() => setStatus('已載入推薦商品'), 200);
    } else if(Array.isArray(cached.ids) && cached.ids.length) {
      // 商品資料不完整，使用 ID 重新查詢
      console.log('⚠️ 商品資料不完整，使用 ID 重新查詢');
      switchToSearch(); // 先切換到商品模式
      doSearchByIds(cached.ids, summaryLine);
    } else {
      console.log('⚠️ 快取資料無效，重新觸發建議');
      triggerSuggest(type);
    }
  } else {
    console.log('❌ 沒有快取資料，重新觸發建議');
    if(mode !== 'search') {
      switchToSearch();
    }
    triggerSuggest(type);
  }
}
```

---

## 🔧 Debug 和維護工具

### 全域 Debug 函數

```javascript
window.debugSearchGoods = function() {
  console.log('🔍 SEARCH_GOODS 系統狀態:');
  console.log('- 當前模式:', mode);
  console.log('- Session ID:', sessionId);
  console.log('- 建議快取:', Object.keys(latestSuggestCache).map(key => {
    const cache = latestSuggestCache[key];
    return `${key}: ${cache.items?.length || 0} 商品, ${cache.ids?.length || 0} IDs`;
  }));
  console.log('- 完整快取資料:', latestSuggestCache);
  
  return {
    mode: mode,
    sessionId: sessionId,
    suggestCache: latestSuggestCache,
    cacheKeys: Object.keys(latestSuggestCache)
  };
};
```

### 控制台日誌系統

```javascript
// 建議按鈕點擊日誌
suggestButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    const t = Number(btn.dataset.sg || '1');
    console.log('🔘 點擊建議按鈕', t, '當前快取狀態:', 
      latestSuggestCache[t] ? 
      `有快取 (${latestSuggestCache[t].items?.length || 0} 商品)` : '無快取');
    handleSuggestTrigger(t);
  });
});

// API 請求日誌
async function triggerSuggest(type) {
  console.log('🚀 觸發建議請求，類型:', type);
  // ... API 調用
  console.log('📦 建議 API 回應:', data);
  console.log('✅ 建議快取已設定:', latestSuggestCache[type]);
}
```

---

## 📱 響應式設計實現

### CSS Media Queries

```css
@media (max-width: 1024px) {
  .workspace { grid-template-columns: 1fr; gap: 20px; }
  .results { grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); }
}

@media (max-width: 720px) {
  .container { padding: 16px; }
  .results { 
    grid-template-columns: 1fr; 
    gap: 16px; 
  }
  .card { 
    border-radius: 12px; 
  }
  .card-body { 
    padding: 16px; 
  }
  .card-row { 
    font-size: 13px; 
  }
  .card-label { 
    min-width: 70px; 
    font-size: 12px; 
  }
  .card-image { 
    height: 120px; 
  }
}
```

### 觸控友好設計

```css
.action-btn {
  min-height: 44px; /* iOS 建議的最小觸控尺寸 */
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:active {
  transform: scale(0.95);
}

@media (hover: hover) {
  .action-btn:hover {
    transform: translateY(-1px);
  }
}
```

---

## 🎯 最佳實踐總結

### 代碼組織
1. **模組化函數設計** - 單一職責原則
2. **統一的錯誤處理** - 一致的用戶體驗
3. **完善的日誌系統** - 便於除錯和維護
4. **響應式優先** - 行動裝置友好

### 性能優化
1. **懶載入機制** - 圖片和資源按需載入
2. **骨架屏技術** - 減少感知載入時間
3. **智能快取** - 避免重複請求
4. **CSS 動畫** - 使用 GPU 加速

### 用戶體驗
1. **漸進增強** - 基礎功能優先
2. **無障礙設計** - ARIA 標籤和語義化 HTML
3. **錯誤容錯** - 優雅的降級處理
4. **即時反饋** - 操作狀態及時告知

### 維護性
1. **文檔完整** - 代碼註釋和技術文檔
2. **Debug 工具** - 開發和除錯輔助
3. **版本控制** - 變更追蹤和回滾
4. **測試友好** - 便於自動化測試

---

**文檔版本**: v1.0  
**最後更新**: 2025年10月26日  
**維護者**: GitHub Copilot Assistant