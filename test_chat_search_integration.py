#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試聊天-搜索整合功能
測試會話追蹤和模式間同步
"""

import asyncio
import aiohttp
import json
import sys
import time
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8001"


async def test_chat_session_tracking():
    """測試聊天會話追蹤功能"""
    
    print("🧪 測試聊天會話追蹤功能")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # 1. 發送聊天消息並獲取會話 ID
        print("1️⃣ 發送聊天消息...")
        chat_data = {
            "message": "我想辦一個生日派對，預算 3000 元",
            "history": [],
            "topn": 8
        }
        
        async with session.post(f"{BASE_URL}/api/chat", json=chat_data) as resp:
            if resp.status != 200:
                print(f"❌ 聊天請求失敗: {resp.status}")
                return False
            
            chat_result = await resp.json()
            print(f"✅ 聊天回覆: {chat_result.get('reply', 'No reply')[:100]}...")
            
            session_id = chat_result.get('chat_session_id')
            if not session_id:
                print("❌ 未獲得會話 ID")
                return False
            
            print(f"📝 會話 ID: {session_id}")
        
        # 2. 測試會話結果檢索
        print("\n2️⃣ 檢索會話結果...")
        async with session.get(f"{BASE_URL}/api/chat-session/{session_id}") as resp:
            if resp.status != 200:
                print(f"❌ 會話檢索失敗: {resp.status}")
                return False
            
            session_result = await resp.json()
            if not session_result.get('ok'):
                print(f"❌ 會話結果無效: {session_result.get('error')}")
                return False
            
            stored_result = session_result.get('result', {})
            print(f"✅ 成功檢索會話結果")
            print(f"📊 回覆: {stored_result.get('reply', 'No reply')[:100]}...")
            
            # 檢查 action 字段
            action = stored_result.get('action')
            if action and action.get('type') == 'switch_to_search':
                items = action.get('items', [])
                print(f"🔄 包含切換搜索動作，商品數量: {len(items)}")
                
                # 3. 測試搜索模式同步
                if items:
                    print("\n3️⃣ 測試搜索模式同步...")
                    ids = [item.get('id') for item in items if item.get('id')]
                    
                    search_data = {
                        "query": "",
                        "ids": ids,
                        "topn": len(ids),
                        "page_size": len(ids)
                    }
                    
                    async with session.post(f"{BASE_URL}/api/search", json=search_data) as search_resp:
                        if search_resp.status != 200:
                            print(f"❌ 搜索同步失敗: {search_resp.status}")
                            return False
                        
                        search_result = await search_resp.json()
                        search_items = search_result.get('items', [])
                        print(f"✅ 成功同步到搜索模式，商品數量: {len(search_items)}")
                        
                        # 顯示同步的商品信息
                        for i, item in enumerate(search_items[:3]):
                            name = item.get('商品名稱', '未知商品')
                            price = item.get('價格', '未知價格')
                            print(f"   {i+1}. {name} - {price}")
            else:
                print("⚠️  無切換搜索動作")
        
        # 4. 測試會話過期處理
        print("\n4️⃣ 測試無效會話處理...")
        invalid_session = "invalid-session-id-12345"
        async with session.get(f"{BASE_URL}/api/chat-session/{invalid_session}") as resp:
            if resp.status == 200:
                result = await resp.json()
                if not result.get('ok'):
                    print("✅ 正確處理無效會話")
                else:
                    print("❌ 未正確處理無效會話")
            else:
                print(f"❌ 無效會話請求失敗: {resp.status}")
        
        print("\n✨ 聊天會話追蹤測試完成!")
        return True


async def test_fallback_category_grouping():
    """測試 fallback 分類商品功能"""
    
    print("\n🎉 測試生日派對分類商品功能")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # 測試生日派對場景
        chat_data = {
            "message": "我要辦小朋友生日派對，預算 2500 元",
            "history": [],
            "topn": 10
        }
        
        async with session.post(f"{BASE_URL}/api/chat", json=chat_data) as resp:
            if resp.status != 200:
                print(f"❌ 聊天請求失敗: {resp.status}")
                return False
            
            result = await resp.json()
            print(f"✅ 生日派對回覆: {result.get('reply', 'No reply')[:150]}...")
            
            # 檢查分組結構
            groups = result.get('groups')
            if groups and isinstance(groups, dict):
                print(f"🎯 檢測到 {len(groups)} 個商品分類:")
                
                total_items = 0
                for category, items in groups.items():
                    if isinstance(items, list):
                        total_items += len(items)
                        print(f"   📦 {category}: {len(items)} 個商品")
                        
                        # 顯示每個分類的前2個商品
                        for i, item in enumerate(items[:2]):
                            name = item.get('商品名稱', '未知商品')
                            price = item.get('價格', '未知價格')
                            print(f"      {i+1}. {name} - {price}")
                
                print(f"📊 總商品數量: {total_items}")
                return True
            else:
                print("⚠️  未檢測到分類結構")
                return False


async def main():
    """主測試函數"""
    
    print("🚀 SEARCH_Goods 聊天-搜索整合測試")
    print("=" * 60)
    print(f"📍 後端服務: {BASE_URL}")
    print()
    
    try:
        # 測試基本連通性
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/health") as resp:
                if resp.status != 200:
                    print(f"❌ 後端服務不可用: {resp.status}")
                    return
                print("✅ 後端服務連通性正常")
        
        # 執行測試
        success1 = await test_chat_session_tracking()
        success2 = await test_fallback_category_grouping()
        
        print("\n" + "=" * 60)
        if success1 and success2:
            print("🎊 所有測試通過!")
        else:
            print("⚠️  部分測試失敗")
            
    except Exception as e:
        print(f"💥 測試執行錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())