# SEARCH_Goods 欄位標準化優化報告

## 📋 項目概述

本文件記錄了 SEARCH_Goods 系統的欄位標準化優化過程，目標是建立統一的欄位存取標準，消除程式碼中的欄位不一致問題，提升系統穩定性和可維護性。

**優化時間**: 2025年10月25日  
**Git 提交**: 592a4bc  
**標準化進度**: 83.3%  

## 🎯 優化目標

### 問題背景
- **欄位名稱不統一**: 系統中同時存在中英文欄位名稱
- **容錯處理不一致**: 各檔案使用不同的欄位存取方式
- **維護成本高**: 新增功能時需要記住多種欄位命名方式
- **錯誤風險**: 拼寫錯誤導致的欄位存取失敗

### 解決方案
建立統一的 `FieldAccessor` 工具類，提供標準化的欄位存取 API，支援多重別名映射和自動容錯處理。

## 🛠️ 核心工具開發

### 1. FieldAccessor 統一欄位處理器

**檔案位置**: `backend/field_utils.py`

#### 主要功能
- **統一欄位存取**: 提供標準化的方法名稱
- **多重別名支援**: 每個欄位支援 2-6 個不同名稱
- **自動容錯**: 處理空值、格式錯誤和缺失欄位
- **型別轉換**: 自動處理價格等數值型欄位

#### 核心欄位映射表

| 邏輯欄位 | 標準英文欄位 | 支援別名 | 存取方法 |
|---------|-------------|---------|---------|
| 商品編號 | `GoodIden` | `商品編號`, `id`, `goodiden`, `barcode`, `條碼`, `sku` | `get_product_id()` |
| 商品名稱 | `Name` | `商品名稱`, `name`, `title`, `商品名` | `get_name()` |
| 分類名稱 | `CateName` | `分類名稱`, `category`, `catename` | `get_category()` |
| 品牌 | `BRAND_Name` | `品牌`, `brand`, `Brand` | `get_brand()` |
| 商品描述 | `DESCRIPTION` | `描述`, `description`, `Description`, `desc` | `get_description()` |
| 售價 | `Price` | `售價`, `price`, `價格` | `get_price()` |
| 特價 | `SpecialOffer` | `特價`, `specialoffer`, `special_price` | `get_special_price()` |
| 規格 | `Size` | `規格`, `size`, `specification` | `get_size()` |
| 庫存量 | `stock` | `庫存量`, `inventory` | `get_stock()` |
| 商品圖片 | `Goodspic_Link1` | `商品圖片網址`, `商品圖片網址1`, `image_url`, `pic_url` | `get_image_url()` |
| 購物網址 | `Goods_Link1` | `購物網址`, `shop_url`, `link` | `get_shop_url()` |
| 影片介紹 | `youtube` | `Youtube 影片介紹`, `video_url` | - |
| 備註 | `REMARK` | `備註`, `remark`, `note` | - |

#### 使用範例

**基本欄位存取**:
```python
from field_utils import FieldAccessor

# 安全的欄位存取
product_id = FieldAccessor.get_product_id(item)
name = FieldAccessor.get_name(item)
price = FieldAccessor.get_price(item)  # 自動轉為整數
category = FieldAccessor.get_category(item)
```

**商品資料標準化**:
```python
# 將不同格式的商品資料統一為標準格式
standardized = FieldAccessor.standardize_product(raw_item)
print(standardized)
# Output: {
#   "id": "4718018351743",
#   "name": "烘焙客無糖乳酪餅乾/120g", 
#   "category": "餅乾/脆果",
#   "brand": "餐御宴",
#   "price": 130,
#   ...
# }
```

**商品摘要生成**:
```python
from field_utils import create_product_summary

# 自動生成商品摘要文字
summary = create_product_summary(products, max_items=3)
print(summary)
# Output: "烘焙客無糖乳酪餅乾/120g、海鹽洋芋片-香辣口味/50g、米森有機黑糖老薑茶"
```

### 2. 欄位標準化驗證工具

**檔案位置**: `backend/validate_field_standardization.py`

#### 功能特色
- **自動掃描**: 檢查所有 Python 檔案的欄位使用情況
- **進度追蹤**: 計算標準化完成度百分比
- **遷移建議**: 提供具體的程式碼改進建議
- **持續監控**: 可定期執行確保標準維持

#### 執行結果範例
```bash
$ python3 validate_field_standardization.py

🔍 欄位標準化驗證報告
==================================================

📋 欄位使用情況掃描:
  GoodIden: 18 個檔案
  Name: 17 個檔案
  商品名稱: 10 個檔案
  ...

✅ 使用 FieldAccessor 的檔案:
  ✓ chat_router_goods_action.py
  ✓ search_ext_goods_1024001.py
  ✓ fallback/multi_category_party.py
  ...

📊 標準化進度:
  總共有欄位存取的檔案: 6
  已使用 FieldAccessor: 5  
  標準化進度: 83.3%
  🎉 標準化進度良好!
```

## 📁 檔案優化記錄

### 已標準化的檔案

#### 1. `chat_router_goods_action.py` - 主要聊天處理器
**優化內容**:
```python
# ❌ 優化前
suggestion_ids = [str(x.get("GoodIden") or x.get("id")) for x in items if (x.get("GoodIden") or x.get("id"))]
samples = "、".join((str(items[i].get("Name") or items[i].get("name") or items[i].get("商品名稱")) for i in range(min(3, len(items)))))

# ✅ 優化後  
suggestion_ids = [FieldAccessor.get_product_id(x) for x in items if FieldAccessor.get_product_id(x)]
samples = create_product_summary(items, max_items=3)
```

#### 2. `chat_router_goods_1024001.py` - 備用聊天處理器
**優化內容**:
```python
# ❌ 優化前
suggestion_ids = [str(x.get("GoodIden") or x.get("id")) for x in items if (x.get("GoodIden") or x.get("id"))]
samples = "、".join((str(items[i].get("name") or items[i].get("商品名稱")) for i in range(min(3,len(items)))))

# ✅ 優化後
suggestion_ids = [FieldAccessor.get_product_id(x) for x in items if FieldAccessor.get_product_id(x)]
samples = create_product_summary(items, max_items=3)
```

#### 3. `search_ext_goods_1024001.py` - 搜尋引擎
**優化內容**:
```python
# ❌ 優化前
out = [x for x in out if category_filter in str(x.get("分類名稱",""))]
name_get = lambda x: str(x.get("name") or x.get("商品名稱") or "").lower()

# ✅ 優化後
out = [x for x in out if category_filter in FieldAccessor.get_category(x)]
out = [x for x in out if k in FieldAccessor.get_name(x).lower()]
```

#### 4. `fallback/multi_category_party.py` - 後備系統
**優化內容**:
```python
# ❌ 優化前  
name = str(row.get(name_col, "")).strip()
price = to_price_int(row.get(price_col))
gid = str(row.get(id_col, "")).strip()

# ✅ 優化後
name = FieldAccessor.get_name(row_dict)
price = FieldAccessor.get_price(row_dict) 
product_id = FieldAccessor.get_product_id(row_dict)
```

#### 5. `promo_cache_goods_1024001.py` - 促銷系統
**優化內容**:
```python
# ❌ 優化前
name = item.get("name") or item.get("商品名稱") or ""
desc = item.get("描述") or item.get("description") or ""
brand = item.get("品牌") or item.get("brand") or ""

# ✅ 優化後
name = FieldAccessor.get_name(item)
desc = FieldAccessor.get_description(item)
brand = FieldAccessor.get_brand(item)
```

### 配置檔案更新

#### `column_definitions.json` 增強
```json
{
  "GoodIden": ["商品編號", "id", "goodiden", "barcode", "條碼", "sku"],
  "Name": ["商品名稱", "name", "title", "商品名"],
  "CateName": ["分類名稱", "category", "catename"],
  "Size": ["規格", "size", "specification"],
  "Price": ["售價", "price", "價格"],
  "SpecialOffer": ["特價", "specialoffer", "special_price"],
  "BRAND_Name": ["品牌", "brand", "Brand"],
  "DESCRIPTION": ["描述", "description", "Description", "desc"],
  "Goods_Link1": ["購物網址", "shop_url", "link"],
  "Goodspic_Link1": ["商品圖片網址", "商品圖片網址1", "image_url", "pic_url"],
  "REMARK": ["備註", "remark", "note"],
  "stock": ["庫存量", "inventory"],
  "youtube": ["Youtube 影片介紹", "video_url"]
}
```

## 🧪 測試驗證

### 功能測試結果

#### 1. FieldAccessor 基本功能測試
```bash
🧪 測試統一欄位處理器...
商品1 ID: 4718018351743
商品1 名稱: 烘焙客無糖乳酪餅乾/120g
商品1 價格: 130
商品2 ID: 1234567
商品2 名稱: 測試商品
商品2 價格: 99
標準化商品1: 烘焙客無糖乳酪餅乾/120g - 130元
商品摘要: 烘焙客無糖乳酪餅乾/120g、測試商品
✅ 統一欄位處理器測試完成
```

#### 2. 聊天系統整合測試
```bash
🧪 測試優化後的聊天系統...
1. "我要辦一場生日聚會請幫忙準備餅乾類以及飲..." → 16 建議 (OK: True)
2. "餅乾類商品..." → 10 建議 (OK: True)  
3. "洋芋片..." → 5 建議 (OK: True)
✅ 優化後的聊天系統測試完成
```

#### 3. 標準化進度驗證
- **總共檔案數**: 6 個主要檔案
- **已標準化**: 5 個檔案  
- **標準化進度**: 83.3%
- **測試結果**: ✅ 所有核心功能正常運作

## 📈 優化效益

### 1. 程式碼品質提升
- **🔸 消除硬編碼**: 統一欄位存取 API 取代分散的硬編碼
- **🔸 提高可讀性**: 方法名稱更直觀 (`get_name()` vs `item.get("Name")`)
- **🔸 減少重複代碼**: 統一的容錯邏輯避免重複實作

### 2. 錯誤防護機制
- **🔸 拼寫錯誤防護**: IDE 自動完成減少欄位名稱錯誤
- **🔸 空值處理**: 自動提供合理的預設值
- **🔸 型別安全**: 價格等數值型欄位自動轉換

### 3. 維護效率改善
- **🔸 集中管理**: 欄位邏輯集中在 `field_utils.py` 
- **🔸 擴展性**: 新增欄位類型只需修改一處
- **🔸 向後相容**: 支援舊有欄位名稱確保平滑遷移

### 4. 開發體驗優化  
- **🔸 統一 API**: 開發人員只需學習一套方法
- **🔸 自動驗證**: 驗證工具提供持續品質監控
- **🔸 清晰文檔**: 完整的使用範例和對照表

## 🔮 未來建議

### 短期改進 (1-2週)
1. **完成剩餘檔案標準化**: 將標準化進度從 83.3% 提升至 100%
2. **增加單元測試**: 為 `FieldAccessor` 建立完整的測試覆蓋
3. **IDE 支援**: 建立 VS Code 程式碼片段提高開發效率

### 中期優化 (1個月)
1. **擴展驗證工具**: 增加更多自動檢查規則
2. **效能優化**: 為頻繁存取的欄位增加快取機制
3. **文檔完善**: 建立開發者指南和最佳實踐

### 長期規劃 (3個月)
1. **資料庫層整合**: 考慮在 ORM 層面實作欄位映射
2. **前端標準化**: 將相同概念擴展到前端 JavaScript 程式碼
3. **微服務支援**: 為未來的微服務架構做準備

## 📚 相關資源

### 文檔連結
- [欄位對照表參考](./field_mapping_reference.md)
- [系統架構概述](../README.md)
- [API 文檔](../backend/README.md)

### 程式碼範例
- [FieldAccessor 完整實作](../backend/field_utils.py)
- [驗證工具使用方式](../backend/validate_field_standardization.py)
- [配置檔案範例](../backend/column_definitions.json)

### Git 提交記錄
- **主要提交**: [592a4bc - optimize: standardize field access across all backend modules](https://github.com/jacky6063/SEARCH_Goods/commit/592a4bc)
- **文檔提交**: [403ae0d - docs: add comprehensive field mapping reference](https://github.com/jacky6063/SEARCH_Goods/commit/403ae0d)

---

**文件版本**: v1.0  
**最後更新**: 2025年10月25日  
**維護人員**: SEARCH_Goods 開發團隊