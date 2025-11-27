# 商品卡「信心度」資料流程分析

## 概述

商品卡中的「信心度」欄位用於指示商品分類層級匹配的可信度。有兩種機制提供信心度數據：

1. **`hierarchy_score`**: 基於分類層級匹配數量的簡單分數 (所有查詢都有)
2. **`hierarchy_confidence`**: 詳細的信心度指標 (L1/L2/L3 個別分數，目前為結構預留)

---

## 前端資料取得 (frontend/index.html)

### 資料來源位置

**Line 1521-1522**：從後端返回的商品物件中提取
```javascript
const hierarchyScore = item["hierarchy_score"] || item["matched_levels"] ? (item["hierarchy_score"] || 0.8) : null;
const hierarchyConfidence = item["hierarchy_confidence"] || null;
```

### 資料結構

```javascript
// 商品物件返回格式
{
  "商品編號": "4712834520154",
  "商品名稱": "歐特有機小米/480g",
  "CateName_L1": "常溫食品",
  "CateName_L2": "五穀/豆類/米麵/乾貨",
  "CateName_L3": "米類",
  
  // 信心度相關欄位
  "matched_levels": ["L1", "L2", "L3"],      // ← 匹配的分類層級
  "hierarchy_score": 9,                       // ← 分數 (matched_levels.length * 3)
  "hierarchy_confidence": null                // ← 詳細信心度 (暫未使用)
}
```

### 顯示邏輯 (Line 1562-1587)

```javascript
// 🎯 LLM 步驟 6: 添加信心度指標
if(hierarchyScore !== null || hierarchyConfidence) {
  let confidenceHtml = '<div class="card-row"><span class="card-label">信心度：</span>';
  
  if(hierarchyConfidence) {
    // 🔵 情況 1：有詳細信心度 (目前不使用)
    const L1Conf = hierarchyConfidence.L1 || 0;    // L1 層級信心度 (0-1)
    const L2Conf = hierarchyConfidence.L2 || 0;    // L2 層級信心度 (0-1)
    const L3Conf = hierarchyConfidence.L3 || 0;    // L3 層級信心度 (0-1)
    const avgConf = Math.round((L1Conf + L2Conf + L3Conf) / 3 * 100);
    // 顯示平均百分比
    
  } else if(hierarchyScore !== null) {
    // 🟢 情況 2：使用簡單分數 (目前使用)
    const scorePercent = Math.round(hierarchyScore * 100);
    // 顯示百分比
  }
  
  // 根據分數選擇顏色
  const confColor = avgConf >= 80 ? '#10b981' : avgConf >= 60 ? '#f59e0b' : '#ef4444';
  // 綠色(≥80%) → 黃色(≥60%) → 紅色(<60%)
}
```

### 顯示樣式

```
信心度：[█████████████████████ 90%]    ← 綠色 (≥80%)
信心度：[██████████████░░░░░░░░ 65%]   ← 黃色 (60-79%)
信心度：[██████░░░░░░░░░░░░░░░░ 45%]   ← 紅色 (<60%)
```

---

## 後端資料生成 (backend/app.py)

### 生成位置 1: `_annotate_hierarchy()` 函數 (Line 507-538)

**功能**：為單個商品記錄添加分類匹配資訊

```python
def _annotate_hierarchy(record: Dict[str, Any], hierarchy: Dict[str, str]) -> Dict[str, Any]:
    """Annotate a single record with matched_levels and hierarchy_score"""
    
    # 輸入：hierarchy = {"L1": "常溫食品", "L2": "五穀/豆類/米麵/乾貨", "L3": "米類"}
    
    matched: List[str] = []
    
    # 檢查 L1 是否匹配
    if l1:  # "常溫食品"
        v = record.get("CateName_L1")  # "常溫食品"
        if v and (l1 in v):
            matched.append("L1")  # ✓ 匹配
    
    # 檢查 L2 是否匹配
    if l2:  # "五穀/豆類/米麵/乾貨"
        v = record.get("CateName_L2")  # "五穀/豆類/米麵/乾貨"
        if v and (l2 in v):
            matched.append("L2")  # ✓ 匹配
    
    # 檢查 L3 是否匹配
    if l3:  # "米類"
        v = record.get("CateName_L3")  # "米類"
        if v and (l3 in v):
            matched.append("L3")  # ✓ 匹配
    
    # 生成分數
    record["matched_levels"] = matched          # ["L1", "L2", "L3"]
    record["hierarchy_score"] = len(matched) * 3  # 9 (3 * 3)
    
    return record
```

### 計分邏輯

| 匹配層級 | `matched_levels` | `hierarchy_score` | 百分比 | 顏色 |
|---------|------------------|------------------|--------|------|
| L1, L2, L3 都匹配 | `["L1","L2","L3"]` | 9 | 100% | 🟢 綠 |
| L1, L2 匹配 | `["L1","L2"]` | 6 | 67% | 🟡 黃 |
| 只有 L1 匹配 | `["L1"]` | 3 | 33% | 🔴 紅 |
| 無匹配 | `[]` | 0 | 0% | 灰 |

### 生成位置 2: `_filter_by_hierarchy()` 函數 (Line 541-640)

**功能**：對所有搜尋結果應用分類過濾，並為每個記錄添加分類匹配資訊

```python
def _filter_by_hierarchy(records: List[Dict[str, Any]], hierarchy: Optional[Dict[str, str]], from_hot_category: bool = False) -> List[Dict[str, Any]]:
    """Filter records by hierarchy and annotate with matched_levels"""
    
    if not hierarchy:
        return records  # 無分類要求，不添加信心度
    
    # 🔍 完整路徑：逐層驗證
    filtered = []
    for rec in records:
        # 為每個記錄添加分類匹配資訊
        rec = _annotate_hierarchy(rec, hierarchy)
        
        # 檢查是否通過分類過濾
        if _passes_hierarchy_filter(rec, hierarchy):
            filtered.append(rec)
    
    return filtered
```

---

## 資料流程圖

```
用戶搜尋
  ↓
前端調用 /api/search
  ├─ query: "米類"
  ├─ category_hierarchy: {L1: "常溫食品", L2: "五穀/豆類/米麵/乾貨", L3: "米類"}
  └─ from_hot_category: true
  ↓
後端 /api/search 端點
  ├─ 步驟 1: 執行全文搜尋 → 9 個商品
  ├─ 步驟 2: 應用 _filter_by_hierarchy()
  │  ├─ 為每個商品調用 _annotate_hierarchy()
  │  ├─ 檢查 L1/L2/L3 是否匹配
  │  ├─ 計算 hierarchy_score
  │  └─ 過濾符合條件的商品 → 6 個商品
  └─ 步驟 3: 返回結果
     ├─ 商品 1: matched_levels=["L1","L2","L3"], hierarchy_score=9
     ├─ 商品 2: matched_levels=["L1","L2","L3"], hierarchy_score=9
     └─ ...
  ↓
前端接收 JSON
  ├─ items: [商品1, 商品2, ...]
  └─ 每個商品包含 hierarchy_score
  ↓
前端渲染商品卡
  ├─ 提取 hierarchy_score
  ├─ 計算百分比: Math.round(hierarchy_score * 100)
  ├─ 根據分數選擇顏色
  └─ 顯示「信心度：[進度條] XX%」
```

---

## 現況與限制

### 🟢 已實現
- ✅ `hierarchy_score`: 基於匹配層級數量的簡單分數
- ✅ `matched_levels`: 記錄匹配的層級
- ✅ 前端顯示信心度百分比和進度條
- ✅ 顏色編碼：綠(≥80%) → 黃(≥60%) → 紅(<60%)

### 🔵 預留結構
- ⚠️ `hierarchy_confidence`: 詳細的 L1/L2/L3 個別信心度 (目前為 `null`)
  - 預留用於未來 LLM 集成
  - 可用於顯示「L1匹配度 90%, L2匹配度 85%, L3匹配度 95%」

### 🔴 未實現功能
- ❌ LLM 信心度計分：使用 LLM 評估分類匹配的可信度
- ❌ 相似度評分：計算商品名稱與查詢的語義相似度
- ❌ 動態權重：基於用戶行為調整信心度權重

---

## 代碼實現示例

### 後端如何生成 (Python)

```python
# Step 1: 搜尋得到 9 個米類相關商品
all_records = search_products(df, "米類", topn=60)

# Step 2: 過濾並添加信心度
hierarchy = {
    "L1": "常溫食品",
    "L2": "五穀/豆類/米麵/乾貨",
    "L3": "米類"
}

filtered = _filter_by_hierarchy(all_records, hierarchy)

# 結果例子
# {
#   "商品編號": "4712834520154",
#   "商品名稱": "歐特有機小米/480g",
#   "CateName_L1": "常溫食品",
#   "CateName_L2": "五穀/豆類/米麵/乾貨",
#   "CateName_L3": "米類",
#   "matched_levels": ["L1", "L2", "L3"],
#   "hierarchy_score": 9
# }
```

### 前端如何使用 (JavaScript)

```javascript
// Step 1: 從後端數據提取信心度
const item = response.items[0];
const hierarchyScore = item["hierarchy_score"] || 0;

// Step 2: 轉換為百分比
const scorePercent = Math.round(hierarchyScore * 100);

// Step 3: 決定顏色
const color = scorePercent >= 80 ? '#10b981' 
            : scorePercent >= 60 ? '#f59e0b' 
            : '#ef4444';

// Step 4: 渲染
const html = `
  <div class="confidence-badge" style="color: ${color}">
    ${scorePercent}%
  </div>
`;
```

---

## 相關設置

### 環境變數
- 暫無相關環境變數控制信心度計算

### 配置檔案
- 暫無相關配置檔案

### 代碼位置
| 檔案 | 行數 | 功能 |
|------|------|------|
| `backend/app.py` | 507-538 | `_annotate_hierarchy()` |
| `backend/app.py` | 541-640 | `_filter_by_hierarchy()` |
| `backend/goods_search_service.py` | 713-714 | `format_for_chat()` |
| `frontend/index.html` | 1521-1522 | 資料提取 |
| `frontend/index.html` | 1562-1587 | 信心度顯示 |

---

## 總結

**信心度** 是基於商品分類層級與查詢分類層級的匹配程度：

- **資料來源**：後端在 `_filter_by_hierarchy()` 時計算
- **計算方法**：統計 L1/L2/L3 中匹配的層級數 × 3
- **顯示方式**：百分比 + 進度條 + 顏色編碼
- **未來擴展**：可集成 LLM 信心度評分

**目前只用層級匹配數量計分，建議未來考慮：**
1. 名稱相似度
2. LLM 語義匹配評分
3. 用戶反饋信任度
4. 商品新舊度權重
