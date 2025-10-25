#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡單的手動測試聊天-搜索整合功能
"""

import requests
import json

BASE_URL = "http://localhost:8001"

def test_manual():
    print("🧪 手動測試聊天-搜索整合功能")
    print("=" * 50)
    
    # 1. 測試健康檢查
    try:
        resp = requests.get(f"{BASE_URL}/health")
        if resp.status_code == 200:
            print("✅ 後端服務健康檢查通過")
        else:
            print(f"❌ 健康檢查失敗: {resp.status_code}")
            return
    except Exception as e:
        print(f"❌ 無法連接到後端服務: {e}")
        return
    
    # 2. 發送聊天消息
    print("\n📤 發送聊天消息...")
    chat_data = {
        "message": "我想辦一個生日派對，預算 2500 元",
        "history": [],
        "topn": 8
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/api/chat", json=chat_data)
        if resp.status_code == 200:
            result = resp.json()
            print(f"✅ 聊天回覆收到: {result.get('reply', 'No reply')[:100]}...")
            
            session_id = result.get('chat_session_id')
            if session_id:
                print(f"📝 會話 ID: {session_id}")
                
                # 3. 檢索會話結果
                print(f"\n🔍 檢索會話結果...")
                session_resp = requests.get(f"{BASE_URL}/api/chat-session/{session_id}")
                if session_resp.status_code == 200:
                    session_result = session_resp.json()
                    if session_result.get('ok'):
                        stored_result = session_result.get('result', {})
                        print("✅ 成功檢索會話結果")
                        print(f"📊 儲存的回覆: {stored_result.get('reply', 'No reply')[:100]}...")
                        
                        # 檢查 action 字段
                        action = stored_result.get('action')
                        if action and action.get('type') == 'switch_to_search':
                            items = action.get('items', [])
                            print(f"🔄 檢測到切換搜索動作，商品數量: {len(items)}")
                            
                            if items:
                                # 4. 測試搜索同步
                                print(f"\n🔍 測試搜索同步...")
                                ids = [item.get('id') for item in items if item.get('id')]
                                
                                search_data = {
                                    "query": "",
                                    "ids": ids[:5],  # 限制數量
                                    "topn": 5,
                                    "page_size": 5
                                }
                                
                                search_resp = requests.post(f"{BASE_URL}/api/search", json=search_data)
                                if search_resp.status_code == 200:
                                    search_result = search_resp.json()
                                    search_items = search_result.get('items', [])
                                    print(f"✅ 搜索同步成功，商品數量: {len(search_items)}")
                                    
                                    # 顯示前3個商品
                                    for i, item in enumerate(search_items[:3]):
                                        name = item.get('商品名稱', '未知商品')
                                        price = item.get('價格', '未知價格')
                                        print(f"   {i+1}. {name} - {price}")
                                else:
                                    print(f"❌ 搜索同步失敗: {search_resp.status_code}")
                        else:
                            print("⚠️  未檢測到切換搜索動作")
                    else:
                        print(f"❌ 會話結果無效: {session_result.get('error')}")
                else:
                    print(f"❌ 會話檢索失敗: {session_resp.status_code}")
            else:
                print("⚠️  未獲得會話 ID")
        else:
            print(f"❌ 聊天請求失敗: {resp.status_code}")
            print(f"響應內容: {resp.text}")
    except Exception as e:
        print(f"❌ 聊天測試錯誤: {e}")

if __name__ == "__main__":
    test_manual()