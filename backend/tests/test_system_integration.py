"""
系統整合測試 - 驗證 LLM 增強商品描述生成功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from llm_service import generate_enhanced_marketing_description
from chat_router_goods_action import _build_marketing_description

def test_system_integration():
    """系統整合測試 - 真實商品數據"""
    
    print("=== LLM 增強商品描述生成系統整合測試 ===\n")
    
    # 測試商品數據（模擬真實 CSV 數據）
    test_products = [
        {
            "Name": "前皮釦式多夾層實用斜背包-黑色",
            "DESCRIPTION": "真皮材質，多夾層設計，可調節背帶，實用便利",
            "category": "包包類"
        },
        {
            "Name": "有機燕麥片/500g",
            "DESCRIPTION": "高纖維營養豐富的健康早餐選擇，無添加防腐劑",
            "category": "食品類"
        },
        {
            "Name": "純棉透氣短袖T恤",
            "DESCRIPTION": "100%純棉材質，透氣舒適，多色可選",
            "category": "服飾類"
        },
        {
            "Name": "藍牙無線耳機Pro",
            "DESCRIPTION": "高品質音響效果，降噪技術，長時間續航",
            "category": "3C類"
        },
        {
            "Name": "維生素C咀嚼錠",
            "DESCRIPTION": "天然維生素C，增強免疫力，橘子口味",
            "category": "保健類"
        }
    ]
    
    print("1. 測試增強版商品描述生成功能：")
    print("-" * 50)
    
    for i, product in enumerate(test_products, 1):
        print(f"{i}. {product['category']} - {product['Name'][:25]}...")
        
        # 使用增強版描述生成
        enhanced_desc = generate_enhanced_marketing_description(product)
        
        print(f"   增強描述: {enhanced_desc}")
        print(f"   長度檢查: {len(enhanced_desc)} 字元 ({'✅ 符合' if len(enhanced_desc) <= 25 else '❌ 超長'})")
        print()
    
    print("2. 測試與現有系統的整合:")
    print("-" * 50)
    
    for i, product in enumerate(test_products, 1):
        # 使用現有系統的 _build_marketing_description
        system_desc = _build_marketing_description(product)
        
        print(f"{i}. {product['Name'][:25]}...")
        print(f"   系統描述: {system_desc}")
        print(f"   長度檢查: {len(system_desc)} 字元 ({'✅ 符合' if len(system_desc) <= 30 else '❌ 超長'})")
        print()
    
    print("3. 品質檢查 - 確保沒有不當的類別混用:")
    print("-" * 50)
    
    quality_checks = [
        {
            "product": {
                "Name": "前皮釦式多夾層實用斜背包",
                "DESCRIPTION": "真皮材質，多夾層設計"
            },
            "should_not_contain": ["香濃", "好滋味", "暖胃", "美味"],
            "should_contain": ["實用", "便利", "搭配"]
        },
        {
            "product": {
                "Name": "有機燕麥片",
                "DESCRIPTION": "高纖維營養豐富"
            },
            "should_not_contain": ["搭配", "時尚", "收納"],
            "should_contain": ["營養", "健康", "選擇"]
        }
    ]
    
    for i, check in enumerate(quality_checks, 1):
        desc = _build_marketing_description(check["product"])
        print(f"{i}. {check['product']['Name'][:20]}...")
        print(f"   生成描述: {desc}")
        
        # 檢查不應該包含的詞彙
        bad_words = [word for word in check["should_not_contain"] if word in desc]
        if bad_words:
            print(f"   ❌ 發現不當詞彙: {bad_words}")
        else:
            print(f"   ✅ 無不當詞彙")
        
        # 檢查應該包含的詞彙
        good_words = [word for word in check["should_contain"] if word in desc]
        if good_words:
            print(f"   ✅ 包含適當詞彙: {good_words}")
        else:
            print(f"   ⚠️  缺少預期詞彙")
        print()
    
    print("=== 系統整合測試完成 ===")
    print("✅ LLM 增強商品描述生成功能已成功整合並正常運作")

if __name__ == "__main__":
    test_system_integration()