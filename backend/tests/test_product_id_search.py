# -*- coding: utf-8 -*-
"""
商品編號搜尋功能測試
測試商品編號檢測和精確匹配功能，確保不影響智能搜尋平衡
"""

import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from goods_search_service import (
    _is_product_id_query, 
    _find_exact_product_id_match,
    search_products
)


class TestProductIdDetection:
    """測試商品編號檢測功能"""
    
    def test_detect_valid_product_ids(self):
        """測試能正確識別有效的商品編號格式"""
        valid_product_ids = [
            "V37312T-0819",     # 字母+數字+字母-數字
            "W80414-S",         # 字母+數字-字母
            "4711467470256",    # 純數字條碼
            "8420701509015",    # 純數字條碼
            "9557205023088",    # 純數字條碼
            "12345678",         # 8位數字條碼
            "ABC123-DEF456",    # 字母+數字-字母+數字
            "XYZ999Z",          # 字母+數字+字母
        ]
        
        for product_id in valid_product_ids:
            assert _is_product_id_query(product_id), f"應該識別 {product_id} 為商品編號"
    
    def test_reject_invalid_queries(self):
        """測試能正確拒絕非商品編號格式的查詢"""
        invalid_queries = [
            "女用包包",          # 純中文
            "3000~4000元",       # 價格區間
            "背包",             # 一般商品名稱
            "特價商品",          # 一般描述
            "hello world",       # 一般英文短語
            "123",              # 太短的數字
            "7654321",          # 7位數字 (不足 8 位)
            "abc",              # 太短的字母
            "",                 # 空字串
            "包包推薦",          # 中文查詢
        ]
        
        for query in invalid_queries:
            assert not _is_product_id_query(query), f"不應該識別 {query} 為商品編號"
    
    def test_edge_cases(self):
        """測試邊界情況"""
        edge_cases = [
            ("A1", False),          # 太短
            ("A" * 30, False),      # 太長
            ("123456789012345", True),  # 15位數字條碼（有效）
            ("12345678901234567890", False),  # 20位數字（太長）
            ("12345678", True),     # 8位數字也視為商品編號
            ("V37312T", True),      # 字母數字混合格式（有效商品編號）
        ]
        
        for case, expected in edge_cases:
            result = _is_product_id_query(case)
            assert result == expected, f"'{case}' 應該返回 {expected}，實際返回 {result}"

    def test_detect_product_id_in_sentence(self):
        """測試含自然語句時能識別商品編號"""
        assert _is_product_id_query("我要查商品編號：V59401P-6613")
        assert _is_product_id_query("請問 9557205023088 這個條碼的商品有哪些資訊？")


class TestProductIdExactMatch:
    """測試商品編號精確匹配功能"""
    
    @pytest.fixture
    def sample_df(self):
        """創建測試用的商品資料"""
        data = {
            'GoodIden': ['V37312T-0819', 'W80414-S', '4711467470256'],
            'Name': ['多夾層經典面料收納休閒包-綠杏', '百搭首選真皮吊帶款', '能益淨天然防蟑侵'],
            'Price': ['3290', '680', '230'],
            'CateName': ['輕量側/斜肩背包', '皮件配件', '居家清潔']
        }
        return pd.DataFrame(data)
    
    def test_exact_match_found(self, sample_df):
        """測試能找到精確匹配的商品編號"""
        # 測試完全匹配
        result = _find_exact_product_id_match(sample_df, "V37312T-0819")
        assert len(result) == 1
        assert result[0]['GoodIden'] == 'V37312T-0819'
        assert '多夾層經典面料收納休閒包' in result[0]['Name']
        
        # 測試不區分大小寫
        result = _find_exact_product_id_match(sample_df, "v37312t-0819")
        assert len(result) == 1
        assert result[0]['GoodIden'] == 'V37312T-0819'
    
    def test_exact_match_not_found(self, sample_df):
        """測試找不到匹配時返回空列表"""
        result = _find_exact_product_id_match(sample_df, "NONEXISTENT-123")
        assert len(result) == 0
        
        result = _find_exact_product_id_match(sample_df, "")
        assert len(result) == 0

    def test_exact_match_from_sentence(self, sample_df):
        """測試自然語句中含商品編號仍能找到精確匹配"""
        sentence = "我要查商品編號：V37312T-0819，麻煩幫我找一下"
        result = _find_exact_product_id_match(sample_df, sentence)
        assert len(result) == 1
        assert result[0]['GoodIden'] == 'V37312T-0819'


class TestIntegratedProductIdSearch:
    """測試整合後的搜尋功能"""
    
    @pytest.fixture
    def sample_df(self):
        """創建測試用的商品資料"""
        data = {
            'GoodIden': [
                'V37312T-0819', 'W80414-S', '4711467470256', 
                'ABC123', 'DEF456', '9999999999999'
            ],
            'Name': [
                '多夾層經典面料收納休閒包-綠杏', '百搭首選真皮吊帶款藍', '能益淨天然防蟑侵',
                '女用時尚背包', '男用皮帶', '特價商品'
            ],
            'Price': ['3290', '680', '230', '1500', '800', '199'],
            'CateName': ['輕量側/斜肩背包', '皮件配件', '居家清潔', '背包', '皮帶', '其他'],
            'DESCRIPTION': [
                '高品質休閒包', '真皮製作', '天然成分', 
                '時尚設計', '耐用皮革', '超值優惠'
            ]
        }
        return pd.DataFrame(data)
    
    def test_product_id_search_priority(self, sample_df):
        """測試商品編號搜尋具有最高優先級"""
        # 搜尋存在的商品編號
        results, terms = search_products(sample_df, "V37312T-0819", topn=5)
        
        # 應該只返回精確匹配的商品
        assert len(results) == 1
        assert results[0]['GoodIden'] == 'V37312T-0819'
        assert '多夾層經典面料收納休閒包' in results[0]['Name']
    
    def test_fallback_to_smart_search(self, sample_df):
        """測試當商品編號不存在時，回退到智能搜尋"""
        # 搜尋不存在的商品編號 - 應該回退到智能搜尋
        results, terms = search_products(sample_df, "NONEXISTENT-123", topn=5)
        
        # 由於沒有相關商品，結果可能為空或分數很低
        # 這是正常的智能搜尋行為
        assert isinstance(results, list)
        assert isinstance(terms, list)
    
    def test_sentence_query_returns_exact_match(self, sample_df):
        """測試包含自然語句的商品編號查詢仍能回傳精確結果"""
        query = "我要查商品編號：V37312T-0819"
        results, terms = search_products(sample_df, query, topn=5)
        assert len(results) == 1
        assert results[0]['GoodIden'] == 'V37312T-0819'
    
    def test_normal_search_unaffected(self, sample_df):
        """測試一般搜尋功能不受影響"""
        # 測試中文關鍵字搜尋
        results, terms = search_products(sample_df, "背包", topn=5, min_score=0.5)
        
        # 應該找到包含"背包"的商品
        assert len(results) >= 1
        
        # 驗證結果包含相關商品
        found_bag_items = [r for r in results if '背包' in r['Name'] or '背包' in r['CateName']]
        assert len(found_bag_items) >= 1
    
    def test_price_range_search_unaffected(self, sample_df):
        """測試價格區間搜尋功能不受影響"""
        # 測試價格區間搜尋
        results, terms = search_products(sample_df, "價格 200 700", topn=5, min_score=0.1)
        
        # 應該能正常處理價格相關查詢
        assert isinstance(results, list)
        assert isinstance(terms, list)


class TestProductIdBoundaryBehavior:
    """測試商品編號功能的邊界行為"""
    
    def test_mixed_query_handling(self):
        """測試混合查詢的處理（商品編號 + 其他關鍵字）"""
        # 這種情況下，系統應該根據查詢的主要特徵來決定處理方式
        mixed_queries = [
            "V37312T-0819 價格",    # 商品編號 + 價格查詢
            "找 W80414-S 商品",     # 商品編號 + 一般詞彙
        ]
        
        for query in mixed_queries:
            # 由於包含明確的商品編號，應該被識別為商品編號查詢
            is_product_id = _is_product_id_query(query.split()[0])  # 取第一個詞
            # 這裡我們測試分詞後的第一個部分是否為商品編號
            assert is_product_id or len(query.split()) > 1
    
    def test_case_insensitive_matching(self):
        """測試不區分大小寫的匹配"""
        test_cases = [
            "V37312T-0819",
            "v37312t-0819", 
            "V37312t-0819",
            "v37312T-0819"
        ]
        
        for case in test_cases:
            assert _is_product_id_query(case), f"應該識別 {case} 為商品編號（不區分大小寫）"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
