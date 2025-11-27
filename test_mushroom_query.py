#!/usr/bin/env python3
"""
測試「台灣日曬木茸」查詢的分類識別與商品過濾
"""
import sys
import os

# 添加 backend 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from llm_service import llm_analyze_query
from goods_search_service import search_products, load_goods_data
import pandas as pd

# 載入商品數據
df = load_goods_data()

def test_mushroom_category_recognition():
    """測試 LLM 是否能正確識別木茸的分類層級"""
    print("\n" + "="*70)
    print("🧪 測試 1: LLM 分類識別 - 台灣日曬木茸")
    print("="*70)
    
    query = "台灣日曬木茸"
    
    try:
        result = llm_analyze_query(query)
        
        print(f"\n📝 查詢: {query}")
        print(f"\n🔍 LLM 分析結果:")
        print(f"  - L1 大分類: {result.get('category_hierarchy', {}).get('L1', 'N/A')}")
        print(f"  - L2 中分類: {result.get('category_hierarchy', {}).get('L2', 'N/A')}")
        print(f"  - L3 小分類: {result.get('category_hierarchy', {}).get('L3', 'N/A')}")
        print(f"  - 信心度: L1={result.get('confidence', {}).get('L1', 0):.2f}, "
              f"L2={result.get('confidence', {}).get('L2', 0):.2f}, "
              f"L3={result.get('confidence', {}).get('L3', 0):.2f}")
        print(f"  - 匹配關鍵字: {result.get('matching_keywords', [])}")
        
        # 檢查是否正確識別
        hierarchy = result.get('category_hierarchy', {})
        expected = {
            'L1': '常溫食品',
            'L2': '五穀/豆類/米麵/乾貨',
            'L3': '烹調食材'
        }
        
        is_correct = (
            hierarchy.get('L1') == expected['L1'] and
            hierarchy.get('L2') == expected['L2'] and
            hierarchy.get('L3') == expected['L3']
        )
        
        if is_correct:
            print(f"\n✅ 分類識別正確!")
        else:
            print(f"\n❌ 分類識別錯誤!")
            print(f"  期望: {expected}")
            print(f"  實際: {hierarchy}")
        
        return is_correct, result
        
    except Exception as e:
        print(f"\n❌ LLM 分析失敗: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_mushroom_search_results():
    """測試商品搜尋結果是否相關"""
    print("\n" + "="*70)
    print("🧪 測試 2: 商品搜尋結果相關性")
    print("="*70)
    
    query = "台灣日曬木茸"
    
    try:
        results, terms = search_products(df, query, topn=10)
        
        print(f"\n📝 查詢: {query}")
        print(f"📊 找到 {len(results)} 筆結果\n")
        
        if not results:
            print("❌ 沒有找到任何結果")
            return False
        
        # 分析結果相關性
        relevant_count = 0
        irrelevant_products = []
        
        for i, product in enumerate(results, 1):
            name = product.get('商品名稱', '')
            l1 = product.get('L1分類', '')
            l2 = product.get('L2分類', '')
            l3 = product.get('L3分類', '')
            score = product.get('score', 0)
            
            # 判斷是否相關 (簡化規則: 食品類 + 包含菇類/木茸/食材關鍵字)
            is_relevant = (
                l1 == '常溫食品' and
                ('木茸' in name or '香菇' in name or '黑木耳' in name or 
                 '白木耳' in name or '海帶' in name or l3 == '烹調食材')
            )
            
            if is_relevant:
                relevant_count += 1
                status = "✅"
            else:
                status = "❌"
                irrelevant_products.append(name)
            
            print(f"{status} {i}. {name}")
            print(f"   分類: {l1} > {l2} > {l3}")
            print(f"   分數: {score:.2f}\n")
        
        # 評估結果
        relevance_rate = relevant_count / len(results) * 100
        
        print(f"\n📈 相關性統計:")
        print(f"  - 相關商品: {relevant_count}/{len(results)} ({relevance_rate:.0f}%)")
        
        if irrelevant_products:
            print(f"  - 不相關商品:")
            for name in irrelevant_products:
                print(f"    • {name}")
        
        # 判斷標準: 至少 70% 相關
        is_good = relevance_rate >= 70
        
        if is_good:
            print(f"\n✅ 搜尋結果相關性良好 ({relevance_rate:.0f}% ≥ 70%)")
        else:
            print(f"\n❌ 搜尋結果相關性不足 ({relevance_rate:.0f}% < 70%)")
        
        return is_good
        
    except Exception as e:
        print(f"\n❌ 商品搜尋失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*70)
    print("🎯 木茸查詢優化驗證測試")
    print("="*70)
    print("\n目標: 驗證 IMPORTANT_CATEGORY_EXAMPLES 和優化後的 Prompt")
    print("      是否能正確識別「木茸」為「烹調食材」分類\n")
    
    # 執行測試
    test1_passed, llm_result = test_mushroom_category_recognition()
    test2_passed = test_mushroom_search_results()
    
    # 總結
    print("\n" + "="*70)
    print("📊 測試總結")
    print("="*70)
    print(f"  測試 1 (LLM 分類識別): {'✅ 通過' if test1_passed else '❌ 失敗'}")
    print(f"  測試 2 (搜尋結果相關性): {'✅ 通過' if test2_passed else '❌ 失敗'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 所有測試通過! 優化成功!")
        return 0
    else:
        print("\n⚠️  部分測試未通過,需要進一步調整")
        return 1

if __name__ == '__main__':
    sys.exit(main())
