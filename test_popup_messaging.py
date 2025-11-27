#!/usr/bin/env python3
"""
測試住戶端彈窗訊息功能

驗證：
1. 客服訊息能正確顯示在彈窗中
2. 住戶可以在彈窗中發送訊息
"""

import requests
import time

BASE_URL = "http://localhost:8000"

def test_popup_messaging():
    """測試彈窗訊息功能"""
    
    print("=" * 70)
    print("🧪 測試住戶端彈窗訊息功能")
    print("=" * 70)
    
    # 步驟 1：住戶發送維修訊息
    print("\n步驟 1：住戶發送維修訊息...")
    payload = {
        "message": "浴室馬桶堵塞，需要疏通",
        "session_id": None,
        "history": [],
        "topn": 3
    }
    
    response = requests.post(f"{BASE_URL}/api/repair/chat", json=payload)
    
    if response.status_code != 200:
        print(f"❌ API 調用失敗: {response.status_code}")
        return
    
    data = response.json()
    session_id = data.get("session_id")
    
    print(f"✅ 收到回覆")
    print(f"   Session ID: {session_id}")
    print(f"   AI 回覆: {data.get('reply', '')[:50]}...")
    
    # 步驟 2：模擬客服接手
    print(f"\n步驟 2：客服接手對話...")
    manual_mode_payload = {
        "session_id": session_id,
        "manual_mode": True,
        "operator_id": "OP001",
        "operator_name": "測試客服"
    }
    
    response = requests.post(f"{BASE_URL}/api/repair/manual_mode", json=manual_mode_payload)
    
    if response.status_code != 200:
        print(f"❌ 接手失敗: {response.status_code}")
        return
    
    print("✅ 客服接手成功")
    
    # 步驟 3：客服發送回覆
    print(f"\n步驟 3：客服發送回覆...")
    reply_data = {
        "reply": "您好！我已經收到您的問題，馬上安排師傅過去處理。預計 30 分鐘內抵達。",
        "operator_id": "OP001",
        "operator_name": "測試客服"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/repair/session/{session_id}/reply",
        data=reply_data
    )
    
    if response.status_code != 200:
        print(f"❌ 發送回覆失敗: {response.status_code}")
        print(response.text)
        return
    
    print("✅ 客服回覆已發送")
    
    # 步驟 4：查詢訊息記錄
    print(f"\n步驟 4：查詢訊息記錄...")
    time.sleep(1)  # 等待寫入完成
    
    response = requests.get(f"{BASE_URL}/api/repair/session/{session_id}/messages?limit=50")
    
    if response.status_code != 200:
        print(f"❌ 查詢失敗: {response.status_code}")
        return
    
    data = response.json()
    messages = data.get('messages', [])
    
    print(f"✅ 訊息記錄 (共 {len(messages)} 則):")
    
    has_user_message = False
    has_ai_message = False
    has_human_message = False
    
    for i, msg in enumerate(messages, 1):
        role_icon = {
            'user': '👤',
            'llm': '🤖',
            'Humans': '👩‍💼',
            'operator': '👩‍💼'
        }.get(msg['role'], '❓')
        
        print(f"   {i}. [{role_icon} {msg['role']}] {msg['content'][:40]}...")
        
        if msg['role'] == 'user':
            has_user_message = True
        elif msg['role'] == 'llm':
            has_ai_message = True
        elif msg['role'] == 'Humans':
            has_human_message = True
    
    # 驗證結果
    print(f"\n步驟 5：驗證結果...")
    
    results = []
    if has_user_message:
        print("   ✅ 住戶訊息已記錄")
        results.append(True)
    else:
        print("   ❌ 缺少住戶訊息")
        results.append(False)
    
    if has_ai_message:
        print("   ✅ AI 回覆已記錄")
        results.append(True)
    else:
        print("   ❌ 缺少 AI 回覆")
        results.append(False)
    
    if has_human_message:
        print("   ✅ 客服回覆已記錄 (role='Humans')")
        results.append(True)
    else:
        print("   ❌ 缺少客服回覆")
        results.append(False)
    
    print("\n" + "=" * 70)
    
    if all(results):
        print("🎉 所有測試通過！")
        print("\n📝 前端測試步驟：")
        print("1. 開啟 http://localhost:5173")
        print("2. 點擊「維修諮詢」")
        print("3. 觀察彈窗是否在 3-5 秒內自動彈出")
        print("4. 檢查彈窗中是否顯示客服訊息：")
        print(f"   「{reply_data['reply']}」")
        print("5. 在彈窗輸入框中輸入訊息並點擊「送出」")
        print("6. 檢查訊息是否成功送出並顯示在彈窗中")
    else:
        print("⚠️ 部分測試失敗，請檢查問題")
    
    print("=" * 70)

if __name__ == "__main__":
    test_popup_messaging()
