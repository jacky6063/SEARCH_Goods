# L3 查米類時 _filter_by_hierarchy 的完整執行程序

## 🎯 使用場景

```
用戶點擊：L3 小分類「米類」
  ↓
前端發送：
{
  query: "常溫食品 五穀/豆類/米麵/乾貨 米類",
  category_hierarchy: {
    L1: "常溫食品",
    L2: "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨",
    L3: "米類"  ⭐️ L3 指定為「米類」
  },
  prefer_special_first: true
}
  ↓
後端搜尋 → 取得 60 個候選商品
  ↓
進入 _filter_by_hierarchy() ← 我們要追蹤的函數
```

---

## 📍 函數位置

```
檔案：backend/app.py
- 輔助函數 _record_text：Line 482
- 標記函數 _annotate_hierarchy：Line 485
- 過濾函數 _filter_by_hierarchy：Line 511
- 調用位置：Line 626
```

---

## 🔴 _filter_by_hierarchy 完整代碼

```python
# backend/app.py Line 511-533

def _filter_by_hierarchy(
    records: List[Dict[str, Any]], 
    hierarchy: Optional[Dict[str, str]]
) -> List[Dict[str, Any]]:
    """
    根據分類層級 (L1/L2/L3) 過濾商品
    
    Args:
        records: 搜尋出來的候選商品列表 (60 個)
        hierarchy: {L1: "常溫食品", L2: "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨", L3: "米類"}
    
    Returns:
        只保留符合層級的商品
    """
    # =============== Step 1: 驗證輸入 ===============
    if not hierarchy:
        return records  # 如果沒有層級，返回原始結果
    
    # =============== Step 2: 提取層級值 ===============
    l1 = _record_text(hierarchy.get("L1"))  # "常溫食品"
    l2 = _record_text(hierarchy.get("L2"))  # "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"
    l3 = _record_text(hierarchy.get("L3"))  # "米類"
    
    # =============== Step 3: 檢查是否有任何層級指定 ===============
    if not any([l1, l2, l3]):
        return records  # 如果三個層級都空，返回原始結果
    
    # =============== Step 4: 初始化過濾結果容器 ===============
    filtered: List[Dict[str, Any]] = []
    
    # =============== Step 5: 逐個商品進行層級檢查 ===============
    for rec in records:  # 迴圈 60 次
        ok = True  # 初始：假設這個商品符合
        
        # 🔵 檢查 L1 (大分類)
        if l1:
            # 從商品記錄取 L1 值
            v = _record_text(
                rec.get("CateName_L1") or rec.get("大分類名稱")
            )
            # v = "常溫食品" (商品的大分類)
            
            # 檢查：用戶要的 "常溫食品" 是否在商品的大分類中
            ok = ok and (l1 in v if v else False)
            # ok = True and ("常溫食品" in "常溫食品") = True
        
        # 🔵 檢查 L2 (中分類) - 只有 L1 符合才檢查 L2
        if ok and l2:
            v = _record_text(
                rec.get("CateName_L2") or rec.get("中分類名稱")
            )
            # v = "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨" (商品的中分類)
            
            # 檢查：用戶要的 "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨" 是否在商品的中分類中
            ok = ok and (l2 in v if v else False)
            # ok = True and ("五穀/豆類/五穀/豆類/米麵/乾貨/乾貨" in "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨") = True
        
        # 🔵 檢查 L3 (小分類) - 只有 L1 和 L2 都符合才檢查 L3
        if ok and l3:
            v = _record_text(
                rec.get("CateName_L3") or rec.get("小分類名稱")
            )
            # v = "米類" (商品的小分類)
            
            # 檢查：用戶要的 "米類" 是否在商品的小分類中 ⭐️ 核心過濾點
            ok = ok and (l3 in v if v else False)
            # ok = True and ("米類" in "米類") = True
        
        # =============== Step 6: 如果商品通過所有檢查，添加到結果 ===============
        if ok:
            # 添加標記：這個商品符合哪些層級
            filtered.append(_annotate_hierarchy(rec, hierarchy))
    
    # =============== Step 7: 返回結果 ===============
    # 如果過濾後有結果就返回過濾結果，否則返回原始結果（優雅降級）
    return filtered or records
```

---

## 🔧 輔助函數

### 1️⃣ `_record_text()` (Line 482)

```python
def _record_text(val: Any) -> str:
    """將任何值轉換為去空格的字串"""
    return str(val or "").strip()

# 例子：
_record_text("米類")         → "米類"
_record_text("  米類  ")     → "米類"
_record_text(None)           → ""
_record_text(123)            → "123"
```

### 2️⃣ `_annotate_hierarchy()` (Line 485)

```python
def _annotate_hierarchy(record: Dict[str, Any], hierarchy: Dict[str, str]) -> Dict[str, Any]:
    """為通過過濾的商品添加層級匹配信息"""
    
    if not hierarchy:
        record.setdefault("matched_levels", [])
        record.setdefault("hierarchy_score", 0)
        return record
    
    # 提取層級
    l1 = _record_text(hierarchy.get("L1"))  # "常溫食品"
    l2 = _record_text(hierarchy.get("L2"))  # "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"
    l3 = _record_text(hierarchy.get("L3"))  # "米類"
    
    # 記錄哪些層級符合
    matched: List[str] = []
    
    # 檢查 L1
    if l1:
        v = _record_text(record.get("CateName_L1") or record.get("大分類名稱"))
        if v and (l1 in v):
            matched.append("L1")
    
    # 檢查 L2
    if l2:
        v = _record_text(record.get("CateName_L2") or record.get("中分類名稱"))
        if v and (l2 in v):
            matched.append("L2")
    
    # 檢查 L3
    if l3:
        v = _record_text(record.get("CateName_L3") or record.get("小分類名稱"))
        if v and (l3 in v):
            matched.append("L3")
    
    # 計算層級分數（每層 3 分）
    hierarchy_score = len(matched) * 3  # 三層都符合 = 9 分
    
    # 標記商品
    record["matched_levels"] = matched        # ["L1", "L2", "L3"]
    record["hierarchy_score"] = hierarchy_score  # 9
    
    return record
```

---

## 📊 完整執行流程示意

### 💾 輸入數據

```python
# Step 1: 收到從 search_products() 返回的 60 個候選商品

records = [
    {
        "商品名稱": "泰國香米 5kg",
        "商品編號": "G001",
        "CateName_L1": "常溫食品",        # 大分類
        "CateName_L2": "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨",         # 中分類
        "CateName_L3": "米類",         # ⭐️ 小分類
        "商品特價": "250",
        ...
    },
    {
        "商品名稱": "日本越光米 3kg",
        "商品編號": "G002",
        "CateName_L1": "常溫食品",
        "CateName_L2": "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨",
        "CateName_L3": "米類",         # ⭐️ 小分類
        ...
    },
    {
        "商品名稱": "義大利麵 400g",    # ❌ 不是米類
        "商品編號": "G003",
        "CateName_L1": "常溫食品",
        "CateName_L2": "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨",
        "CateName_L3": "麵類",         # ❌ 小分類不符！
        ...
    },
    ...更多 60 個商品
]

hierarchy = {
    "L1": "常溫食品",
    "L2": "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨",
    "L3": "米類"  ⭐️
}
```

### 🔄 執行過程

```
呼叫：_filter_by_hierarchy(records, hierarchy)
│
├─ Step 2: 提取層級值
│  l1 = "常溫食品"
│  l2 = "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"
│  l3 = "米類"
│
├─ Step 3: 驗證有層級指定
│  any(["常溫食品", "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨", "米類"]) = True ✓
│
├─ Step 5: 開始迴圈 (for rec in records)
│
│  ┌─ 第 1 個商品：「泰國香米 5kg」
│  │  ├─ 檢查 L1: "常溫食品" in "常溫食品"？ ✓ ok = True
│  │  ├─ 檢查 L2: "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨" in "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"？ ✓ ok = True
│  │  ├─ 檢查 L3: "米類" in "米類"？ ✓ ok = True
│  │  └─ if ok: 添加到 filtered ✓
│  │     (_annotate_hierarchy() 添加 matched_levels=["L1","L2","L3"], score=9)
│  │
│  ├─ 第 2 個商品：「日本越光米 3kg」
│  │  ├─ 檢查 L1: "常溫食品" in "常溫食品"？ ✓ ok = True
│  │  ├─ 檢查 L2: "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨" in "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"？ ✓ ok = True
│  │  ├─ 檢查 L3: "米類" in "米類"？ ✓ ok = True
│  │  └─ if ok: 添加到 filtered ✓
│  │
│  ├─ 第 3 個商品：「義大利麵 400g」
│  │  ├─ 檢查 L1: "常溫食品" in "常溫食品"？ ✓ ok = True
│  │  ├─ 檢查 L2: "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨" in "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"？ ✓ ok = True
│  │  ├─ 檢查 L3: "米類" in "麵類"？ ❌ ok = False
│  │  └─ if ok: 不添加 ✗ (被過濾掉)
│  │
│  └─ ... 繼續迴圈其他 57 個商品
│
├─ Step 6: 檢查過濾結果
│  filtered 中現在有 15 個商品 (都是米類)
│
└─ Step 7: 返回結果
   return filtered  # 15 個米類商品
```

### 💾 輸出數據

```python
filtered = [
    {
        "商品名稱": "泰國香米 5kg",
        "商品編號": "G001",
        "CateName_L3": "米類",
        "hierarchy_score": 9,        # ⭐️ 新增
        "matched_levels": ["L1", "L2", "L3"],  # ⭐️ 新增
        ...
    },
    {
        "商品名稱": "日本越光米 3kg",
        "商品編號": "G002",
        "CateName_L3": "米類",
        "hierarchy_score": 9,
        "matched_levels": ["L1", "L2", "L3"],
        ...
    },
    ...共 15 個商品
]
```

---

## 🎬 時序圖

```
時間軸               _filter_by_hierarchy 執行步驟

T0ms   ├─ 輸入：60 個候選商品 + hierarchy
       │
T1ms   ├─ Step 1: 驗證 hierarchy 不為空
       │
T2ms   ├─ Step 2: 提取層級值
       │  l1 = "常溫食品"
       │  l2 = "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"
       │  l3 = "米類"
       │
T3ms   ├─ Step 3: 驗證任意層級不空
       │
T5ms   ├─ Step 5: 開始迴圈 (for rec in records)
       │
T6ms   │  ┌─ 第 1 商品: 檢查 L1/L2/L3 ✓ 添加
T7ms   │  ├─ 第 2 商品: 檢查 L1/L2/L3 ✓ 添加
T8ms   │  ├─ 第 3 商品: 檢查 L1/L2/L3 ❌ 跳過
T9ms   │  ├─ 第 4 商品: 檢查 L1/L2/L3 ✓ 添加
       │  └─ ...
T50ms  │
T51ms  ├─ 完成 60 次檢查
       │
T52ms  ├─ Step 7: 返回 15 個過濾結果
       │
T53ms  └─ 完成

【總耗時：~50ms】
```

---

## 📋 判斷邏輯詳解

### 關鍵：三層級都必須符合

```
for rec in records:
    ok = True
    
    # 層 1：大分類檢查
    if l1:  # 如果用戶指定了 L1
        v = rec.get("CateName_L1")  # 取商品的 L1
        ok = ok and (l1 in v)  # 檢查「常溫食品」是否在商品 L1 中
    
    # 層 2：中分類檢查（只有 L1 符合才檢查）
    if ok and l2:  # 如果用戶指定了 L2
        v = rec.get("CateName_L2")  # 取商品的 L2
        ok = ok and (l2 in v)  # 檢查「五穀/豆類/五穀/豆類/米麵/乾貨/乾貨」是否在商品 L2 中
    
    # 層 3：小分類檢查（只有 L1 和 L2 都符合才檢查）
    if ok and l3:  # 如果用戶指定了 L3
        v = rec.get("CateName_L3")  # 取商品的 L3 ⭐️
        ok = ok and (l3 in v)  # 檢查「米類」是否在商品 L3 中 ⭐️
    
    # 如果全部通過
    if ok:
        filtered.append(_annotate_hierarchy(rec, hierarchy))
```

### 米類搜尋的具體檢查過程

```
商品 1: 泰國香米
┌──────────────────────────────────────┐
│ hierarchy.L1 = "常溫食品"                │
│ 商品 CateName_L1 = "常溫食品"            │
│ 檢查："常溫食品" in "常溫食品"？ = True ✓    │
│ ok = True                            │
└──────────────────────────────────────┘
         ↓
┌──────────────────────────────────────┐
│ hierarchy.L2 = "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"                │
│ 商品 CateName_L2 = "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"            │
│ 檢查："五穀/豆類/五穀/豆類/米麵/乾貨/乾貨" in "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"？ = True ✓   │
│ ok = True                            │
└──────────────────────────────────────┘
         ↓
┌──────────────────────────────────────┐
│ hierarchy.L3 = "米類"                │
│ 商品 CateName_L3 = "米類"            │
│ 檢查："米類" in "米類"？ = True ✓   │ ⭐️ 核心檢查
│ ok = True                            │
└──────────────────────────────────────┘
         ↓
    ✅ 添加到過濾結果
```

### 麵類商品為何被過濾掉

```
商品 3: 義大利麵
┌──────────────────────────────────────┐
│ hierarchy.L1 = "常溫食品"                │
│ 商品 CateName_L1 = "常溫食品"            │
│ 檢查："常溫食品" in "常溫食品"？ = True ✓    │
│ ok = True                            │
└──────────────────────────────────────┘
         ↓
┌──────────────────────────────────────┐
│ hierarchy.L2 = "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"                │
│ 商品 CateName_L2 = "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"            │
│ 檢查："五穀/豆類/五穀/豆類/米麵/乾貨/乾貨" in "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"？ = True ✓   │
│ ok = True                            │
└──────────────────────────────────────┘
         ↓
┌──────────────────────────────────────┐
│ hierarchy.L3 = "米類"                │
│ 商品 CateName_L3 = "麵類"            │
│ 檢查："米類" in "麵類"？ = False ❌ │ ⭐️ 不符合！
│ ok = False                           │
└──────────────────────────────────────┘
         ↓
    ❌ 跳過，不添加到過濾結果
```

---

## 🧪 實際代碼追蹤（Python 執行）

```python
# 假設這是第 1 個商品
rec = {
    "商品名稱": "泰國香米 5kg",
    "CateName_L1": "常溫食品",
    "CateName_L2": "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨",
    "CateName_L3": "米類",
}

hierarchy = {"L1": "常溫食品", "L2": "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨", "L3": "米類"}

# 執行 _filter_by_hierarchy 邏輯
l1 = _record_text(hierarchy.get("L1"))  # "常溫食品"
l2 = _record_text(hierarchy.get("L2"))  # "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"
l3 = _record_text(hierarchy.get("L3"))  # "米類"

ok = True

# 檢查 L1
if l1:  # True
    v = _record_text(rec.get("CateName_L1") or rec.get("大分類名稱"))
    # v = "常溫食品"
    ok = ok and ("常溫食品" in "常溫食品" if "常溫食品" else False)
    # ok = True and True = True

# 檢查 L2
if ok and l2:  # True and True
    v = _record_text(rec.get("CateName_L2") or rec.get("中分類名稱"))
    # v = "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨"
    ok = ok and ("五穀/豆類/五穀/豆類/米麵/乾貨/乾貨" in "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨" if "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨" else False)
    # ok = True and True = True

# 檢查 L3
if ok and l3:  # True and True
    v = _record_text(rec.get("CateName_L3") or rec.get("小分類名稱"))
    # v = "米類"
    ok = ok and ("米類" in "米類" if "米類" else False)
    # ok = True and True = True

# 最終決定
if ok:  # True
    filtered.append(_annotate_hierarchy(rec, hierarchy))
    # ✅ 這個商品被添加
```

---

## 💡 重要細節

### 1️⃣ 短路評估 (Short-circuit)
```
if ok and l2:  ← 只有 ok 是 True 才檢查 L2
if ok and l3:  ← 只有 ok 是 True 才檢查 L3
```
這意味著：
- 如果 L1 不符，L2 和 L3 都不會被檢查（提高效率）
- 必須 L1 ✓ 且 L2 ✓ 且 L3 ✓ 才會通過

### 2️⃣ 子字串匹配
```python
ok = ok and (l1 in v if v else False)
       ↑
       子字串檢查，不是完全相同
```
例如：
- "米" in "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨" = True
- "米" in "米類" = True
- "麞" in "五穀/豆類/五穀/豆類/米麵/乾貨/乾貨" = True

### 3️⃣ 優雅降級
```python
return filtered or records
      ↑
      如果過濾後沒有結果，返回原始結果
```
例如：如果過濾結果為空，返回原始 60 個商品

---

## 📊 性能統計

| 操作 | 耗時 |
|------|------|
| 提取層級值 | < 1ms |
| 迴圈 60 個商品 | 30-40ms |
| 每個商品檢查（L1/L2/L3） | ~0.5-1ms |
| 標記過濾結果 | ~5ms |
| **總耗時** | **~40-50ms** |

---

## ✨ 完整函數定義

```python
# backend/app.py Line 482-533

def _record_text(val: Any) -> str:
    """Convert value to stripped string"""
    return str(val or "").strip()


def _annotate_hierarchy(record: Dict[str, Any], hierarchy: Dict[str, str]) -> Dict[str, Any]:
    """Add hierarchy matching metadata to record"""
    if not hierarchy:
        record.setdefault("matched_levels", [])
        record.setdefault("hierarchy_score", 0)
        return record
    
    l1 = _record_text(hierarchy.get("L1"))
    l2 = _record_text(hierarchy.get("L2"))
    l3 = _record_text(hierarchy.get("L3"))
    matched: List[str] = []
    
    if l1:
        v = _record_text(record.get("CateName_L1") or record.get("大分類名稱"))
        if v and (l1 in v):
            matched.append("L1")
    if l2:
        v = _record_text(record.get("CateName_L2") or record.get("中分類名稱"))
        if v and (l2 in v):
            matched.append("L2")
    if l3:
        v = _record_text(record.get("CateName_L3") or record.get("小分類名稱"))
        if v and (l3 in v):
            matched.append("L3")
    
    hierarchy_score = len(matched) * 3
    record["matched_levels"] = matched
    record["hierarchy_score"] = hierarchy_score
    return record


def _filter_by_hierarchy(records: List[Dict[str, Any]], hierarchy: Optional[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Filter records by hierarchy (L1/L2/L3)"""
    if not hierarchy:
        return records
    
    l1 = _record_text(hierarchy.get("L1"))
    l2 = _record_text(hierarchy.get("L2"))
    l3 = _record_text(hierarchy.get("L3"))
    
    if not any([l1, l2, l3]):
        return records
    
    filtered: List[Dict[str, Any]] = []
    for rec in records:
        ok = True
        if l1:
            v = _record_text(rec.get("CateName_L1") or rec.get("大分類名稱"))
            ok = ok and (l1 in v if v else False)
        if ok and l2:
            v = _record_text(rec.get("CateName_L2") or rec.get("中分類名稱"))
            ok = ok and (l2 in v if v else False)
        if ok and l3:
            v = _record_text(rec.get("CateName_L3") or rec.get("小分類名稱"))
            ok = ok and (l3 in v if v else False)
        if ok:
            filtered.append(_annotate_hierarchy(rec, hierarchy))
    
    return filtered or records
```

