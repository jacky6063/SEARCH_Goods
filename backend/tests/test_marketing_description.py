"""
測試商品描述生成功能
"""
import sys
import os
# 添加父目錄到路徑以便匯入模組
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch, MagicMock
from llm_service import (
    detect_product_category,
    llm_generate_marketing_description,
    generate_smart_template_description,
    generate_enhanced_marketing_description
)
from chat_router_goods_action import _build_marketing_description


class TestProductCategoryDetection:
    """測試商品類別檢測功能"""
    
    def test_food_category_detection(self):
        """測試食品類商品檢測"""
        assert detect_product_category("有機燕麥片", "營養豐富的早餐選擇") == "food"
        assert detect_product_category("冷壓純鮮椰子油", "椰子油含有豐富中鏈脂肪") == "food"
        assert detect_product_category("蜂蜜檸檬茶", "天然蜂蜜調味") == "food"
    
    def test_bag_category_detection(self):
        """測試包包類商品檢測"""
        assert detect_product_category("前皮釦式多夾層實用斜背包", "多夾層設計收納便利") == "bag"
        assert detect_product_category("真皮手提包", "義大利進口牛皮") == "bag"
        assert detect_product_category("防水後背包", "戶外運動專用") == "bag"
    
    def test_clothing_category_detection(self):
        """測試服飾類商品檢測"""
        assert detect_product_category("純棉透氣T恤", "100%純棉材質") == "clothing"
        assert detect_product_category("保暖外套", "防風保暖設計") == "clothing"
    
    def test_electronics_category_detection(self):
        """測試3C類商品檢測"""
        assert detect_product_category("藍牙無線耳機", "高品質音響效果") == "electronics"
        assert detect_product_category("智能手機充電器", "快速充電技術") == "electronics"
    
    def test_general_category_fallback(self):
        """測試一般類商品（無法明確分類）"""
        assert detect_product_category("", "") == "general"
        assert detect_product_category("神秘商品", "特殊用途") == "general"


class TestSmartTemplateGeneration:
    """測試智能模板生成功能"""
    
    def test_food_template_generation(self):
        """測試食品類模板生成"""
        item = {
            "Name": "有機燕麥片/500g",
            "DESCRIPTION": "高纖維營養豐富的健康選擇"
        }
        result = generate_smart_template_description(item)
        assert "有機燕麥片" in result
        assert "營養" in result or "健康" in result
        assert len(result) <= 25
    
    def test_bag_template_generation(self):
        """測試包包類模板生成"""
        item = {
            "Name": "前皮釦式多夾層實用斜背包-黑色",
            "DESCRIPTION": "真皮材質，多夾層設計，實用便利"
        }
        result = generate_smart_template_description(item)
        assert "前皮釦式" in result
        assert "實用" in result or "便利" in result
        assert "好搭配" in result or "好夥伴" in result
        assert len(result) <= 25


class TestLLMMarketingDescription:
    """測試 LLM 商品描述生成功能"""
    
    @pytest.mark.llm
    @patch('llm_service._get_client')
    @patch('llm_service.USE_LLM_MARKETING', True)
    def test_llm_generation_success(self, mock_get_client):
        """測試 LLM 成功生成描述"""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "真皮多夾層設計便利，時尚實用好搭配"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        result = llm_generate_marketing_description(
            "前皮釦式多夾層實用斜背包",
            "真皮材質，多夾層設計",
            "bag"
        )
        
        assert result == "真皮多夾層設計便利，時尚實用好搭配"
        assert mock_client.chat.completions.create.called
    
    @pytest.mark.llm
    @patch('llm_service._get_client')
    @patch('llm_service.USE_LLM_MARKETING', False)
    def test_llm_generation_disabled(self, mock_get_client):
        """測試 LLM 功能被停用"""
        result = llm_generate_marketing_description(
            "測試商品",
            "測試描述",
            "general"
        )
        
        assert result == ""
        assert not mock_get_client.called
    
    @pytest.mark.llm
    @patch('llm_service._get_client')
    @patch('llm_service.USE_LLM_MARKETING', True)
    def test_llm_generation_failure_fallback(self, mock_get_client):
        """測試 LLM 失敗時的處理"""
        mock_get_client.return_value = None  # No client available
        
        result = llm_generate_marketing_description(
            "測試商品",
            "測試描述",
            "general"
        )
        
        assert result == ""


class TestEnhancedMarketingDescription:
    """測試增強版商品描述生成功能"""
    
    @pytest.mark.llm
    @patch('llm_service.llm_generate_marketing_description')
    @patch('llm_service.USE_LLM_MARKETING', True)
    @patch('llm_service._get_client')
    def test_llm_priority_success(self, mock_get_client, mock_llm_generate):
        """測試 LLM 優先級成功"""
        mock_get_client.return_value = MagicMock()
        mock_llm_generate.return_value = "LLM生成的優質描述"
        
        item = {
            "Name": "測試商品",
            "DESCRIPTION": "測試描述"
        }
        
        result = generate_enhanced_marketing_description(item)
        assert result == "LLM生成的優質描述"
    
    @pytest.mark.llm
    @patch('llm_service.llm_generate_marketing_description')
    @patch('llm_service.USE_LLM_MARKETING', True)
    @patch('llm_service._get_client')
    def test_smart_template_fallback(self, mock_get_client, mock_llm_generate):
        """測試智能模板降級"""
        mock_get_client.return_value = MagicMock()
        mock_llm_generate.return_value = ""  # LLM 失敗
        
        item = {
            "Name": "有機燕麥片",
            "DESCRIPTION": "營養豐富的健康選擇"
        }
        
        result = generate_enhanced_marketing_description(item)
        assert "有機燕麥片" in result
        assert len(result) > 0


class TestIntegrationWithChatRouter:
    """測試與 chat_router_goods_action.py 的整合"""
    
    @patch('llm_service.generate_enhanced_marketing_description')
    def test_build_marketing_description_integration(self, mock_enhanced):
        """測試 _build_marketing_description 整合"""
        mock_enhanced.return_value = "整合測試成功描述"
        
        from chat_router_goods_action import _build_marketing_description
        
        item = {
            "Name": "測試商品",
            "DESCRIPTION": "測試描述"
        }
        
        result = _build_marketing_description(item)
        assert result == "整合測試成功描述"
    
    def test_fallback_to_basic_description(self):
        """測試降級到基礎描述生成"""
        from chat_router_goods_action import _build_basic_marketing_description_fallback
        
        # 測試包包商品
        bag_item = {
            "Name": "前皮釦式多夾層實用斜背包-黑色",
            "DESCRIPTION": "真皮材質，多夾層設計"
        }
        
        result = _build_basic_marketing_description_fallback(bag_item)
        assert "前皮釦式" in result
        assert "好搭配" in result  # 包包專用結尾
        assert "香濃好滋味" not in result  # 不應該有食品描述
        
        # 測試食品商品
        food_item = {
            "Name": "有機燕麥片/500g",
            "DESCRIPTION": "高纖維營養豐富"
        }
        
        result = _build_basic_marketing_description_fallback(food_item)
        assert "有機燕麥片" in result
        assert ("好選擇" in result or "好滋味" in result)  # 食品專用結尾


if __name__ == "__main__":
    # 執行測試
    print("=== 執行商品類別檢測測試 ===")
    
    # 測試基本功能
    print("1. 測試商品類別檢測:")
    print(f"椰子油: {detect_product_category('冷壓純鮮椰子油', '椰子油含有豐富中鏈脂肪')}")
    print(f"斜背包: {detect_product_category('前皮釦式多夾層實用斜背包', '多夾層設計')}")
    print(f"T恤: {detect_product_category('純棉T恤', '100%純棉材質')}")
    
    print("\n2. 測試智能模板生成:")
    test_items = [
        {
            "Name": "前皮釦式多夾層實用斜背包-黑色",
            "DESCRIPTION": "真皮材質，多夾層設計，實用便利"
        },
        {
            "Name": "有機燕麥片/500g", 
            "DESCRIPTION": "高纖維營養豐富的健康選擇"
        }
    ]
    
    for item in test_items:
        result = generate_smart_template_description(item)
        print(f"{item['Name'][:20]}... → {result}")
    
    print("\n3. 測試基礎描述改善:")
    from chat_router_goods_action import _build_basic_marketing_description_fallback
    
    for item in test_items:
        result = _build_basic_marketing_description_fallback(item)
        print(f"{item['Name'][:20]}... → {result}")
    
    print("\n✅ 基礎功能測試完成！")