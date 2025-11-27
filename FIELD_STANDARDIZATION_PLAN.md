# 欄位標準化重構計畫 (方案 C: FieldAccessor)

## 📋 概述

統一使用 `FieldAccessor` 類進行所有欄位存取，隱藏欄位名稱細節，提升代碼可維護性。

**時間估計**: 2-3 小時  
**影響範圍**: 7 個文件，~800 行代碼  
**風險等級**: 低 (所有改動都是純粹的重構)

---

## 🎯 目標

- ✅ 消除所有 `item.get("Name") or item.get("商品名稱")` 的冗餘代碼
- ✅ 統一通過 `FieldAccessor` 存取欄位
- ✅ 保留所有業務邏輯完全不變
- ✅ 確保所有 95 個測試通過
- ✅ 為未來欄位變更提供單一變更點

---

## 📝 改造檔案清單

### 優先級 1: 核心業務邏輯 (必改)

| 檔案 | 函數/位置 | 影響行數 | 優先級 |
|------|---------|--------|------|
| `backend/llm_service.py` | `_apply_structured_filters()` 等 20+ 處 | ~150 | 🔴 |
| `backend/goods_search_service.py` | 搜尋邏輯 15+ 處 | ~120 | 🔴 |
| `backend/app.py` | API 回應格式化 20+ 處 | ~200 | 🔴 |

### 優先級 2: 聊天系統 (應改)

| 檔案 | 函數/位置 | 影響行數 | 優先級 |
|------|---------|--------|------|
| `backend/chat_router_goods_action.py` | 格式化函數 10+ 處 | ~80 | 🟡 |
| `backend/field_utils.py` | 已完成 ✅ | - | ✅ |

### 優先級 3: 測試 (可改)

| 檔案 | 影響 | 優先級 |
|------|-----|------|
| `backend/tests/test_*.py` | 更新 mock 資料 | 🟢 |

---

## 🔄 改造步驟

### 階段 1: llm_service.py 中的 _apply_structured_filters()

**當前代碼**:
```python
name = str(item.get("Name") or item.get("商品名稱") or item.get("name") or "").lower()
category = str(item.get("CateName") or item.get("分類名稱") or item.get("category") or "").lower()
l1_cat = str(item.get("大分類名稱") or "").lower()
l2_cat = str(item.get("中分類名稱") or "").lower()
l3_cat = str(item.get("小分類名稱") or "").lower()
haystack = " ".join([name, category, l1_cat, l2_cat, l3_cat, ...]).lower()
```

**改造後**:
```python
name = FieldAccessor.get_name(item).lower()
l1_cat = FieldAccessor.get_category_l1(item).lower()  # 需新增此方法
l2_cat = FieldAccessor.get_category_l2(item).lower()  # 需新增此方法
l3_cat = FieldAccessor.get_category_l3(item).lower()  # 需新增此方法
description = FieldAccessor.get_description(item).lower()
haystack = " ".join([name, l1_cat, l2_cat, l3_cat, description]).lower()
```

**收益**: 
- 減少 4 行混亂的 `or` 鏈
- 邏輯清晰
- 易於測試

---

### 階段 2: 擴展 FieldAccessor

**需要新增的方法**:
```python
@classmethod
def get_category_l1(cls, item: Dict[str, Any]) -> str:
    """取得大分類名稱"""
    
@classmethod
def get_category_l2(cls, item: Dict[str, Any]) -> str:
    """取得中分類名稱"""
    
@classmethod
def get_category_l3(cls, item: Dict[str, Any]) -> str:
    """取得小分類名稱"""
```

---

### 階段 3: goods_search_service.py

替換所有:
```python
# 舊
row.get("Name", "") or row.get("商品名稱", "")
row.get("Price") or row.get("價格")

# 新
FieldAccessor.get_name(row)
FieldAccessor.get_price(row)
```

---

### 階段 4: app.py

替換所有回應格式化代碼:
```python
# 舊
"商品編號": row.get("GoodIden", ""),
"商品名稱": row.get("Name", ""),
"商品價格": row.get("Price_fmt") or row.get("Price", ""),

# 新
"商品編號": FieldAccessor.get_product_id(row),
"商品名稱": FieldAccessor.get_name(row),
"商品價格": FieldAccessor.get_price(row),
```

---

### 階段 5: chat_router_goods_action.py

替換格式化函數中的所有欄位存取。

---

## ✅ 驗證檢查清單

- [ ] 所有 95 個單元測試通過
- [ ] 女用包包查詢返回 41 個商品
- [ ] 防蚊、防蟑 L3 查詢無錯誤
- [ ] 代碼通過 pylint 檢查
- [ ] 沒有新的 deprecation 警告

---

## 🔗 相關檔案

- `backend/field_utils.py` - FieldAccessor 類定義
- `backend/llm_service.py` - 主要改造目標
- `column_definitions.json` - 欄位映射 (參考)

---

## 📊 預期效果

### 改造前後對比

| 指標 | 改造前 | 改造後 | 改進 |
|------|------|------|------|
| 冗餘 `.get()` 鏈 | ~200+ 處 | 0 | 100% 消除 |
| 欄位變更影響行數 | ~800 | ~50 (只需改 FieldAccessor) | 94% 減少 |
| 代碼可讀性 | ⭐⭐ | ⭐⭐⭐⭐⭐ | 大幅提升 |
| 後期維護成本 | 🔴 高 | 🟢 低 | 顯著降低 |

---

## 💡 實施建議

1. **備份現狀**: 確保 git commit 是乾淨的
2. **分檔重構**: 一次改一個檔案，測試後再改下一個
3. **保留彈性**: 保留 FieldAccessor 中的多別名支援
4. **逐步推進**: 先改 Priority 1，再改 Priority 2

