#!/usr/bin/env python3
"""
測試「台灣日曬木茸」查詢的商品過濾 (不需要 OpenAI API)
"""
import sys
import os

# 添加 backend 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from goods_search_service import search_products, load_data
import pandas as pd
import os

# 取得 CSV 路徑
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'VIEW_GOODS_enhanced.csv')

def test_mushroom_search_results():
    """測試商品搜尋結果是否相關"""
    print("\n" + "="*70)
    print("🧪 測試: 木茸查詢的商品搜尋結果相關性")
    print("="*70)
    
    # 載入數據
    print("\n📂 載入商品數據...")
    df = load_data(DATA_PATH)
    print(f"   已載入 {len(df)} 筆商品")
    
    query = "台灣日曬木茸"
    
    try:
        print(f"\n📝 查詢: {query}")
        results, terms = search_products(df, query, topn=10)
        
        print(f"📊 找到 {len(results)} 筆結果")
        print(f"🔤 提取詞彙: {terms}\n")
        
        if not results:
            print("❌ 沒有找到任何結果")
            return False
        
        # 分析結果相關性
        relevant_count = 0
        irrelevant_products = []
        
        print("="*70)
        print("商品列表與分類分析:")
        print("="*70)
        
        for i, product in enumerate(results, 1):
            name = product.get('商品名稱', '')
            l1 = product.get('L1分類', '')
            l2 = product.get('L2分類', '')
            l3 = product.get('L3分類', '')
            score = product.get('score', 0)
            
            # 判斷是否相關
            # 規則: 
            # 1. 必須是常溫食品
            # 2. 優先: 烹調食材分類或商品名含菇類關鍵字
            # 3. 可接受: 其他食材相關小分類 (米類、麵條、醬油等食品)
            is_mushroom = any(keyword in name for keyword in ['木茸', '香菇', '木耳', '菇'])
            is_food = l1 == '常溫食品'
            is_cooking_ingredient = l3 == '烹調食材'
            
            # 相關性判斷
            if is_mushroom or is_cooking_ingredient:
                is_relevant = True
                relevance_reason = "✅ 直接相關"
            elif is_food and l2 == '五穀/豆類/米麵/乾貨':
                is_relevant = True  # 同一中分類下的其他小分類也可接受
                relevance_reason = "✅ 相關 (同類食材)"
            else:
                is_relevant = False
                relevance_reason = "❌ 不相關"
            
            if is_relevant:
                relevant_count += 1
            else:
                irrelevant_products.append({
                    'name': name,
                    'l1': l1,
                    'l2': l2,
                    'l3': l3
                })
            
            print(f"\n{relevance_reason} {i}. {name}")
            print(f"   分類: {l1} > {l2} > {l3}")
            print(f"   分數: {score:.2f}")
        
        # 評估結果
        relevance_rate = relevant_count / len(results) * 100
        
        print("\n" + "="*70)
        print("📈 相關性統計:")
        print("="*70)
        print(f"  - 相關商品: {relevant_count}/{len(results)} ({relevance_rate:.0f}%)")
        
        if irrelevant_products:
            print(f"\n  ⚠️  不相關商品 ({len(irrelevant_products)} 件):")
            for item in irrelevant_products:
                print(f"    • {item['name']}")
                print(f"      分類: {item['l1']} > {item['l2']} > {item['l3']}")
        
        # 判斷標準: 至少 70% 相關
        is_good = relevance_rate >= 70
        
        print("\n" + "="*70)
        if is_good:
            print(f"✅ 搜尋結果相關性良好 ({relevance_rate:.0f}% ≥ 70%)")
        else:
            print(f"❌ 搜尋結果相關性不足 ({relevance_rate:.0f}% < 70%)")
        print("="*70)
        
        return is_good
        
    except Exception as e:
        print(f"\n❌ 商品搜尋失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_category_examples_in_code():
    """驗證 IMPORTANT_CATEGORY_EXAMPLES 是否已加入代碼"""
    print("\n" + "="*70)
    print("🔍 驗證: IMPORTANT_CATEGORY_EXAMPLES 是否存在於代碼中")
    print("="*70)
    
    llm_service_path = os.path.join(
        os.path.dirname(__file__), 
        'backend', 
        'llm_service.py'
    )
    
    with open(llm_service_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    has_dict = 'IMPORTANT_CATEGORY_EXAMPLES' in content
    has_mushroom = '烹調食材' in content and ('木茸' in content or '香菇' in content)
    
    print(f"\n  - IMPORTANT_CATEGORY_EXAMPLES 字典: {'✅ 存在' if has_dict else '❌ 不存在'}")
    print(f"  - 烹調食材與菇類範例: {'✅ 存在' if has_mushroom else '❌ 不存在'}")
    
    if has_dict and has_mushroom:
        print("\n✅ 代碼修改已正確應用!")
        return True
    else:
        print("\n❌ 代碼修改未正確應用!")
        return False

def main():
    print("\n" + "="*70)
    print("🎯 木茸查詢優化驗證測試 (簡化版 - 不需 OpenAI API)")
    print("="*70)
    print("\n目標: 驗證商品搜尋結果是否過濾掉不相關的商品\n")
    
    # 執行測試
    test1_passed = verify_category_examples_in_code()
    test2_passed = test_mushroom_search_results()
    
    # 總結
    print("\n" + "="*70)
    print("📊 測試總結")
    print("="*70)
    print(f"  測試 1 (代碼修改驗證): {'✅ 通過' if test1_passed else '❌ 失敗'}")
    print(f"  測試 2 (搜尋結果相關性): {'✅ 通過' if test2_passed else '❌ 失敗'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 測試通過! 代碼修改已成功!")
        print("\n💡 備註:")
        print("  - IMPORTANT_CATEGORY_EXAMPLES 已加入 llm_service.py")
        print("  - _build_category_hierarchy_prompt() 已更新")
        print("  - 商品搜尋結果相關性良好")
        print("\n  ⚠️  完整的 LLM 分類識別測試需要設定 OPENAI_API_KEY")
        return 0
    else:
        print("\n⚠️  部分測試未通過,需要進一步調整")
        return 1

if __name__ == '__main__':
    sys.exit(main())
