#!/usr/bin/env python3
"""
測試 session_id 一致性修正

驗證：
1. repair_sessions.session_id 應該與 chat_messages.session_id 一致
2. 兩者都應該來自 session_events.session_id
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_repair_chat():
    """測試維修對話，檢查 session_id 一致性"""
    
    print("=" * 70)
    print("🧪 測試 session_id 一致性修正")
    print("=" * 70)
    
    # 步驟 1：發送維修訊息
    print("\n步驟 1：發送維修訊息...")
    payload = {
        "message": "測試：廚房水龍頭漏水",
        "session_id": None,  # 不提供 session_id，讓後端自動生成
        "history": [],
        "topn": 3
    }
    
    response = requests.post(f"{BASE_URL}/api/repair/chat", json=payload)
    
    if response.status_code != 200:
        print(f"❌ API 調用失敗: {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    session_id = data.get("session_id")
    
    print(f"✅ 收到回覆")
    print(f"   Session ID: {session_id}")
    print(f"   回覆: {data.get('reply', '')[:50]}...")
    
    if not session_id:
        print("❌ 沒有收到 session_id")
        return
    
    # 步驟 2：查詢 repair_sessions
    print(f"\n步驟 2：查詢 repair_sessions 表...")
    try:
        status_response = requests.get(f"{BASE_URL}/api/repair/session/{session_id}/status")
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"✅ repair_sessions 記錄存在")
            print(f"   Session ID: {status_data.get('session_id')}")
            print(f"   Manual Mode: {status_data.get('manual_mode')}")
            print(f"   Status: {status_data.get('status')}")
        else:
            print(f"❌ repair_sessions 記錄不存在 (HTTP {status_response.status_code})")
            return
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")
        return
    
    # 步驟 3：查詢 chat_messages
    print(f"\n步驟 3：查詢 chat_messages 表...")
    try:
        messages_response = requests.get(f"{BASE_URL}/api/repair/session/{session_id}/messages")
        
        if messages_response.status_code == 200:
            messages_data = messages_response.json()
            message_count = messages_data.get('total_count', 0)
            print(f"✅ chat_messages 記錄存在")
            print(f"   Session ID: {messages_data.get('session_id')}")
            print(f"   訊息數量: {message_count}")
            
            # 顯示訊息詳情
            for msg in messages_data.get('messages', []):
                print(f"   - [{msg['role']}] {msg['content'][:30]}...")
        else:
            print(f"❌ chat_messages 記錄不存在 (HTTP {messages_response.status_code})")
            return
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")
        return
    
    # 步驟 4：驗證一致性
    print(f"\n步驟 4：驗證 session_id 一致性...")
    repair_session_id = status_data.get('session_id')
    chat_session_id = messages_data.get('session_id')
    
    if repair_session_id == chat_session_id == session_id:
        print(f"✅ Session ID 完全一致！")
        print(f"   API 返回: {session_id}")
        print(f"   repair_sessions: {repair_session_id}")
        print(f"   chat_messages: {chat_session_id}")
        print(f"\n🎉 測試通過！session_id 一致性修正成功！")
    else:
        print(f"❌ Session ID 不一致！")
        print(f"   API 返回: {session_id}")
        print(f"   repair_sessions: {repair_session_id}")
        print(f"   chat_messages: {chat_session_id}")
        print(f"\n⚠️ 需要進一步檢查程式碼")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    test_repair_chat()
