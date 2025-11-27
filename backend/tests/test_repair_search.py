# -*- coding: utf-8 -*-
"""
================================================================================
SEARCH_Goods 系統 - 維修搜尋服務測試
================================================================================

檔案名稱: test_repair_search.py
建立日期: 2025年11月11日

測試內容:
    - 維修資料載入
    - 維修項目搜尋
    - 評分計算
    - 結果格式化

================================================================================
"""
import pytest
import pandas as pd
from pathlib import Path
import sys

# 加入父目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from repair_search_service import (
    load_repair_data,
    extract_repair_terms,
    score_repair_row,
    search_repairs,
    format_for_chat,
    find_repair_by_name,
    get_repair_categories,
    DEFAULT_REPAIR_CSV_PATH,
)
from repair_constants import REPAIR_CSV_COLUMNS


class TestRepairDataLoading:
    """測試維修資料載入"""
    
    def test_load_repair_data_success(self):
        """測試成功載入維修資料"""
        df = load_repair_data()
        assert not df.empty, "維修資料不應該是空的"
        assert len(df) > 0, "應該至少有一筆維修資料"
    
    def test_load_repair_data_columns(self):
        """測試載入的資料包含必要欄位"""
        df = load_repair_data()
        
        # 檢查必要欄位是否存在
        required_cols = [
            REPAIR_CSV_COLUMNS["responsibility"],
            REPAIR_CSV_COLUMNS["category"],
            REPAIR_CSV_COLUMNS["name"],
        ]
        
        for col in required_cols:
            assert col in df.columns, f"缺少必要欄位: {col}"
    
    def test_load_repair_data_cache(self):
        """測試資料快取功能"""
        # 第一次載入
        df1 = load_repair_data()
        
        # 第二次載入（應使用快取）
        df2 = load_repair_data(refresh=False)
        
        assert len(df1) == len(df2), "快取的資料應該相同"


class TestTermExtraction:
    """測試詞彙提取"""
    
    def test_extract_repair_terms_basic(self):
        """測試基本詞彙提取"""
        query = "水龍頭滴水"
        terms = extract_repair_terms(query)
        
        assert len(terms) > 0, "應該提取到詞彙"
        assert "水龍頭" in terms or "滴水" in terms, "應該包含關鍵詞"
    
    def test_extract_repair_terms_complex(self):
        """測試複雜查詢的詞彙提取"""
        query = "廁所的馬桶一直流水怎麼辦"
        terms = extract_repair_terms(query)
        
        assert len(terms) > 0, "應該提取到詞彙"
        # 應該包含主要關鍵字
        assert any(term in ["馬桶", "流水", "廁所"] for term in terms)
    
    def test_extract_repair_terms_empty(self):
        """測試空查詢"""
        query = ""
        terms = extract_repair_terms(query)
        
        assert isinstance(terms, list), "應該返回列表"


class TestScoring:
    """測試評分計算"""
    
    def test_score_repair_row_name_match(self):
        """測試項目名稱匹配的評分"""
        row = {
            REPAIR_CSV_COLUMNS["name"]: "水龍頭持續滴水",
            REPAIR_CSV_COLUMNS["category"]: "給/排水設備",
            REPAIR_CSV_COLUMNS["symptoms"]: "水龍頭或三角凡爾持續滴水。",
            REPAIR_CSV_COLUMNS["responsibility"]: "住家",
            "__text_cache__": "水龍頭 滴水 給排水",
        }
        
        terms = ["水龍頭", "滴水"]
        score = score_repair_row(row, terms)
        
        assert score > 5.0, "項目名稱匹配應該得高分"
    
    def test_score_repair_row_category_match(self):
        """測試類別匹配的評分"""
        row = {
            REPAIR_CSV_COLUMNS["name"]: "其他問題",
            REPAIR_CSV_COLUMNS["category"]: "給/排水設備",
            REPAIR_CSV_COLUMNS["symptoms"]: "一些症狀",
            REPAIR_CSV_COLUMNS["responsibility"]: "住家",
            "__text_cache__": "給排水 其他問題",
        }
        
        terms = ["給排水", "設備"]
        score = score_repair_row(row, terms)
        
        assert score > 0, "類別匹配應該有分數"
    
    def test_score_repair_row_no_match(self):
        """測試無匹配的評分"""
        row = {
            REPAIR_CSV_COLUMNS["name"]: "冷氣不冷",
            REPAIR_CSV_COLUMNS["category"]: "空調設備",
            REPAIR_CSV_COLUMNS["symptoms"]: "冷氣運轉但不冷",
            REPAIR_CSV_COLUMNS["responsibility"]: "住家",
            "__text_cache__": "冷氣 空調",
        }
        
        terms = ["水龍頭", "漏水"]
        score = score_repair_row(row, terms)
        
        assert score == 0.0, "無匹配應該得 0 分"


class TestSearchRepairs:
    """測試維修項目搜尋"""
    
    def test_search_repairs_basic(self):
        """測試基本搜尋功能"""
        df = load_repair_data()
        query = "水龍頭滴水"
        
        results, terms = search_repairs(df, query, topn=3)
        
        assert isinstance(results, list), "結果應該是列表"
        assert isinstance(terms, list), "詞彙應該是列表"
        assert len(results) <= 3, "結果不應超過 topn"
    
    def test_search_repairs_with_filter(self):
        """測試帶篩選條件的搜尋"""
        df = load_repair_data()
        query = "漏水"
        
        results, terms = search_repairs(
            df,
            query,
            topn=5,
            category_filter="給/排水"
        )
        
        # 檢查結果是否符合篩選條件
        for result in results:
            category = result.get(REPAIR_CSV_COLUMNS["category"], "")
            assert "給" in category or "排水" in category, "結果應符合類別篩選"
    
    def test_search_repairs_empty_query(self):
        """測試空查詢"""
        df = load_repair_data()
        query = ""
        
        results, terms = search_repairs(df, query, topn=3)
        
        # 空查詢應返回前 N 筆
        assert isinstance(results, list), "應返回列表"
    
    def test_search_repairs_no_results(self):
        """測試無結果的查詢"""
        df = load_repair_data()
        query = "根本不存在的維修項目xyz123"
        
        results, terms = search_repairs(df, query, topn=3)
        
        assert isinstance(results, list), "應返回列表"
        # 可能返回空列表或低分結果


class TestFormatting:
    """測試結果格式化"""
    
    def test_format_for_chat_normal(self):
        """測試正常格式化"""
        records = [
            {
                REPAIR_CSV_COLUMNS["name"]: "水龍頭持續滴水",
                REPAIR_CSV_COLUMNS["category"]: "給/排水設備",
                REPAIR_CSV_COLUMNS["symptoms"]: "水龍頭或三角凡爾持續滴水。",
                REPAIR_CSV_COLUMNS["link"]: "https://example.com",
                REPAIR_CSV_COLUMNS["video"]: "https://youtu.be/example",
            }
        ]
        
        formatted = format_for_chat(records, slim_mode=False)
        
        assert len(formatted) == 1, "應該有一筆結果"
        assert "維修項目" in formatted[0], "應該包含維修項目欄位"
        assert "序號" in formatted[0], "應該包含序號欄位"
    
    def test_format_for_chat_slim(self):
        """測試瘦身模式格式化"""
        records = [
            {
                REPAIR_CSV_COLUMNS["name"]: "水龍頭持續滴水",
                REPAIR_CSV_COLUMNS["category"]: "給/排水設備",
                REPAIR_CSV_COLUMNS["symptoms"]: "水龍頭或三角凡爾持續滴水。",
                REPAIR_CSV_COLUMNS["link"]: "https://example.com",
                REPAIR_CSV_COLUMNS["video"]: "https://youtu.be/example",
            }
        ]
        
        formatted = format_for_chat(records, slim_mode=True)
        
        assert len(formatted) == 1, "應該有一筆結果"
        # 瘦身模式不包含所有欄位
        assert "維修項目" in formatted[0], "應該包含核心欄位"
    
    def test_format_for_chat_empty(self):
        """測試空結果格式化"""
        records = []
        formatted = format_for_chat(records)
        
        assert formatted == [], "空結果應返回空列表"


class TestUtilityFunctions:
    """測試工具函數"""
    
    def test_find_repair_by_name_exact(self):
        """測試依名稱精確查找"""
        df = load_repair_data()
        
        # 使用實際存在的維修項目名稱
        if not df.empty:
            first_name = df.iloc[0][REPAIR_CSV_COLUMNS["name"]]
            results = find_repair_by_name(df, first_name, limit=1)
            
            assert len(results) > 0, "應該找到結果"
            assert results[0][REPAIR_CSV_COLUMNS["name"]] == first_name, "應該是精確匹配"
    
    def test_find_repair_by_name_partial(self):
        """測試依名稱部分匹配"""
        df = load_repair_data()
        
        # 使用部分關鍵字
        results = find_repair_by_name(df, "水龍頭", limit=3)
        
        # 應該找到包含「水龍頭」的項目
        if results:
            assert any("水龍頭" in r[REPAIR_CSV_COLUMNS["name"]] for r in results)
    
    def test_get_repair_categories(self):
        """測試取得維修類別"""
        df = load_repair_data()
        categories = get_repair_categories(df)
        
        assert isinstance(categories, list), "應該返回列表"
        assert len(categories) > 0, "應該有至少一個類別"
        
        # 檢查類別是否為字串
        for cat in categories:
            assert isinstance(cat, str), "類別應該是字串"


if __name__ == "__main__":
    # 執行測試
    pytest.main([__file__, "-v", "--tb=short"])
