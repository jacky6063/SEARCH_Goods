"""
調試智能模板生成問題
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from llm_service import generate_smart_template_description, detect_product_category

def debug_template_generation():
    """調試智能模板生成問題"""
    
    test_item = {
        "Name": "前皮釦式多夾層實用斜背包-黑色",
        "DESCRIPTION": "真皮材質，多夾層設計，可調節背帶，實用便利"
    }
    
    print("=== 調試智能模板生成問題 ===")
    print(f"商品名稱: {test_item['Name']}")
    print(f"商品描述: {test_item['DESCRIPTION']}")
    print()
    
    # 步驟 1: 檢查類別檢測
    category = detect_product_category(test_item['Name'], test_item['DESCRIPTION'])
    print(f"檢測類別: {category}")
    
    # 步驟 2: 檢查名稱核心提取
    name_core = test_item['Name']
    print(f"原始名稱: {name_core}")
    
    import re
    name_core = re.sub(r"[（(].*?[)）]", "", name_core)
    print(f"移除括號後: {name_core}")
    
    name_core = re.split(r"[／/\-]", name_core)[0]
    print(f"分割後取第一部分: {name_core}")
    
    name_core = re.sub(r"\d+(?:g|ml|包|袋|入|瓶|顆|公分|cm)", "", name_core, flags=re.IGNORECASE)
    print(f"移除規格後: {name_core}")
    
    name_core = name_core.strip()
    print(f"去除空白後: {name_core}")
    
    if len(name_core) > 8:
        truncated = name_core[:8]
        print(f"初步截斷至 8 字元: {truncated}")
        # 如果最後一個字是常見詞彙的開頭，退一個字
        if truncated.endswith(('實', '多', '前', '後', '上', '下')):
            truncated = truncated[:-1]
            print(f"智能截斷避免詞彙中斷: {truncated}")
        name_core = truncated
    
    print()
    
    # 步驟 3: 生成完整描述
    result = generate_smart_template_description(test_item)
    print(f"最終生成結果: {result}")

if __name__ == "__main__":
    debug_template_generation()