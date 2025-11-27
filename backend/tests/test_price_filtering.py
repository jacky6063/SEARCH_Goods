"""
測試價格過濾功能
"""
import sys
import os
import types
import importlib
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from utils.simple_extract import extract_budget_and_cats
from search_ext_goods_1024001 import filter_items
import search_ext_goods_1024001 as strict_search
from field_utils import FieldAccessor


class TestBudgetExtraction:
    """測試預算提取功能"""
    
    def test_simple_budget_extraction(self):
        """測試基本預算提取"""
        result = extract_budget_and_cats("我想找2500元以下的包包")
        assert result["budget"] == 2500
        assert result["budget_info"]["max_price"] == 2500
        assert result["budget_info"]["min_price"] is None
    
    def test_budget_within_extraction(self):
        """測試'以內'表達方式"""
        result = extract_budget_and_cats("預算3000元內的女包")
        assert result["budget"] == 3000
        assert result["budget_info"]["max_price"] == 3000
    
    def test_budget_range_extraction(self):
        """測試價格範圍"""
        result = extract_budget_and_cats("1000-2500元的背包")
        assert result["budget"] == 2500  # 向後相容取最大值
        assert result["budget_info"]["min_price"] == 1000
        assert result["budget_info"]["max_price"] == 2500
    
    def test_budget_prefix_extraction(self):
        """測試'預算'前綴"""
        result = extract_budget_and_cats("預算是2000元的商品")
        assert result["budget"] == 2000
        assert result["budget_info"]["max_price"] == 2000
    
    def test_no_budget_extraction(self):
        """測試沒有預算的情況"""
        result = extract_budget_and_cats("我想找女用包包")
        assert result["budget"] is None
        assert result["budget_info"]["max_price"] is None
    
    def test_tilde_range_extraction(self):
        """測試波浪號價格範圍"""
        result = extract_budget_and_cats("3000~4000元的包包")
        assert result["budget"] == 4000  # 向後相容取最大值
        assert result["budget_info"]["min_price"] == 3000
        assert result["budget_info"]["max_price"] == 4000
    
    def test_tilde_with_yuan_extraction(self):
        """測試帶'元'的波浪號價格範圍"""
        result = extract_budget_and_cats("我想要找3000元~4000元的女用包包")
        assert result["budget"] == 4000
        assert result["budget_info"]["min_price"] == 3000
        assert result["budget_info"]["max_price"] == 4000


class TestPriceFiltering:
    """測試價格過濾功能"""
    
    def setup_method(self):
        """設置測試數據"""
        self.test_items = [
            {
                "Name": "便宜包包",
                "Price": "1500",
                "SpecialOffer": "",
                "CateName": "包包"
            },
            {
                "Name": "中等包包",
                "Price": "2800", 
                "SpecialOffer": "2533",  # 有特價
                "CateName": "包包"
            },
            {
                "Name": "昂貴包包",
                "Price": "3980",
                "SpecialOffer": "",
                "CateName": "包包"
            },
            {
                "Name": "無價格包包",
                "Price": "",
                "SpecialOffer": "",
                "CateName": "包包"
            }
        ]
    
    def test_max_price_filter(self):
        """測試最高價格過濾"""
        price_filter = {"max_price": 2500}
        filtered = filter_items(self.test_items, price_filter=price_filter)
        
        # 應該包含：便宜包包(1500), 中等包包(特價2533，但超過2500會被排除)
        names = [item["Name"] for item in filtered]
        assert "便宜包包" in names
        # 注意：中等包包的特價是2533，超過2500，應該被排除
        assert "中等包包" not in names  
        assert "昂貴包包" not in names
        assert "無價格包包" not in names
    
    def test_min_price_filter(self):
        """測試最低價格過濾"""
        price_filter = {"min_price": 2000}
        filtered = filter_items(self.test_items, price_filter=price_filter)
        
        names = [item["Name"] for item in filtered]
        assert "便宜包包" not in names  # 1500 < 2000
        assert "中等包包" in names     # 特價2533 >= 2000
        assert "昂貴包包" in names     # 3980 >= 2000
        assert "無價格包包" not in names
    
    def test_price_range_filter(self):
        """測試價格範圍過濾"""
        price_filter = {"min_price": 2000, "max_price": 3000}
        filtered = filter_items(self.test_items, price_filter=price_filter)
        
        names = [item["Name"] for item in filtered]
        assert "便宜包包" not in names  # 1500 < 2000
        assert "中等包包" in names     # 2533 在範圍內
        assert "昂貴包包" not in names  # 3980 > 3000
    
    def test_special_price_priority(self):
        """測試特價優先邏輯"""
        # 修改測試商品，讓特價低於原價
        modified_item = {
            "Name": "特價包包",
            "Price": "3000",      # 原價3000
            "SpecialOffer": "2000",  # 特價2000
            "CateName": "包包"
        }
        
        price_filter = {"max_price": 2500}
        filtered = filter_items([modified_item], price_filter=price_filter)
        
        # 應該使用特價2000進行判斷，符合 <= 2500 的條件
        assert len(filtered) == 1
        assert filtered[0]["Name"] == "特價包包"


class TestIntegratedBudgetSearch:
    """整合測試：預算提取 + 搜尋過濾"""
    
    def test_budget_search_integration(self):
        """測試完整的預算搜尋流程"""
        # 1. 提取預算
        query = "我想要找2500元以下的女用包包"
        budget_result = extract_budget_and_cats(query)
        
        # 2. 構建過濾條件
        price_filter = {}
        if budget_result["budget_info"]["max_price"]:
            price_filter["max_price"] = budget_result["budget_info"]["max_price"]
        
        # 3. 模擬商品數據
        mock_products = [
            {"Name": "平價斜背包", "Price": "2200", "SpecialOffer": "", "CateName": "包包"},
            {"Name": "高檔手提包", "Price": "3500", "SpecialOffer": "", "CateName": "包包"},
            {"Name": "特價背包", "Price": "2800", "SpecialOffer": "2300", "CateName": "包包"},
        ]
        
        # 4. 應用過濾
        filtered = filter_items(
            mock_products, 
            category_filter="包",
            price_filter=price_filter
        )
        
        # 5. 驗證結果
        names = [item["Name"] for item in filtered]
        assert "平價斜背包" in names      # 2200 <= 2500 ✓
        assert "高檔手提包" not in names  # 3500 > 2500 ✗
        assert "特價背包" in names        # 特價2300 <= 2500 ✓
        
        print(f"查詢: {query}")
        print(f"預算上限: {price_filter['max_price']}")
        print(f"符合條件的商品: {names}")


class TestSearchProductsStrict:
    """確保 search_products_strict 正確保留價格過濾條件"""
    
    def test_preserves_external_price_filter(self, monkeypatch):
        """原始 filters 中的 price_filter 不應被覆蓋"""
        # 建立 stub app 模組避免載入 FastAPI 等依賴
        stub_app = types.SimpleNamespace(get_df=lambda: object())
        monkeypatch.setitem(sys.modules, "app", stub_app)
        
        test_items = [
            {"Name": "平價包包", "CateName": "包包", "Price": "1500"},
            {"Name": "昂貴包包", "CateName": "包包", "Price": "3200"},
        ]
        
        def fake_base_search(df, query, topn):
            return test_items, None
        
        def fake_infer(query, extra_filters):
            # 確認原始 price_filter 有傳入
            assert extra_filters == {"price_filter": {"max_price": 2000}}
            return {
                "category_filter": "包",
                "must_have_keywords": ["包"],
            }
        
        monkeypatch.setattr(strict_search, "base_search", fake_base_search)
        monkeypatch.setattr(strict_search, "infer_filters_from_query", fake_infer)
        
        results = strict_search.search_products_strict(
            query="推薦女用包包",
            limit=10,
            filters={"price_filter": {"max_price": 2000}}
        )
        
        names = [item["Name"] for item in results]
        assert "平價包包" in names
        assert "昂貴包包" not in names


class TestApplyStructuredFilters:
    """確保聊天路徑也會套用價格過濾"""
    
    def test_price_filter_enforced(self, monkeypatch):
        """_apply_structured_filters 應根據價格限制篩選"""
        # 建立 openai stub，避免匯入 llm_service 時缺少依賴
        openai_stub = types.ModuleType("openai")
        openai_stub.OpenAI = type("OpenAI", (), {})
        monkeypatch.setitem(sys.modules, "openai", openai_stub)
        monkeypatch.delitem(sys.modules, "llm_service", raising=False)
        
        llm_service = importlib.import_module("llm_service")
        
        records = [
            {"Name": "平價背包", "CateName": "包包", "Price": "1800", "SpecialOffer": ""},
            {"Name": "特價背包", "CateName": "包包", "Price": "2800", "SpecialOffer": "1900"},
            {"Name": "昂貴背包", "CateName": "包包", "Price": "4200", "SpecialOffer": ""},
            {"Name": "無價背包", "CateName": "包包", "Price": "", "SpecialOffer": ""},
        ]
        filters = {
            "must_have_keywords": ["包"],
            "price_filter": {"min_price": 1500, "max_price": 2000},
        }
        
        filtered = llm_service._apply_structured_filters(records, filters)
        names = [item["Name"] for item in filtered]
        
        assert "平價背包" in names          # 1800 在範圍內
        assert "特價背包" in names          # 特價 1900 在範圍內
        assert "昂貴背包" not in names      # 4200 超過範圍
        assert "無價背包" not in names      # 沒有有效價格被排除


if __name__ == "__main__":
    # 執行基本測試
    print("=== 價格過濾功能測試 ===")
    
    # 測試預算提取
    test_queries = [
        "我想要找2500元以下的女用包包",
        "預算3000元的商品",
        "1000-2500元的背包",
        "不超過2000元的包包"
    ]
    
    print("1. 預算提取測試:")
    for query in test_queries:
        result = extract_budget_and_cats(query)
        print(f"  '{query}' → 預算: {result['budget']}, 範圍: {result['budget_info']}")
    
    # 測試價格過濾
    print("\n2. 價格過濾測試:")
    test_items = [
        {"Name": "包包A", "Price": "1500", "SpecialOffer": "", "CateName": "包包"},
        {"Name": "包包B", "Price": "2800", "SpecialOffer": "2200", "CateName": "包包"},
        {"Name": "包包C", "Price": "3500", "SpecialOffer": "", "CateName": "包包"},
    ]
    
    price_filter = {"max_price": 2500}
    filtered = filter_items(test_items, price_filter=price_filter)
    
    print(f"  原始商品: {len(test_items)} 個")
    print(f"  預算限制: <= {price_filter['max_price']} 元")
    print(f"  符合條件: {len(filtered)} 個")
    for item in filtered:
        regular_price = FieldAccessor.get_price(item)
        special_price = FieldAccessor.get_special_price(item)
        effective_price = special_price if special_price else regular_price
        print(f"    - {item['Name']}: 有效價格 {effective_price} 元")
    
    print("\n✅ 價格過濾功能測試完成！")
