#!/usr/bin/env python3
"""
快速測試: 驗證「台灣日曬木茸」查詢結果
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from goods_search_service import search_products, load_data
import json

# 載入數據
print("📂 載入商品數據...")
csv_path = os.path.join(os.path.dirname(__file__), 'data', 'VIEW_GOODS_enhanced.csv')
df = load_data(csv_path)
print(f"✅ 已載入 {len(df)} 筆商品\n")

# 執行搜尋
query = "台灣日曬木茸"
print(f"🔍 查詢: {query}")
results, terms = search_products(df, query, topn=10)
print(f"📊 找到 {len(results)} 筆結果\n")

# 顯示結果 
print("="*80)
print("搜尋結果:")
print("="*80)

if not results:
    print("❌ 沒有找到任何結果")
else:
    for i, item in enumerate(results, 1):
        # 打印所有可用的 keys
        if i == 1:
            print(f"\n可用欄位: {list(item.keys())}\n")
        
        print(f"\n{i}. ", end="")
        
        # 嘗試不同的欄位名稱
        name = (item.get('商品名稱') or item.get('GoodName') or 
                item.get('Name') or item.get('name') or '(未知商品)')
        print(f"{name}")
        
        # 分類資訊
        l1 = item.get('L1分類') or item.get('L1Category') or item.get('L1') or ''
        l2 = item.get('L2分類') or item.get('L2Category') or item.get('L2') or ''
        l3 = item.get('L3分類') or item.get('L3Category') or item.get('L3') or ''
        
        if l1 or l2 or l3:
            print(f"   分類: {l1} > {l2} > {l3}")
        
        # 分數
        score = item.get('score') or item.get('__score__') or 0
        print(f"   分數: {score:.2f}")
        
        # 特價
        special = item.get('SpecialOffer') or item.get('特價') or ''
        price = item.get('Price') or item.get('價格') or ''
        if special or price:
            print(f"   價格: {price} (特價: {special})")

print("\n" + "="*80)
print(f"\n💡 提取詞彙: {terms}")
