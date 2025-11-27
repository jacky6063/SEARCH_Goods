#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試腳本：看到程式實際執行的路徑

使用方式：
1. 啟動後端: cd backend && python -m uvicorn app:app --reload --port 8000
2. 在另一個終端執行本腳本: python test_execution_paths.py

三個測試場景：
1. 熱門分類 UI 路徑（L3 直接過濾）
2. 單純 L3 查詢（快速路徑）
3. 普通文字搜尋（完整路徑）
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def print_section(title):
    """印出分隔線"""
    print("\n" + "=" * 100)
    print(f"  {title}")
    print("=" * 100 + "\n")

def test_hot_category_l3_filter():
    """測試 1: 熱門分類 UI L3 點擊（超快速路徑 ⚡⚡）"""
    print_section("測試 1: 熱門分類 UI L3 點擊（超快速路徑 ⚡⚡）")
    
    payload = {
        "query": "食品 米麞 米類",
        "page": 1,
        "page_size": 5,
        "category_hierarchy": {
            "L1": "食品",
            "L2": "米麞",
            "L3": "米類"
        },
        "prefer_special_first": True,
        "from_hot_category": True  # 🆕 關鍵標誌
    }
    
    print("📤 發送請求:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()
    
    start = time.time()
    try:
        response = requests.post(f"{BASE_URL}/api/search", json=payload, timeout=30)
        elapsed = time.time() - start
        
        print(f"✅ 回應 (耗時: {elapsed:.3f}s):")
        result = response.json()
        print(f"  - 訊息: {result.get('message')}")
        print(f"  - 結果筆數: {len(result.get('items', []))}")
        if result.get('items'):
            print(f"  - 第一筆: {result['items'][0].get('name', '未知')}")
    except Exception as e:
        print(f"❌ 請求失敗: {e}")

def test_l3_only_filter():
    """測試 2: L3 Only 查詢（快速路徑 ⚡）"""
    print_section("測試 2: L3 Only 查詢（快速路徑 ⚡）")
    
    payload = {
        "query": "米類",
        "page": 1,
        "page_size": 5,
        "category_hierarchy": {
            "L1": "",
            "L2": "",
            "L3": "米類"
        },
        "prefer_special_first": False,
        "from_hot_category": False  # 沒有此標誌
    }
    
    print("📤 發送請求:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()
    
    start = time.time()
    try:
        response = requests.post(f"{BASE_URL}/api/search", json=payload, timeout=30)
        elapsed = time.time() - start
        
        print(f"✅ 回應 (耗時: {elapsed:.3f}s):")
        result = response.json()
        print(f"  - 訊息: {result.get('message')}")
        print(f"  - 結果筆數: {len(result.get('items', []))}")
        if result.get('items'):
            print(f"  - 第一筆: {result['items'][0].get('name', '未知')}")
    except Exception as e:
        print(f"❌ 請求失敗: {e}")

def test_text_search():
    """測試 3: 普通文字搜尋（完整路徑 🔍）"""
    print_section("測試 3: 普通文字搜尋（完整路徑 🔍）")
    
    payload = {
        "query": "有機米",
        "page": 1,
        "page_size": 5,
        "prefer_special_first": False
    }
    
    print("📤 發送請求:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()
    
    start = time.time()
    try:
        response = requests.post(f"{BASE_URL}/api/search", json=payload, timeout=30)
        elapsed = time.time() - start
        
        print(f"✅ 回應 (耗時: {elapsed:.3f}s):")
        result = response.json()
        print(f"  - 訊息: {result.get('message')}")
        print(f"  - 結果筆數: {len(result.get('items', []))}")
        print(f"  - 意圖解析結果:")
        intent = result.get('intent', {})
        if intent:
            print(f"    - 必需詞: {intent.get('required_terms')}")
            print(f"    - 類別詞: {intent.get('category_terms')}")
            print(f"    - 分類層級: {intent.get('category_hierarchy')}")
    except Exception as e:
        print(f"❌ 請求失敗: {e}")

def test_multi_level_hierarchy():
    """測試 4: 多層級階層查詢（完整路徑 🔍）"""
    print_section("測試 4: 多層級階層查詢（完整路徑 🔍）")
    
    payload = {
        "query": "食品 穀類",
        "page": 1,
        "page_size": 5,
        "category_hierarchy": {
            "L1": "食品",
            "L2": "穀類",
            "L3": ""
        }
    }
    
    print("📤 發送請求:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()
    
    start = time.time()
    try:
        response = requests.post(f"{BASE_URL}/api/search", json=payload, timeout=30)
        elapsed = time.time() - start
        
        print(f"✅ 回應 (耗時: {elapsed:.3f}s):")
        result = response.json()
        print(f"  - 訊息: {result.get('message')}")
        print(f"  - 結果筆數: {len(result.get('items', []))}")
        if result.get('items'):
            print(f"  - 第一筆: {result['items'][0].get('name', '未知')}")
    except Exception as e:
        print(f"❌ 請求失敗: {e}")

if __name__ == "__main__":
    print("\n" + "█" * 100)
    print("█" + " " * 98 + "█")
    print("█" + " SEARCH_Goods 執行路徑追蹤測試 ".center(98) + "█")
    print("█" + " " * 98 + "█")
    print("█" * 100)
    
    print("\n📝 提示：在後端終端機觀看詳細的日誌輸出，以查看執行路徑\n")
    
    time.sleep(1)
    
    # 執行所有測試
    test_hot_category_l3_filter()
    time.sleep(1)
    
    test_l3_only_filter()
    time.sleep(1)
    
    test_text_search()
    time.sleep(1)
    
    test_multi_level_hierarchy()
    
    print_section("測試完成")
    print("✅ 所有測試完成！\n")
    print("📊 查看後端終端輸出以了解執行路徑的詳細信息")
    print("   你應該能看到不同的執行路徑被觸發:\n")
    print("   - 測試 1: ⚡⚡ 超快速路徑")
    print("   - 測試 2: ⚡ 快速路徑")
    print("   - 測試 3: 🔍 完整路徑 (包含 LLM 查詢擴展和意圖分析)")
    print("   - 測試 4: 🔍 完整路徑 (L1+L2 逐層驗證)")
    print()
