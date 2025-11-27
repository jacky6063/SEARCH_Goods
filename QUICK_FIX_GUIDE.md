# 快速修復指南

## 🎯 問題
查詢「女用包包價格在 3000~4000元之間」返回 0 件商品，但 CSV 中有 41 件符合條件

## 🔴 原因
`_apply_structured_filters()` 查詢錯誤的欄位名稱

## ✅ 修復（2 分鐘搞定）

### 步驟 1：打開檔案
```
backend/llm_service.py
第 664-690 行
```

### 步驟 2：找到這段代碼
```python
def _apply_structured_filters(records: List[Dict[str, Any]], filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not records or not filters:
        return records
    category_filter = (filters.get("category_filter") or "").lower()
    must_keywords = [kw.lower() for kw in filters.get("must_have_keywords") or [] if kw]
    excluded_keywords = [kw.lower() for kw in filters.get("excluded_keywords") or [] if kw]
    price_filter = filters.get("price_filter") or {}
    min_price = price_filter.get("min_price")
    max_price = price_filter.get("max_price")
    filtered: List[Dict[str, Any]] = []
    for item in records:
        name = str(item.get("Name") or item.get("商品名稱") or item.get("name") or "").lower()
        category = str(item.get("CateName") or item.get("分類名稱") or item.get("category") or "").lower()
        haystack = " ".join([
            name,
            category,
            str(item.get("DESCRIPTION") or item.get("Description") or item.get("ShortDesc") or ""),
        ]).lower()
```

### 步驟 3：替換這段代碼

**改前**:
```python
        name = str(item.get("Name") or item.get("商品名稱") or item.get("name") or "").lower()
        category = str(item.get("CateName") or item.get("分類名稱") or item.get("category") or "").lower()
        haystack = " ".join([
            name,
            category,
            str(item.get("DESCRIPTION") or item.get("Description") or item.get("ShortDesc") or ""),
        ]).lower()
```

**改後**:
```python
        name = str(item.get("Name") or item.get("商品名稱") or item.get("name") or "").lower()
        category = str(item.get("CateName") or item.get("分類名稱") or item.get("category") or "").lower()
        # 🆕 修復：支援 CSV 的三層分類欄位
        l1_cat = str(item.get("大分類名稱") or "").lower()
        l2_cat = str(item.get("中分類名稱") or "").lower()
        l3_cat = str(item.get("小分類名稱") or "").lower()
        haystack = " ".join([
            name,
            category,
            l1_cat,
            l2_cat,
            l3_cat,
            str(item.get("DESCRIPTION") or item.get("Description") or item.get("ShortDesc") or ""),
        ]).lower()
```

### 步驟 4：驗證並提交
```bash
# 驗證語法
python3 -m py_compile backend/llm_service.py

# 提交
git add backend/llm_service.py
git commit -m "fix: 修復結構化篩選無法識別 CSV 分類欄位"
git push
```

## 🧪 驗證

測試查詢：
```
"我要購買女用包包價格在 3000~4000元之間"
```

預期結果：
```
✅ 應返回 41 件商品
✅ 包括「多夾層經典面料收納休閒包」等
```

## 📊 修復前後

| 項目 | 修復前 | 修復後 |
|------|-------|-------|
| 搜尋結果 | 0 件 ❌ | 41 件 ✅ |
| 類別過濾 | 故障 | 正常 |
| 價格過濾 | 正常 | 正常 |

---

詳細診斷: 見 `CHAT_QUERY_BUG_DIAGNOSIS.md`
