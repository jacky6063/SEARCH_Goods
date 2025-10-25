# SEARCH_Goods 欄位對照表

## 中文欄位對應英文欄位名稱

本文件整理了 SEARCH_Goods 系統中所有中文欄位與英文欄位的對應關係。

### 核心商品欄位對照

| 中文欄位名稱 | 英文欄位名稱 | 資料類型 | 說明 |
|-------------|-------------|----------|------|
| 商品編號 | `GoodIden` | String | 商品唯一識別碼，例如：4718018351743 |
| 商品名稱 | `Name` | String | 商品完整名稱，例如：烘焙客無糖乳酪餅乾/120g |
| 分類名稱 | `CateName` | String | 商品分類，例如：餅乾/脆果 |
| 品牌 | `BRAND_Name` | String | 商品品牌，例如：餐御宴 |
| 商品描述 | `DESCRIPTION` | String | 詳細的商品說明，包含成分、營養資訊等 |

### 價格與規格欄位

| 中文欄位名稱 | 英文欄位名稱 | 資料類型 | 說明 |
|-------------|-------------|----------|------|
| 售價 | `Price` | String/Number | 商品原價 |
| 特價 | `SpecialOffer` | String/Number | 商品特價 |
| 規格 | `Size` | String | 商品規格描述 |
| 庫存量 | `庫存量` | String/Number | 目前庫存數量 |

### 媒體與連結欄位

| 中文欄位名稱 | 英文欄位名稱 | 資料類型 | 說明 |
|-------------|-------------|----------|------|
| 購物網址 | `Goods_Link1` | String | 商品購買連結 |
| 商品圖片網址1 | `Goodspic_Link1` | String | 商品圖片 URL |
| Youtube 影片介紹 | `Youtube 影片介紹` | String | 影片介紹連結 |
| 備註 | `REMARK` | String | 額外備註資訊 |

## 系統內部對照表

### column_definitions.json 定義
```json
{
  "GoodIden": ["商品編號"],
  "Name": ["商品名稱"], 
  "CateName": ["分類名稱"],
  "Size": ["規格"],
  "Price": ["售價"],
  "SpecialOffer": ["特價"],
  "BRAND_Name": ["品牌"],
  "DESCRIPTION": ["描述"],
  "Goods_Link1": ["購物網址"],
  "Goodspic_Link1": ["商品圖片網址", "商品圖片網址1"],
  "REMARK": ["備註"]
}
```

### CSV 資料庫欄位順序
```
1. 商品編號
2. 商品名稱  
3. 分類名稱
4. 規格
5. 售價
6. 特價
7. 庫存量
8. 品牌
9. 描述
10. Youtube 影片介紹
11. 購物網址
12. 備註
13. 商品圖片網址1
```

## 程式碼中的使用方式

### 搜尋引擎回傳格式 (search_ext_goods_1024001.py)
商品搜尋後回傳的物件包含以下英文欄位：
- `GoodIden` - 商品編號
- `Name` - 商品名稱
- `CateName` - 分類名稱  
- `BRAND_Name` - 品牌
- `DESCRIPTION` - 商品描述
- `Price` - 售價
- `SpecialOffer` - 特價
- `Size` - 規格
- `Goods_Link1` - 購物網址
- `Goodspic_Link1` - 商品圖片
- `__score__` - 搜尋評分 (系統內部使用)

### Fallback 系統對照 (fallback/multi_category_party.py)
在 fallback 系統中，支援以下欄位別名查找：
```python
name_col = _col(df, "商品名稱", "商品名", "name", "title")
price_col = _col(df, "售價", "價格", "price", "特價")  
id_col = _col(df, "商品編號", "GoodIden", "goodiden", "id", "barcode", "條碼", "sku")
```

### 聊天處理器欄位優先級 (chat_router_goods_action.py)
商品名稱顯示的優先順序：
```python
item.get("Name") or item.get("name") or item.get("商品名稱")
```

## 程式檔案中的欄位使用狀況

### 主要檔案的欄位引用

#### backend/fallback/multi_category_party.py
```python
name_col = _col(df, "商品名稱", "商品名", "name", "title")
id_col = _col(df, "商品編號", "GoodIden", "goodiden", "id", "barcode", "條碼", "sku")
price_col = _col(df, "售價", "價格", "price", "特價")
```

#### backend/chat_router_goods_action.py 
```python
# 商品名稱顯示優先級
item.get("Name") or item.get("name") or item.get("商品名稱")
```

#### backend/promo_cache_goods_1024001.py
```python
name = item.get("name") or item.get("商品名稱") or ""
desc = item.get("描述") or item.get("description") or ""
brand = item.get("品牌") or item.get("brand") or ""
```

#### backend/search_ext_goods_1024001.py
```python
# 分類過濾
x.get("分類名稱","")
# 商品名稱取得
x.get("name") or x.get("商品名稱") or ""
```

#### backend/goods_search_service.py
```python
# 欄位重命名對照
COLUMN_NAME_MAP: Dict[str, str] = _load_column_mapping()
# 搜尋時的欄位引用
row.get("Name", "")
row.get("DESCRIPTION") or row.get("Description") or ""
row.get("CateName") or row.get("分類名稱") or ""
```

## 標準化建議

### 建議統一使用的欄位名稱

為了提高程式碼的一致性，建議統一使用以下英文欄位名稱：

| 功能 | 標準英文欄位 | 備用中文欄位 | 程式碼範例 |
|------|-------------|-------------|------------|
| 商品編號 | `GoodIden` | `商品編號` | `item.get("GoodIden")` |
| 商品名稱 | `Name` | `商品名稱` | `item.get("Name")` |
| 分類名稱 | `CateName` | `分類名稱` | `item.get("CateName")` |
| 品牌 | `BRAND_Name` | `品牌` | `item.get("BRAND_Name")` |
| 商品描述 | `DESCRIPTION` | `描述` | `item.get("DESCRIPTION")` |
| 售價 | `Price` | `售價` | `item.get("Price")` |
| 特價 | `SpecialOffer` | `特價` | `item.get("SpecialOffer")` |

### 容錯取值範例

推薦在程式中使用容錯的欄位取值方式：

```python
# 商品名稱 (支援多種欄位名稱)
name = item.get("Name") or item.get("name") or item.get("商品名稱") or "未知商品"

# 商品描述 (支援大小寫變化)
desc = item.get("DESCRIPTION") or item.get("Description") or item.get("描述") or ""

# 商品編號 (支援多種 ID 格式)
product_id = item.get("GoodIden") or item.get("id") or item.get("商品編號") or ""

# 分類名稱
category = item.get("CateName") or item.get("分類名稱") or "未分類"

# 品牌資訊
brand = item.get("BRAND_Name") or item.get("品牌") or ""
```

## 注意事項

1. **欄位名稱一致性**: 系統支援中英文欄位名稱混用，但建議統一使用英文欄位名稱以確保相容性。

2. **資料類型**: 所有欄位在 CSV 中都以字串形式儲存，數值型欄位需要在程式中轉換。

3. **空值處理**: 部分商品的某些欄位可能為空，程式需要適當處理空值情況。

4. **特殊欄位**: `__score__` 是搜尋引擎新增的內部評分欄位，不存在於原始資料中。

5. **大小寫敏感**: 部分程式檔案對欄位名稱的大小寫敏感，建議保持一致。

---
*更新時間: 2025年10月25日*
*系統版本: v1.0*