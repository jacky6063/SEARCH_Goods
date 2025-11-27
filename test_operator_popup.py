#!/usr/bin/env python3
"""
真人客服彈窗功能快速測試腳本

測試項目:
1. 建立測試 session
2. 切換為真人接手模式
3. 查詢 session 狀態
4. 恢復 AI 自動模式
"""

import requests
import json
import time
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"
TEST_OPERATOR_ID = "TEST_OP_001"
TEST_OPERATOR_NAME = "測試客服"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_create_session():
    """測試建立 session"""
    print_section("1. 測試建立 session")
    
    url = f"{BASE_URL}/api/repair/chat"
    payload = {
        "message": "測試：餐桌的插座發熱怎麼辦",
        "history": [],
        "topn": 5
    }
    
    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    response = requests.post(url, json=payload)
    
    print(f"\nStatus: {response.status_code}")
    
    if response.ok:
        data = response.json()
        session_id = data.get('session_id')
        print(f"✅ Session 建立成功!")
        print(f"   Session ID: {session_id}")
        print(f"   回覆: {data.get('reply', '')[:100]}...")
        return session_id
    else:
        print(f"❌ 建立失敗: {response.text}")
        return None

def test_check_status(session_id):
    """測試查詢 session 狀態"""
    print_section("2. 查詢 session 狀態")
    
    url = f"{BASE_URL}/api/repair/session/{session_id}/status"
    
    print(f"GET {url}")
    
    response = requests.get(url)
    
    print(f"\nStatus: {response.status_code}")
    
    if response.ok:
        data = response.json()
        print(f"✅ 狀態查詢成功!")
        print(f"   Session ID: {data.get('session_id')}")
        print(f"   Manual Mode: {data.get('manual_mode')}")
        print(f"   Operator: {data.get('operator_name') or '(無)'}")
        print(f"   Status: {data.get('status')}")
        return data
    else:
        print(f"❌ 查詢失敗: {response.text}")
        return None

def test_manual_mode(session_id, manual_mode, operator_id=None, operator_name=None):
    """測試切換對話模式"""
    mode_text = "真人接手" if manual_mode else "AI 自動回覆"
    print_section(f"3. 切換為{mode_text}")
    
    url = f"{BASE_URL}/api/repair/manual_mode"
    payload = {
        "session_id": session_id,
        "manual_mode": manual_mode,
        "operator_id": operator_id if manual_mode else None,
        "operator_name": operator_name if manual_mode else None
    }
    
    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    response = requests.post(url, json=payload)
    
    print(f"\nStatus: {response.status_code}")
    
    if response.ok:
        data = response.json()
        print(f"✅ 模式切換成功!")
        print(f"   Message: {data.get('message')}")
        print(f"   Manual Mode: {data.get('manual_mode')}")
        if manual_mode:
            print(f"   Operator: {data.get('operator_id')} - {operator_name}")
        return True
    else:
        print(f"❌ 切換失敗: {response.text}")
        return False

def test_get_messages(session_id):
    """測試查詢對話記錄"""
    print_section("4. 查詢對話記錄")
    
    url = f"{BASE_URL}/api/repair/session/{session_id}/messages?limit=10"
    
    print(f"GET {url}")
    
    response = requests.get(url)
    
    print(f"\nStatus: {response.status_code}")
    
    if response.ok:
        data = response.json()
        messages = data.get('messages', [])
        print(f"✅ 對話記錄查詢成功!")
        print(f"   總數: {data.get('total_count')}")
        print(f"   訊息:")
        for msg in messages[:5]:  # 只顯示前5筆
            role_icon = '👤' if msg['role'] == 'user' else ('👩‍💼' if msg['role'] in ['Humans', 'operator'] else '🤖')
            print(f"     {role_icon} {msg['role']}: {msg['content'][:50]}...")
        return True
    else:
        print(f"❌ 查詢失敗: {response.text}")
        return False

def main():
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     真人客服彈窗功能 - API 測試腳本                          ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\n測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"後端URL: {BASE_URL}")
    
    # 測試流程
    try:
        # 1. 建立 session
        session_id = test_create_session()
        if not session_id:
            print("\n❌ 無法建立 session，測試中止")
            return
        
        time.sleep(1)
        
        # 2. 查詢初始狀態 (應該是 manual_mode=False)
        status = test_check_status(session_id)
        if not status:
            print("\n❌ 無法查詢狀態，測試中止")
            return
        
        time.sleep(1)
        
        # 3. 切換為真人接手
        success = test_manual_mode(
            session_id, 
            manual_mode=True,
            operator_id=TEST_OPERATOR_ID,
            operator_name=TEST_OPERATOR_NAME
        )
        if not success:
            print("\n❌ 無法切換模式，測試中止")
            return
        
        time.sleep(1)
        
        # 4. 再次查詢狀態 (應該是 manual_mode=True)
        status = test_check_status(session_id)
        if status and status.get('manual_mode'):
            print("\n✅ 狀態變更確認成功!")
        
        time.sleep(1)
        
        # 5. 查詢對話記錄
        test_get_messages(session_id)
        
        time.sleep(1)
        
        # 6. 恢復 AI 自動模式
        test_manual_mode(session_id, manual_mode=False)
        
        time.sleep(1)
        
        # 7. 最終狀態檢查
        final_status = test_check_status(session_id)
        
        print_section("測試總結")
        print(f"Session ID: {session_id}")
        print(f"✅ 所有測試完成!")
        print(f"\n💡 提示:")
        print(f"   - 可在前端開啟 http://localhost:8000")
        print(f"   - 輸入維修問題後，session 會自動建立")
        print(f"   - 在 repair_chat_viewer.html 點擊「接手」")
        print(f"   - 3秒內前端應顯示彈窗")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 無法連線到後端服務")
        print(f"   請確認後端運行在 {BASE_URL}")
        print(f"   啟動指令: uvicorn app:app --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"\n❌ 測試發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
