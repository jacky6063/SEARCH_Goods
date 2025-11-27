#!/usr/bin/env python3
"""
意圖切換測試腳本
測試公司查詢、商品查詢和維修查詢之間的切換功能
"""

import requests
import json
import time
from typing import Dict, List, Any

# 測試配置
BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{BASE_URL}/api/chat"
REPAIR_ENDPOINT = f"{BASE_URL}/api/repair/chat"

class IntentSwitchTester:
    def __init__(self):
        self.session_id = None
        self.test_results = []
        
    def test_case(self, name: str, messages: List[Dict[str, str]], expected_intents: List[str]):
        """執行單一測試案例"""
        print(f"\n{'='*60}")
        print(f"測試案例: {name}")
        print(f"{'='*60}")
        
        history = []
        results = []
        
        for i, (msg, expected_intent) in enumerate(zip(messages, expected_intents), 1):
            print(f"\n第 {i} 輪對話:")
            print(f"  使用者: {msg['content']}")
            print(f"  預期意圖: {expected_intent}")
            
            # 根據訊息內容決定要呼叫哪個 API
            # 實際上前端會自動路由，這裡我們測試兩個端點
            
            # 嘗試聊天端點
            chat_payload = {
                "message": msg["content"],
                "history": history,
                "topn": 5,
                "session_id": self.session_id or "test-session"
            }
            
            try:
                response = requests.post(CHAT_ENDPOINT, json=chat_payload, timeout=30)
                response_data = response.json()
                
                # 檢查回應中的意圖標記
                actual_intent = response_data.get("_intent", "unknown")
                reply = response_data.get("reply", "")
                
                print(f"  實際意圖: {actual_intent}")
                print(f"  回應: {reply[:100]}...")
                
                # 記錄結果
                passed = actual_intent == expected_intent
                results.append({
                    "round": i,
                    "message": msg["content"],
                    "expected": expected_intent,
                    "actual": actual_intent,
                    "passed": passed,
                    "reply": reply[:200]
                })
                
                # 更新對話歷史
                history.append({"role": "user", "content": msg["content"]})
                history.append({"role": "assistant", "content": reply})
                
                if passed:
                    print(f"  ✅ 通過")
                else:
                    print(f"  ❌ 失敗")
                    
            except Exception as e:
                print(f"  ❌ 錯誤: {e}")
                results.append({
                    "round": i,
                    "message": msg["content"],
                    "expected": expected_intent,
                    "actual": "error",
                    "passed": False,
                    "error": str(e)
                })
            
            time.sleep(1)  # 避免請求過快
        
        # 統計結果
        passed_count = sum(1 for r in results if r["passed"])
        total_count = len(results)
        success_rate = (passed_count / total_count * 100) if total_count > 0 else 0
        
        print(f"\n測試結果: {passed_count}/{total_count} 通過 ({success_rate:.1f}%)")
        
        self.test_results.append({
            "name": name,
            "results": results,
            "passed": passed_count,
            "total": total_count,
            "success_rate": success_rate
        })
        
        return success_rate == 100

    def run_all_tests(self):
        """執行所有測試案例"""
        print("\n" + "="*60)
        print("開始意圖切換測試")
        print("="*60)
        
        # 測試案例 1: 公司 → 維修
        self.test_case(
            "測試 1: 公司查詢 → 維修查詢",
            [
                {"content": "你們公司在哪裡？"},
                {"content": "水龍頭滴水怎麼辦？"}
            ],
            ["shopping", "repair"]  # 公司查詢會被歸類為 shopping (走 /api/chat)
        )
        
        # 測試案例 2: 商品 → 維修
        self.test_case(
            "測試 2: 商品查詢 → 維修查詢",
            [
                {"content": "有便宜的冷氣嗎？"},
                {"content": "冷氣不冷怎麼辦？"}
            ],
            ["shopping", "repair"]
        )
        
        # 測試案例 3: 維修 → 公司
        self.test_case(
            "測試 3: 維修查詢 → 公司查詢",
            [
                {"content": "馬桶堵塞怎麼處理？"},
                {"content": "你們公司電話多少？"}
            ],
            ["repair", "shopping"]
        )
        
        # 測試案例 4: 維修 → 商品
        self.test_case(
            "測試 4: 維修查詢 → 商品查詢",
            [
                {"content": "漏水問題"},
                {"content": "推薦便宜的水龍頭"}
            ],
            ["repair", "shopping"]
        )
        
        # 測試案例 5: 混合場景
        self.test_case(
            "測試 5: 混合意圖切換",
            [
                {"content": "你們賣什麼？"},
                {"content": "有冷氣嗎？"},
                {"content": "冷氣滴水怎麼辦？"},
                {"content": "那推薦其他冷氣"}
            ],
            ["shopping", "shopping", "repair", "shopping"]
        )
        
        # 輸出總結報告
        self.print_summary()
    
    def print_summary(self):
        """輸出測試總結"""
        print("\n" + "="*60)
        print("測試總結")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for t in self.test_results if t["success_rate"] == 100)
        
        print(f"\n總測試案例: {total_tests}")
        print(f"通過案例: {passed_tests}")
        print(f"失敗案例: {total_tests - passed_tests}")
        print(f"總成功率: {(passed_tests / total_tests * 100):.1f}%")
        
        print("\n各案例詳情:")
        for test in self.test_results:
            status = "✅" if test["success_rate"] == 100 else "❌"
            print(f"{status} {test['name']}: {test['passed']}/{test['total']} ({test['success_rate']:.1f}%)")
        
        # 輸出 JSON 報告
        with open("intent_switch_test_report.json", "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n詳細報告已儲存至: intent_switch_test_report.json")

def main():
    """主程式"""
    print("意圖切換測試工具")
    print("="*60)
    print(f"測試目標: {BASE_URL}")
    print("確保後端服務已啟動...")
    
    # 檢查後端是否運行
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 後端服務運行中\n")
        else:
            print("⚠️ 後端服務狀態異常\n")
    except Exception as e:
        print(f"❌ 無法連接到後端服務: {e}")
        print("請先啟動後端服務:")
        print("  cd backend && uvicorn app:app --reload")
        return
    
    # 執行測試
    tester = IntentSwitchTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
