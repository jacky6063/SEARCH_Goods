# SEARCH_Goods AI 程式設計規範

## 🎯 規範目標

本規範基於 SEARCH_Goods 系統的實際開發經驗，建立 AI 友好的程式設計標準，確保系統能夠持續進化並保持高品質。本規範專為 AI 協作開發設計，提供明確的指導原則和可執行的標準。

**核心理念**: **可理解性 → 可維護性 → 可進化性**

---

## 📋 目錄

1. [架構設計原則](#1-架構設計原則)
2. [資料存取標準](#2-資料存取標準) 
3. [檔案命名與組織](#3-檔案命名與組織)
4. [程式碼結構規範](#4-程式碼結構規範)
5. [錯誤處理策略](#5-錯誤處理策略)
6. [API 設計標準](#6-api-設計標準)
7. [測試與驗證](#7-測試與驗證)
8. [文檔與註解](#8-文檔與註解)
9. [版本控制實踐](#9-版本控制實踐)
10. [AI 協作指導](#10-ai-協作指導)

---

## 1. 架構設計原則

### 1.1 單一職責原則 (SRP)

每個模組、類別、函數只負責一項明確的職責。

**✅ 良好範例**:
```python
# ✅ 專門負責欄位存取
class FieldAccessor:
    @staticmethod
    def get_product_id(item):
        # 單一職責：獲取商品ID
        pass

# ✅ 專門負責搜尋邏輯
class ProductSearchEngine:
    def search_products(self, query):
        # 單一職責：商品搜尋
        pass
```

**❌ 不良範例**:
```python
# ❌ 混合多種職責
class ProductManager:
    def get_product_id(self, item):
        pass
    def search_products(self, query):
        pass
    def format_response(self, data):
        pass
    def send_email(self, recipient):  # 職責不相關
        pass
```

### 1.2 依賴注入與解耦

使用依賴注入減少模組間的耦合度，提高測試性和可維護性。

**✅ 良好範例**:
```python
# ✅ 依賴注入
class ChatRouter:
    def __init__(self, search_engine, llm_service=None):
        self.search_engine = search_engine
        self.llm_service = llm_service
        
    def process_chat(self, query):
        results = self.search_engine.search(query)
        if self.llm_service:
            results = self.llm_service.enhance(results)
        return results
```

### 1.3 配置外部化

所有環境相關的設定都應該外部化，避免硬編碼。

**設定檔案結構**:
```
backend/
├── .env                    # 環境變數
├── config/
│   ├── column_definitions.json    # 欄位映射
│   ├── branding_config.json      # 品牌設定
│   └── feature_flags.json        # 功能開關
```

**✅ 良好範例**:
```python
# ✅ 使用環境變數
USE_LLM_EXPAND = os.getenv("USE_LLM_EXPAND", "False").lower() == "true"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
DATA_PATH = os.getenv("DATA_PATH", "data/VIEW_GOODS_enhanced.csv")
```

---

## 2. 資料存取標準

### 2.1 統一欄位存取介面

**強制使用 FieldAccessor 模式**，禁止直接存取資料欄位。

**✅ 標準做法**:
```python
from field_utils import FieldAccessor

# ✅ 使用統一介面
product_id = FieldAccessor.get_product_id(item)
name = FieldAccessor.get_name(item)
price = FieldAccessor.get_price(item)
category = FieldAccessor.get_category(item)
```

**❌ 禁止做法**:
```python
# ❌ 直接存取欄位
product_id = item.get("GoodIden") or item.get("商品編號")
name = item.get("Name") or item.get("商品名稱") 
price = int(item.get("Price", 0))
```

### 2.2 資料驗證與轉換

所有外部資料都必須通過驗證和標準化處理。

**標準化流程**:
```python
def process_raw_data(raw_items):
    """標準化資料處理流程"""
    validated_items = []
    
    for item in raw_items:
        try:
            # 1. 驗證必要欄位
            if not FieldAccessor.get_product_id(item):
                continue
                
            # 2. 標準化資料格式
            standardized = FieldAccessor.standardize_product(item)
            
            # 3. 業務邏輯驗證
            if standardized['price'] <= 0:
                continue
                
            validated_items.append(standardized)
            
        except Exception as e:
            logger.warning(f"資料處理錯誤: {e}")
            continue
            
    return validated_items
```

### 2.3 快取策略

實作多層快取提升效能，確保資料一致性。

**快取層級**:
```python
# 全域資料快取
_df_cache = None

# 會話快取
SESSION_ALIGN_CACHE = {}
SUGGEST_CACHE = {}

# 快取管理
def clear_all_caches():
    """清除所有快取"""
    global _df_cache
    _df_cache = None
    SESSION_ALIGN_CACHE.clear()
    SUGGEST_CACHE.clear()
```

---

## 3. 檔案命名與組織

### 3.1 檔案命名規範

**檔案命名格式**: `{功能}_{類型}_{版本}.py`

| 類型 | 命名範例 | 說明 |
|------|---------|------|
| 主要服務 | `goods_search_service.py` | 核心業務邏輯 |
| API 路由 | `chat_router_goods_action.py` | API 端點定義 |
| 工具類別 | `field_utils.py` | 通用工具函數 |
| 配置管理 | `config_store.py` | 設定管理 |
| 資料處理 | `etl/update_csv.py` | 資料處理邏輯 |
| 後備系統 | `fallback/multi_category_party.py` | 後備邏輯 |

### 3.2 目錄結構標準

```
backend/
├── app.py                          # 主應用程式
├── field_utils.py                  # 🎯 統一欄位工具
├── goods_search_service.py         # 搜尋引擎
├── llm_service.py                  # LLM 整合
├── config_store.py                 # 配置管理
├── config/                         # 配置檔案
│   ├── column_definitions.json
│   ├── branding_config.json
│   └── feature_flags.json
├── routers/                        # API 路由
│   ├── chat_router_goods_action.py
│   └── search_router.py
├── fallback/                       # 後備系統
│   └── multi_category_party.py
├── etl/                           # 資料處理
│   └── update_csv.py
├── tests/                         # 測試檔案
│   ├── test_field_utils.py
│   ├── test_api.py
│   └── test_search.py
└── docs/                          # 文檔
    └── api_specs.md
```

### 3.3 模組引入規範

**引入順序**: 標準庫 → 第三方庫 → 本地模組

```python
# ✅ 標準引入順序
import os
import json
from typing import List, Dict, Optional

from fastapi import FastAPI, HTTPException
import pandas as pd
import openai

from field_utils import FieldAccessor
from config_store import get_config
```

---

## 4. 程式碼結構規範

### 4.1 函數設計原則

**函數長度**: 不超過 50 行  
**參數數量**: 不超過 5 個參數  
**回傳型別**: 明確定義型別註解

**✅ 標準函數結構**:
```python
def search_products_by_category(
    category: str, 
    max_results: int = 10,
    include_special_offers: bool = False
) -> List[Dict[str, Any]]:
    """
    根據分類搜尋商品
    
    Args:
        category: 商品分類名稱
        max_results: 最大回傳數量
        include_special_offers: 是否包含特價商品
        
    Returns:
        標準化的商品資料列表
        
    Raises:
        ValueError: 當分類名稱無效時
    """
    # 1. 參數驗證
    if not category or not isinstance(category, str):
        raise ValueError("分類名稱不能為空")
        
    # 2. 業務邏輯
    results = _perform_search(category)
    
    # 3. 結果處理
    return _format_results(results, max_results)
```

### 4.2 類別設計規範

**類別職責**: 單一明確的職責  
**方法數量**: 公開方法不超過 10 個  
**繼承層級**: 不超過 3 層

**✅ 標準類別結構**:
```python
class ProductSearchEngine:
    """商品搜尋引擎
    
    負責商品搜尋的核心邏輯，包含關鍵字匹配、分類篩選、結果排序等功能。
    """
    
    def __init__(self, data_path: str, config: Dict[str, Any]):
        """初始化搜尋引擎"""
        self.data_path = data_path
        self.config = config
        self._cache = {}
        
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """主要搜尋介面"""
        pass
        
    def _load_data(self) -> pd.DataFrame:
        """私有方法：載入資料"""
        pass
        
    def _calculate_score(self, item: Dict, query: str) -> float:
        """私有方法：計算相關性分數"""
        pass
```

### 4.3 錯誤處理模式

**統一例外處理**: 使用自定義例外類別  
**日誌記錄**: 記錄適當層級的日誌  
**優雅降級**: 提供後備方案

```python
# 自定義例外
class SearchEngineError(Exception):
    """搜尋引擎相關錯誤"""
    pass

class DataValidationError(SearchEngineError):
    """資料驗證錯誤"""
    pass

# 標準錯誤處理
def search_with_fallback(query: str) -> List[Dict[str, Any]]:
    """帶後備方案的搜尋"""
    try:
        # 主要搜尋邏輯
        results = primary_search(query)
        if not results:
            raise SearchEngineError("主搜尋無結果")
        return results
        
    except SearchEngineError as e:
        logger.warning(f"搜尋失敗，使用後備方案: {e}")
        return fallback_search(query)
        
    except Exception as e:
        logger.error(f"未預期錯誤: {e}")
        return []
```

---

## 5. 錯誤處理策略

### 5.1 多層錯誤處理

**第一層**: 輸入驗證  
**第二層**: 業務邏輯錯誤  
**第三層**: 系統級錯誤  
**第四層**: 未預期錯誤

```python
def process_chat_request(request_data: Dict) -> Dict[str, Any]:
    """多層錯誤處理範例"""
    
    try:
        # 第一層：輸入驗證
        if not request_data.get("query"):
            raise ValueError("查詢內容不能為空")
            
        query = request_data["query"].strip()
        if len(query) > 1000:
            raise ValueError("查詢內容過長")
            
        # 第二層：業務邏輯
        try:
            results = search_products(query)
            if not results:
                # 啟動後備機制
                results = fallback_search(query)
                
        except SearchEngineError as e:
            logger.warning(f"搜尋引擎錯誤: {e}")
            results = []
            
        # 第三層：格式化回應
        try:
            formatted_response = format_chat_response(results)
            return formatted_response
            
        except Exception as e:
            logger.error(f"回應格式化錯誤: {e}")
            return create_error_response("處理失敗")
            
    except ValueError as e:
        # 輸入驗證錯誤
        logger.info(f"輸入驗證失敗: {e}")
        return create_error_response(str(e))
        
    except Exception as e:
        # 第四層：未預期錯誤
        logger.critical(f"系統錯誤: {e}", exc_info=True)
        return create_error_response("系統暫時無法處理請求")
```

### 5.2 日誌記錄標準

**日誌層級使用**:
- `DEBUG`: 詳細的除錯資訊
- `INFO`: 一般操作資訊  
- `WARNING`: 警告但可恢復的錯誤
- `ERROR`: 嚴重錯誤但系統可繼續運行
- `CRITICAL`: 系統級嚴重錯誤

```python
import logging

# 標準日誌配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 使用範例
def search_products(query: str):
    logger.info(f"開始搜尋: {query}")
    
    try:
        results = perform_search(query)
        logger.info(f"搜尋完成，找到 {len(results)} 個結果")
        return results
        
    except Exception as e:
        logger.error(f"搜尋失敗: {e}", exc_info=True)
        raise
```

---

## 6. API 設計標準

### 6.1 RESTful API 設計

**URL 命名**: 使用名詞，避免動詞  
**HTTP 方法**: 語義化使用 GET、POST、PUT、DELETE  
**狀態碼**: 標準化 HTTP 狀態碼

```python
# ✅ 良好的 API 設計
@app.post("/api/search")
async def search_products(request: SearchRequest):
    """搜尋商品"""
    pass

@app.post("/api/chat") 
async def process_chat(request: ChatRequest):
    """處理聊天請求"""
    pass

@app.get("/api/products/{product_id}")
async def get_product(product_id: str):
    """取得單一商品"""
    pass
```

### 6.2 請求/回應格式標準

**統一回應格式**:
```python
# 標準回應結構
class APIResponse:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# 成功回應
{
    "success": true,
    "data": {
        "products": [...],
        "total": 156
    },
    "metadata": {
        "query_time": 0.234,
        "cache_hit": false
    }
}

# 錯誤回應
{
    "success": false,
    "error": "查詢參數無效",
    "metadata": {
        "error_code": "INVALID_QUERY",
        "timestamp": "2025-10-25T10:30:00Z"
    }
}
```

### 6.3 API 版本控制

**URL 版本控制**:
```python
# v1 API
@app.post("/api/v1/search")
async def search_v1(request: SearchRequestV1):
    pass

# v2 API (向後相容)
@app.post("/api/v2/search") 
async def search_v2(request: SearchRequestV2):
    # 支援新功能
    if hasattr(request, 'groups'):
        return enhanced_search(request)
    else:
        # 向後相容
        return search_v1(request)
```

---

## 7. 測試與驗證

### 7.1 測試金字塔

**單元測試** (70%): 測試個別函數和方法  
**整合測試** (20%): 測試模組間互動  
**端對端測試** (10%): 測試完整流程

```python
# 單元測試範例
def test_field_accessor_get_product_id():
    """測試 FieldAccessor 的 get_product_id 方法"""
    # Arrange
    test_item = {"GoodIden": "12345"}
    
    # Act  
    result = FieldAccessor.get_product_id(test_item)
    
    # Assert
    assert result == "12345"
    
def test_field_accessor_handles_missing_field():
    """測試缺失欄位的處理"""
    test_item = {}
    result = FieldAccessor.get_product_id(test_item)
    assert result == ""
```

### 7.2 自動化驗證工具

**程式碼品質檢查**:
```python
# validate_code_quality.py
def validate_field_standardization():
    """驗證欄位標準化進度"""
    pass

def check_function_complexity():
    """檢查函數複雜度"""
    pass

def verify_test_coverage():
    """驗證測試覆蓋率"""
    pass
```

### 7.3 性能測試標準

**回應時間要求**:
- API 回應: < 2 秒
- 搜尋查詢: < 1 秒  
- 快取存取: < 100ms

```python
import time
import pytest

@pytest.mark.performance
def test_search_performance():
    """測試搜尋性能"""
    start_time = time.time()
    
    results = search_products("餅乾")
    
    end_time = time.time()
    response_time = end_time - start_time
    
    assert response_time < 1.0, f"搜尋時間過長: {response_time:.2f}s"
    assert len(results) > 0, "搜尋應該有結果"
```

---

## 8. 文檔與註解

### 8.1 程式碼註解標準

**函數註解**: 使用 Google 風格的 docstring

```python
def calculate_product_score(item: Dict[str, Any], query: str, weights: Dict[str, float]) -> float:
    """
    計算商品與查詢的相關性分數
    
    這個函數使用多個因子來計算商品與搜尋查詢的相關性分數，
    包括名稱匹配、描述匹配、分類匹配等。
    
    Args:
        item: 商品資料字典，必須包含基本商品資訊
        query: 使用者的搜尋查詢字串，已經過預處理
        weights: 各個評分因子的權重配置
            - name_weight: 名稱匹配權重 (預設: 2.0)
            - desc_weight: 描述匹配權重 (預設: 1.0) 
            - category_weight: 分類匹配權重 (預設: 1.0)
    
    Returns:
        float: 相關性分數，範圍 0.0-10.0，分數越高表示越相關
    
    Raises:
        ValueError: 當 item 缺少必要欄位時
        TypeError: 當 query 不是字串類型時
        
    Example:
        >>> item = {"name": "巧克力餅乾", "description": "香脆可口"}
        >>> score = calculate_product_score(item, "餅乾", DEFAULT_WEIGHTS)
        >>> print(f"相關性分數: {score:.2f}")
        相關性分數: 6.50
    """
    # 實作細節...
```

### 8.2 配置檔案註解

**JSON 配置檔案應包含註解或說明文件**:

```json
{
  "_comment": "欄位映射配置 - 定義資料欄位的多重別名",
  "_version": "1.2.0",
  "_last_updated": "2025-10-25",
  
  "GoodIden": {
    "aliases": ["商品編號", "id", "goodiden", "barcode", "條碼", "sku"],
    "type": "string", 
    "required": true,
    "description": "商品的唯一識別碼"
  },
  
  "Name": {
    "aliases": ["商品名稱", "name", "title", "商品名"],
    "type": "string",
    "required": true,
    "description": "商品顯示名稱"
  }
}
```

### 8.3 API 文檔標準

**使用 OpenAPI/Swagger 格式**:

```python
from pydantic import BaseModel, Field

class SearchRequest(BaseModel):
    """搜尋請求模型"""
    query: str = Field(..., description="搜尋關鍵字", example="巧克力餅乾")
    category: Optional[str] = Field(None, description="分類篩選", example="餅乾")
    max_results: int = Field(10, description="最大結果數", ge=1, le=100)

class ProductResponse(BaseModel):  
    """商品回應模型"""
    id: str = Field(..., description="商品ID")
    name: str = Field(..., description="商品名稱")
    price: int = Field(..., description="價格（新台幣）")
    category: str = Field(..., description="商品分類")
```

---

## 9. 版本控制實踐

### 9.1 Git 提交規範

**提交訊息格式**: `type(scope): description`

**Type 類型**:
- `feat`: 新功能
- `fix`: 錯誤修正
- `docs`: 文檔更新
- `style`: 程式碼格式調整
- `refactor`: 程式碼重構
- `test`: 測試相關
- `chore`: 建構或輔助工具變動

**範例**:
```bash
feat(search): add product category filtering
fix(api): handle empty query parameter
docs(readme): update installation instructions  
refactor(field): standardize field access across modules
test(search): add performance test cases
```

### 9.2 分支策略

**主要分支**:
- `main`: 穩定發布版本
- `develop`: 開發整合分支
- `feature/*`: 功能開發分支
- `hotfix/*`: 緊急修復分支

**工作流程**:
```bash
# 建立功能分支
git checkout -b feature/add-product-grouping develop

# 開發完成後合併
git checkout develop  
git merge --no-ff feature/add-product-grouping
git branch -d feature/add-product-grouping

# 發布到 main
git checkout main
git merge --no-ff develop
git tag -a v1.2.0 -m "Release version 1.2.0"
```

### 9.3 程式碼審查檢查清單

**功能性檢查**:
- [ ] 功能是否符合需求規格
- [ ] 邊界條件是否正確處理
- [ ] 錯誤處理是否完整

**程式碼品質檢查**:
- [ ] 是否遵循命名規範
- [ ] 是否使用統一的欄位存取介面
- [ ] 函數複雜度是否適中
- [ ] 是否有適當的註解

**安全性檢查**:
- [ ] 是否有 SQL 注入風險
- [ ] 輸入驗證是否充分
- [ ] 敏感資料是否正確處理

---

## 10. AI 協作指導

### 10.1 AI 理解優化

**結構化註解**: 使用標準化的註解格式幫助 AI 理解

```python
"""
AI_CONTEXT: 這是商品搜尋引擎的核心類別
AI_DEPENDENCIES: 依賴 field_utils.FieldAccessor 進行欄位存取  
AI_USAGE: 主要用於處理使用者搜尋請求和商品推薦
AI_MODIFICATION_SAFE: 可以安全修改 search() 方法的參數，但不要改變回傳格式
"""
class ProductSearchEngine:
    pass
```

**模式識別標記**:
```python
# AI_PATTERN: 統一欄位存取模式
# 當需要存取商品欄位時，請使用以下標準方式：
product_id = FieldAccessor.get_product_id(item)
name = FieldAccessor.get_name(item) 
price = FieldAccessor.get_price(item)

# AI_ANTIPATTERN: 避免直接存取欄位
# 請勿使用以下方式：
# product_id = item.get("GoodIden") or item.get("商品編號")
```

### 10.2 迭代開發指南

**階段性開發**:

**第一階段 - 基礎功能**:
```python
# AI_STAGE_1: 實作核心功能
def basic_search(query: str) -> List[Dict]:
    """基礎搜尋功能 - AI 可以安全修改"""
    pass
```

**第二階段 - 功能增強**:  
```python
# AI_STAGE_2: 增強功能，向後相容
def enhanced_search(query: str, filters: Optional[Dict] = None) -> List[Dict]:
    """增強搜尋功能 - 保持向後相容"""
    if filters is None:
        return basic_search(query)
    # 新功能實作
```

**第三階段 - 優化改進**:
```python  
# AI_STAGE_3: 性能優化，保持介面不變
def optimized_search(query: str, filters: Optional[Dict] = None) -> List[Dict]:
    """優化版搜尋 - 介面不變，性能提升"""
    pass
```

### 10.3 AI 協作最佳實踐

**1. 明確的意圖表達**:
```python
"""
AI_INTENT: 這個函數的目的是將多種商品資料格式統一為標準格式
AI_INPUT: 接受任何包含商品資訊的字典
AI_OUTPUT: 回傳標準化的商品字典，包含 id, name, price, category 等欄位
AI_SIDE_EFFECTS: 無副作用，純函數
"""
def standardize_product_data(raw_data: Dict) -> Dict:
    pass
```

**2. 漸進式修改指導**:
```python
# AI_MODIFICATION_GUIDE:
# 1. 先理解現有邏輯
# 2. 識別需要修改的部分  
# 3. 保持現有 API 不變
# 4. 添加新功能時使用可選參數
# 5. 測試向後相容性
```

**3. 錯誤處理指導**:
```python
# AI_ERROR_HANDLING_PATTERN:
# 所有對外的函數都應該：
# 1. 驗證輸入參數
# 2. 處理預期的錯誤  
# 3. 記錄適當的日誌
# 4. 提供有意義的錯誤訊息
# 5. 不讓內部錯誤洩漏到外部
```

---

## 📋 規範檢查清單

### 開發前檢查
- [ ] 是否理解業務需求和技術約束
- [ ] 是否查看了相關的現有程式碼
- [ ] 是否確認了要使用的設計模式
- [ ] 是否規劃了測試策略

### 開發中檢查  
- [ ] 是否使用 FieldAccessor 進行欄位存取
- [ ] 是否遵循命名規範
- [ ] 是否加入適當的錯誤處理
- [ ] 是否寫了必要的註解和文檔

### 開發後檢查
- [ ] 是否通過所有測試
- [ ] 是否更新了相關文檔
- [ ] 是否遵循 Git 提交規範
- [ ] 是否考慮了向後相容性

### AI 協作檢查
- [ ] 是否加入了 AI 理解標記
- [ ] 是否提供了修改指導
- [ ] 是否標明了安全修改範圍
- [ ] 是否記錄了設計決策

---

## 🔄 規範進化

本規範會根據實際開發經驗持續進化，每次重大變更都會：

1. **記錄變更原因**
2. **提供遷移指南**  
3. **更新相關範例**
4. **通知所有協作者**

**規範版本**: v1.0  
**最後更新**: 2025年10月25日  
**下次審查**: 2025年11月25日

---

**📞 聯絡資訊**: 如對本規範有任何疑問或建議，請建立 Issue 或提交 Pull Request。