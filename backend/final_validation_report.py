# coding: utf-8
"""
廚房用品分類精度修正 - 最終驗證報告
"""

from planner.category_planner import detect_intent, build_plan, _validate_category_match, CATEGORY_KEYWORDS, NEGATIVE_KEYWORDS, CATEGORY_FIELD_MAPPING
import pandas as pd

def final_validation_report():
    """產生最終驗證報告"""
    
    print("=" * 60)
    print("廚房用品分類精度修正 - 最終驗證報告")
    print("=" * 60)
    
    # 1. 驗證分類規則
    print("\\n1. 分類規則驗證")
    print("-" * 30)
    
    keywords = CATEGORY_KEYWORDS.get("廚房用品", [])
    negative_keywords = NEGATIVE_KEYWORDS.get("廚房用品", [])
    category_fields = CATEGORY_FIELD_MAPPING.get("廚房用品", [])
    
    print(f"✅ 正面關鍵字: {len(keywords)} 個")
    print(f"✅ 負面關鍵字: {len(negative_keywords)} 個 (包含鍋粑、鍋巴等)")
    print(f"✅ 分類欄位: {len(category_fields)} 個")
    
    # 2. 測試問題商品過濾
    print("\\n2. 問題商品過濾驗證")
    print("-" * 30)
    
    problem_items = [
        {"name": "黑米鹹酥鍋粑/200g", "CateName": "餅乾/脆果"},
        {"name": "鹹酥鍋粑/200g", "CateName": "餅乾/脆果"},
        {"name": "五穀鹹酥鍋粑/200g", "CateName": "餅乾/脆果"},
        {"name": "紅麴鹹酥鍋粑/200g", "CateName": "餅乾/脆果"},
    ]
    
    filtered_count = 0
    for item in problem_items:
        result = _validate_category_match(item, "廚房用品", keywords, negative_keywords, category_fields)
        status = "❌ 已過濾" if not result else "⚠️  未過濾"
        print(f"{status}: {item['name']}")
        if not result:
            filtered_count += 1
    
    filter_rate = (filtered_count / len(problem_items)) * 100
    print(f"\\n過濾效果: {filter_rate:.0f}% ({filtered_count}/{len(problem_items)}) 問題商品被正確過濾")
    
    # 3. 測試真實廚房用具
    print("\\n3. 真實廚房用具驗證")
    print("-" * 30)
    
    real_kitchen_items = [
        {"name": "不銹鋼炒鍋 30cm", "CateName": "廚具"},
        {"name": "陶瓷湯鍋 3L", "CateName": "鍋具"},
        {"name": "平底鍋", "CateName": "廚房用品"},
        {"name": "砧板", "CateName": "廚具"},
        {"name": "菜刀", "CateName": "廚房用具"},
    ]
    
    passed_count = 0
    for item in real_kitchen_items:
        result = _validate_category_match(item, "廚房用品", keywords, negative_keywords, category_fields)
        status = "✅ 通過" if result else "❌ 被誤過濾"
        print(f"{status}: {item['name']}")
        if result:
            passed_count += 1
    
    pass_rate = (passed_count / len(real_kitchen_items)) * 100
    print(f"\\n正確識別率: {pass_rate:.0f}% ({passed_count}/{len(real_kitchen_items)}) 真實廚具被正確識別")
    
    # 4. 資料庫現狀分析
    print("\\n4. 資料庫現狀分析")
    print("-" * 30)
    
    try:
        df = pd.read_csv('../data/VIEW_GOODS_enhanced.csv')
        pot_items = df[df['商品名稱'].str.contains('鍋', na=False)]
        
        print(f"總商品數: {len(df)} 項")
        print(f"包含「鍋」字商品: {len(pot_items)} 項")
        
        print("\\n「鍋」字商品詳細:")
        for _, row in pot_items.iterrows():
            name = row['商品名稱']
            category = row['分類名稱']
            is_filtered = not _validate_category_match(
                {"name": name, "CateName": category}, 
                "廚房用品", keywords, negative_keywords, category_fields
            )
            status = "✅ 已過濾" if is_filtered else "⚠️  未過濾"
            print(f"  {status}: {name} ({category})")
            
    except Exception as e:
        print(f"資料庫分析失敗: {e}")
    
    # 5. 最終結論
    print("\\n5. 最終結論")
    print("-" * 30)
    
    if filter_rate >= 90 and pass_rate >= 90:
        print("✅ 分類精度修正成功！")
        print("   - 問題商品（鍋粑等）已被正確過濾")
        print("   - 真實廚房用具能被正確識別")
        print("   - 系統能有效區分食品與廚具")
    else:
        print("⚠️  分類精度需要進一步調整")
        print(f"   - 過濾效果: {filter_rate:.0f}%")
        print(f"   - 識別效果: {pass_rate:.0f}%")
    
    # 6. 使用建議
    print("\\n6. 使用建議")
    print("-" * 30)
    print("💡 由於當前資料庫主要為食品商品，廚房用品查詢可能會:")
    print("   1. 正確過濾掉「鍋粑」等零食類商品")
    print("   2. 無法找到真正的鍋具、餐具")
    print("   3. 可能推薦洗碗精等廚房相關清潔用品")
    print("\\n💡 若需要測試真實廚房用具推薦，建議:")
    print("   1. 增加鍋具、餐具等商品資料")
    print("   2. 或使用現有的清潔用品類別進行測試")
    
    print("\\n" + "=" * 60)

if __name__ == "__main__":
    final_validation_report()