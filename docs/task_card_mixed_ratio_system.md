# 任務卡：智慧混合分配系統 + 自動化補丁 V4

**任務編號**: TC-20251025-001  
**完成日期**: 2025-10-25  
**提交記錄**: c499de0, c6c5eb0, 16a31e9  

## 任務概述

本次升級實現了後端智慧商品組合推薦系統和前端自動化用戶交互體驗，主要包含：
1. **後端**: 智慧混合分配算法 + 預算約束優化
2. **前端**: V4 雙層攔截系統 + 智慧建議收集
3. **UI**: 自動清理系統提升用戶體驗

## 後端核心算法

### 智慧混合比例計算 (mixed_ratio)

```python
def mixed_ratio(user_text: str, cookie_items: List[Dict], drink_items: List[Dict]) -> float:
    # 基準比例：60% 餅乾 / 40% 飲料
    cookie_ratio = 0.6
    
    # 語意加權 (±10%)
    c_cnt = count_terms(user_text, CAT_KEYWORDS["餅乾類"])
    d_cnt = count_terms(user_text, CAT_KEYWORDS["飲料類"])
    if c_cnt > d_cnt: cookie_ratio += 0.1
    elif d_cnt > c_cnt: cookie_ratio -= 0.1
    
    # 均價修正 (±10%)
    ac, ad = avg_price(cookie_items), avg_price(drink_items)
    if ad >= 1.8 * ac: cookie_ratio -= 0.1  # 飲料貴 → 多給飲料預算
    elif ac >= 1.8 * ad: cookie_ratio += 0.1  # 餅乾貴 → 多給餅乾預算
    
    return max(0.2, min(0.8, cookie_ratio))  # 限制在 [20%, 80%]
```

### 貪婪裝配算法 (pack_under_budget)

```python
def pack_under_budget(items: List[Dict], budget: int, max_items: int = 999):
    # 價格升序排序 (零價優先，然後按價格升序)
    items_sorted = sorted(items, key=lambda x: (x["price"] is None, x["price"] or 10**9))
    
    picked, total = [], 0
    for item in items_sorted:
        price = item["price"] or 0
        # 零價商品直接收入 (促銷品、免費樣品等)
        if price <= 0 and len(picked) < max_items:
            picked.append(item)
        # 有價商品檢查預算約束
        elif price > 0 and total + price <= budget and len(picked) < max_items:
            picked.append(item)
            total += price
    return picked, total
```

## 前端自動化系統

### V4 雙層攔截架構

```javascript
// Fetch 層：自動保存 API 回應
window.fetch = async function(input, init = {}) {
    const res = await origFetch(input, init);
    if (url.includes("/api/chat") && method === "POST") {
        res.clone().json().then(j => window.lastAssistantJson = j);
    }
    return res;
};

// UI 層：事件攔截
document.addEventListener("submit", e => {
    const text = getInputText(e.target);
    if (agreeLex.test(text)) {
        e.preventDefault();
        triggerSearch();  // 立即切換商品模式
    }
}, true);
```

### 智慧建議收集系統

```javascript
function collectAllIdsFromJson(json) {
    // 掃描多種 JSON 結構
    const structures = [
        'suggestion_ids', 'category_suggestions', 
        'groups', 'categories', 'items', 'recommendations'
    ];
    
    // 遞歸掃描，提取 6 位以上數字 ID
    return extractIds(json, structures).slice(0, 60);  // 限制 60 筆
}
```

## 測試用例

### 後端測試場景

| 用戶輸入 | 預期分配 | 驗證點 |
|---------|----------|--------|
| "100元餅乾飲料" | 60元餅乾/40元飲料 | 基準比例 |
| "100元需要很多餅乾少量飲料" | 70元餅乾/30元飲料 | 語意加權+10% |
| "50元餅乾汽水" (飲料均價2倍) | 40元餅乾/60元飲料 | 價格修正+10% |
| "餅乾飲料" (無預算) | 各8筆展示 | 無預算模式 |

### 前端測試場景

| 操作 | 預期結果 | 驗證點 |
|------|----------|--------|
| 輸入"要" → Enter | 立即切換商品模式 | V4 攔截生效 |
| 點擊"1.原建議" | 收集所有 suggestion_ids | 智慧收集 |
| 頁面出現"（隱藏JSON：...）" | 自動清理消失 | UI 清理系統 |

## 性能指標

- **算法複雜度**: O(n log n) - 主要來自排序操作
- **記憶體使用**: 最多載入 60 筆商品資料
- **響應時間**: 
  - 前端攔截: < 50ms
  - 後端分配: < 200ms
  - 總體體驗: < 500ms

## 部署配置

### 環境要求
- **後端**: Python 3.9+, pandas, FastAPI 0.115+
- **前端**: 現代瀏覽器支援 ES2020+ (async/await, MutationObserver)
- **資料**: CSV 格式商品目錄，包含商品名稱、價格、ID 欄位

### 回滾計劃
```bash
# 緊急回滾至上一穩定版本
git reset --hard 16a31e9
git push --force-with-lease origin main

# 或選擇性回滾單一檔案
git checkout 16a31e9 -- backend/fallback/multi_category_party.py
```

## 後續優化方向

1. **機器學習增強**: 基於用戶行為數據調優分配比例
2. **多語言支援**: 擴展關鍵字庫支援英文、其他語言  
3. **個性化推薦**: 考慮用戶偏好歷史
4. **A/B 測試**: 不同算法參數的效果對比
5. **性能監控**: 添加詳細的性能指標追蹤

## 風險評估

| 風險點 | 影響程度 | 緩解措施 |
|-------|----------|----------|
| 算法計算錯誤 | 中 | 詳細單元測試 + 邊界值驗證 |
| 前端兼容性 | 低 | 漸進式增強 + 優雅降級 |
| 性能退化 | 中 | 性能基準測試 + 監控告警 |
| 用戶體驗混亂 | 低 | 充分的用戶測試 + 回滾機制 |

---

**維護責任**: Backend Team (算法) + Frontend Team (用戶體驗)  
**文檔更新**: API 文檔, 用戶手冊需同步更新  
**監控**: 部署後需監控錯誤率、響應時間、用戶滿意度指標
