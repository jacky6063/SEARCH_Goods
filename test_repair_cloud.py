#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
住宅維修服務雲端測試腳本
用途: 快速驗證 Render 環境的維修服務是否正常啟用
"""
import requests
import json
import sys
from typing import Dict, Any

# 🔧 配置
BACKEND_URL = "https://search-goods-backend.onrender.com"  # 請替換為實際的 Render 後端網址
TEST_QUERIES = [
    "馬桶嚴重堵塞",
    "水龍頭滴水怎麼辦",
    "跳電維修",
    "熱水器點不著"
]

def test_health() -> bool:
    """測試後端健康狀態"""
    print("🔍 [Test 1] 檢查後端健康狀態...")
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=10)
        if resp.status_code == 200:
            print("   ✅ 後端服務正常運行")
            data = resp.json()
            print(f"   📊 服務資訊: {json.dumps(data, ensure_ascii=False, indent=2)}")
            return True
        else:
            print(f"   ❌ 後端回應異常: {resp.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 連線失敗: {e}")
        return False

def test_repair_endpoint() -> bool:
    """測試維修端點是否可用"""
    print("\n🔍 [Test 2] 檢查維修端點...")
    endpoint = f"{BACKEND_URL}/api/repair/chat"
    
    test_payload = {
        "message": "測試連線",
        "history": [],
        "topn": 1
    }
    
    try:
        resp = requests.post(
            endpoint,
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if resp.status_code == 200:
            print("   ✅ 維修端點可訪問")
            return True
        elif resp.status_code == 404:
            print("   ❌ 維修端點不存在 (404)")
            print("   💡 可能原因: ENABLE_REPAIR_SERVICE 未設定為 True")
            return False
        else:
            print(f"   ⚠️ 端點回應異常: {resp.status_code}")
            print(f"   回應內容: {resp.text[:200]}")
            return False
    except requests.exceptions.Timeout:
        print("   ⚠️ 請求超時（可能是冷啟動，請稍後重試）")
        return False
    except Exception as e:
        print(f"   ❌ 請求失敗: {e}")
        return False

def test_repair_queries() -> Dict[str, bool]:
    """測試維修查詢功能"""
    print("\n🔍 [Test 3] 測試維修查詢功能...")
    endpoint = f"{BACKEND_URL}/api/repair/chat"
    results = {}
    
    for query in TEST_QUERIES:
        print(f"\n   📝 測試: \"{query}\"")
        
        payload = {
            "message": query,
            "history": [],
            "topn": 5
        }
        
        try:
            resp = requests.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if resp.status_code != 200:
                print(f"      ❌ 請求失敗: {resp.status_code}")
                results[query] = False
                continue
            
            data = resp.json()
            
            # 檢查回應結構
            if "reply" not in data:
                print("      ⚠️ 回應缺少 'reply' 欄位")
                results[query] = False
                continue
            
            if "repairs" not in data:
                print("      ⚠️ 回應缺少 'repairs' 欄位")
                results[query] = False
                continue
            
            # 檢查維修項目
            repairs = data.get("repairs", [])
            reply = data.get("reply", "")
            
            print(f"      📨 回應: {reply[:100]}...")
            print(f"      🔧 維修項目數: {len(repairs)}")
            
            if len(repairs) > 0:
                print(f"      ✅ 找到 {len(repairs)} 個維修項目")
                # 顯示第一個維修項目
                first_repair = repairs[0]
                print(f"         • 項目: {first_repair.get('維修項目', 'N/A')}")
                print(f"         • 類別: {first_repair.get('維修類別', 'N/A')}")
                print(f"         • 緊急度: {first_repair.get('緊急程度', 'N/A')}")
                results[query] = True
            else:
                print(f"      ⚠️ 沒有找到維修項目（可能是資料庫問題）")
                results[query] = False
                
        except requests.exceptions.Timeout:
            print("      ⚠️ 請求超時")
            results[query] = False
        except Exception as e:
            print(f"      ❌ 測試失敗: {e}")
            results[query] = False
    
    return results

def print_summary(health_ok: bool, endpoint_ok: bool, query_results: Dict[str, bool]):
    """列印測試總結"""
    print("\n" + "="*60)
    print("📊 測試總結")
    print("="*60)
    
    total_tests = 3
    passed = 0
    
    print(f"\n[1] 後端健康檢查: {'✅ PASS' if health_ok else '❌ FAIL'}")
    if health_ok:
        passed += 1
    
    print(f"[2] 維修端點可用性: {'✅ PASS' if endpoint_ok else '❌ FAIL'}")
    if endpoint_ok:
        passed += 1
    
    print(f"[3] 維修查詢功能:")
    query_success = sum(1 for v in query_results.values() if v)
    query_total = len(query_results)
    if query_success == query_total:
        print(f"    ✅ PASS ({query_success}/{query_total} 查詢成功)")
        passed += 1
    else:
        print(f"    ⚠️ PARTIAL ({query_success}/{query_total} 查詢成功)")
    
    for query, success in query_results.items():
        status = "✅" if success else "❌"
        print(f"      {status} {query}")
    
    print(f"\n{'='*60}")
    print(f"總計: {passed}/{total_tests} 項測試通過")
    print("="*60)
    
    if passed == total_tests:
        print("\n🎉 所有測試通過！住宅維修服務已正常啟用。")
        return 0
    elif endpoint_ok:
        print("\n⚠️ 維修服務已啟用，但部分功能異常。請檢查:")
        print("   • 維修資料 CSV 檔案是否存在")
        print("   • OPENAI_API_KEY 是否正確設定")
        print("   • 後端日誌是否有錯誤訊息")
        return 1
    else:
        print("\n❌ 維修服務未啟用！請執行以下步驟:")
        print("   1. 在 Render Dashboard 設定: ENABLE_REPAIR_SERVICE=True")
        print("   2. 觸發重新部署 (Manual Deploy)")
        print("   3. 等待部署完成後重新執行此測試")
        return 2

def main():
    print("🔧 住宅維修服務雲端測試")
    print(f"📍 後端網址: {BACKEND_URL}")
    print("="*60)
    
    # 執行測試
    health_ok = test_health()
    endpoint_ok = test_repair_endpoint() if health_ok else False
    query_results = test_repair_queries() if endpoint_ok else {}
    
    # 列印總結
    exit_code = print_summary(health_ok, endpoint_ok, query_results)
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
