#!/usr/bin/env python3
"""
測試 API 端點是否返回 rich_content
"""
import requests
import json

# 測試本地後端
print("="*60)
print("測試本地後端 (http://localhost:8000)")
print("="*60)

try:
    response = requests.post(
        "http://localhost:8000/api/chat",
        json={
            "message": "公司電話是多少？",
            "history": [],
            "topn": 8,
            "session_id": "test-session-123"
        },
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API 回應成功")
        print(f"   status_code: {response.status_code}")
        print(f"   reply 長度: {len(data.get('reply', ''))}")
        print(f"   包含 rich_content: {'rich_content' in data}")
        
        if 'rich_content' in data:
            rich = data['rich_content']
            print(f"\n📦 rich_content 結構:")
            print(f"   type: {rich.get('type')}")
            print(f"   items 數量: {len(rich.get('items', []))}")
            
            for i, item in enumerate(rich.get('items', [])[:3], 1):
                print(f"\n   項目 {i}:")
                print(f"      type: {item.get('type')}")
                print(f"      label: {item.get('label')}")
                print(f"      action: {item.get('action')[:60]}...")
        else:
            print(f"\n❌ 沒有 rich_content！")
            print(f"   回應內容: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
    else:
        print(f"❌ API 錯誤: {response.status_code}")
        print(f"   回應: {response.text[:200]}")
        
except requests.exceptions.ConnectionError:
    print("❌ 無法連接到本地後端")
    print("   請確認後端是否啟動: cd backend && uvicorn app:app --reload")
except Exception as e:
    print(f"❌ 錯誤: {e}")

print("\n" + "="*60)
print("💡 測試建議:")
print("="*60)
print("1. 如果本地測試失敗，請啟動後端:")
print("   cd backend && uvicorn app:app --reload")
print()
print("2. 如果生產環境測試，請用瀏覽器開發者工具:")
print("   - 開啟 Network 標籤")
print("   - 送出查詢")
print("   - 查看 /api/chat 回應")
print("   - 檢查是否有 rich_content 欄位")
