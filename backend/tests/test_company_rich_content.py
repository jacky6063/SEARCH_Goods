#!/usr/bin/env python3
"""
測試公司簡介豐富內容格式化

驗證連結、地圖等可點擊元素的正確生成
"""
import sys
from pathlib import Path

# 添加 backend 到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from company_profile_service import CompanyProfileService
from company_response_formatter import CompanyResponseFormatter


def test_contact_rich_content():
    """測試聯絡資訊的豐富內容格式化"""
    print("\n" + "="*60)
    print("測試 1: 聯絡資訊豐富內容")
    print("="*60)
    
    # 載入公司資料
    json_path = Path(__file__).parent.parent.parent / "data" / "company_profiles" / "company_profile_chuanchi.jsonl"
    
    if not json_path.exists():
        print(f"❌ 檔案不存在: {json_path}")
        return False
    
    service = CompanyProfileService()
    if not service.load_from_file(json_path):
        print("❌ 載入失敗")
        return False
    
    profile = service.get_profile()
    contacts = profile.get('contacts', {})
    media = profile.get('media', {}) or {}
    profile_url = profile.get("profile_page_url") or contacts.get("website")
    intro_video = media.get("introduction_video") or media.get("introductionVideo")
    
    # 格式化聯絡資訊
    formatter = CompanyResponseFormatter()
    result = formatter.format_contact_info(
        contacts,
        profile_page_url=profile_url,
        introduction_video=intro_video
    )
    
    # 驗證結構
    assert isinstance(result, dict), "回應應為字典格式"
    assert "text" in result, "應包含 text 欄位"
    assert "rich_content" in result, "應包含 rich_content 欄位"
    
    text = result["text"]
    rich_content = result["rich_content"]
    
    print(f"\n📝 文字回應 ({len(text)} 字元):")
    print(text)
    
    if rich_content:
        print(f"\n🎨 豐富內容:")
        print(f"  類型: {rich_content.get('type')}")
        print(f"  項目數量: {len(rich_content.get('items', []))}")
        
        for item in rich_content.get('items', []):
            print(f"\n  - {item['icon']} {item['label']}")
            print(f"    值: {item['value']}")
            print(f"    動作: {item['action']}")
            if 'action_label' in item:
                print(f"    按鈕文字: {item['action_label']}")
    
    # 驗證必要的項目
    items = rich_content.get('items', [])
    
    # 檢查電話
    phone_items = [i for i in items if i['type'] == 'phone']
    assert len(phone_items) >= 1, "應至少有一個電話項目"
    print(f"\n✅ 電話項目: {len(phone_items)} 個")
    
    # 檢查地址（Google Maps）
    address_items = [i for i in items if i['type'] == 'address']
    assert len(address_items) >= 1, "應至少有一個地址項目"
    assert 'google.com/maps' in address_items[0]['action'], "地址應包含 Google Maps 連結"
    print(f"✅ 地址項目: {len(address_items)} 個")
    print(f"   Google Maps URL: {address_items[0]['action'][:80]}...")
    
    # 檢查官網
    url_items = [i for i in items if i['type'] == 'url']
    assert len(url_items) >= 2, "應至少有兩個網址項目（官方網站 + 官方介紹頁）"
    print(f"✅ 網址項目: {len(url_items)} 個")
    
    # 檢查影片
    video_items = [i for i in items if i['type'] == 'video']
    assert len(video_items) >= 1, "應至少有一個影片項目"
    print(f"✅ 影片項目: {len(video_items)} 個")
    
    print(f"\n✅ 測試 1 通過")
    return True


def test_promotion_rich_content():
    """測試促銷活動的豐富內容格式化"""
    print("\n" + "="*60)
    print("測試 2: 促銷活動豐富內容")
    print("="*60)
    
    # 載入公司資料
    json_path = Path(__file__).parent.parent.parent / "data" / "company_profiles" / "company_profile_chuanchi.jsonl"
    
    service = CompanyProfileService()
    service.load_from_file(json_path)
    
    profile = service.get_profile()
    promotions = profile.get('promotions', [])
    
    if not promotions:
        print("⚠️ 沒有促銷活動資料")
        return True
    
    # 格式化促銷活動
    formatter = CompanyResponseFormatter()
    result = formatter.format_promotion(promotions[0])
    
    # 驗證結構
    assert isinstance(result, dict), "回應應為字典格式"
    assert "text" in result, "應包含 text 欄位"
    assert "rich_content" in result, "應包含 rich_content 欄位"
    
    text = result["text"]
    rich_content = result["rich_content"]
    
    print(f"\n📝 文字回應 ({len(text)} 字元):")
    print(text)
    
    if rich_content:
        print(f"\n🎨 豐富內容:")
        print(f"  類型: {rich_content.get('type')}")
        print(f"  標題: {rich_content.get('title')}")
        print(f"  項目數量: {len(rich_content.get('items', []))}")
        
        for item in rich_content.get('items', []):
            print(f"\n  - {item['icon']} {item['label']}")
            print(f"    動作: {item['action']}")
            print(f"    按鈕文字: {item['action_label']}")
    
    # 驗證連結
    items = rich_content.get('items', [])
    
    # 檢查優惠連結
    url_items = [i for i in items if i['type'] == 'url']
    if url_items:
        assert url_items[0]['action'].startswith('http'), "URL 應以 http 開頭"
        print(f"\n✅ 優惠連結: {url_items[0]['action']}")
    
    # 檢查影片連結
    video_items = [i for i in items if i['type'] == 'video']
    if video_items:
        video_url = video_items[0]['action'].lower()
        assert 'youtube' in video_url or 'youtu.be' in video_url, "影片連結應包含 youtube 或 youtu.be"
        print(f"✅ 影片連結: {video_items[0]['action']}")
    
    print(f"\n✅ 測試 2 通過")
    return True


def test_format_by_topic():
    """測試主題格式化返回結構化資料"""
    print("\n" + "="*60)
    print("測試 3: 主題格式化結構")
    print("="*60)
    
    # 載入公司資料
    json_path = Path(__file__).parent.parent.parent / "data" / "company_profiles" / "company_profile_chuanchi.jsonl"
    
    service = CompanyProfileService()
    service.load_from_file(json_path)
    
    profile = service.get_profile()
    formatter = CompanyResponseFormatter()
    
    # 測試各種主題（包含所有公司介紹相關主題）
    topics = ["contact", "promotion", "overview", "service", "hours"]
    
    for topic in topics:
        print(f"\n--- 測試主題: {topic} ---")
        
        result = formatter.format_by_topic(topic, profile)
        
        # 驗證返回結構
        assert isinstance(result, dict), f"{topic} 應返回字典"
        assert "text" in result, f"{topic} 應包含 text"
        assert "rich_content" in result, f"{topic} 應包含 rich_content"
        
        print(f"✅ {topic}: 結構正確")
        print(f"   文字長度: {len(result['text'])} 字元")
        print(f"   有豐富內容: {result['rich_content'] is not None}")
        
        # 檢查是否包含頁面連結和影片（除了 contact 和 promotion 有特殊內容）
        if topic in ["overview", "service", "hours"]:
            assert result["rich_content"], f"{topic} 應包含 rich_content"
            items = result["rich_content"].get("items", [])
            url_items = [i for i in items if i.get("type") == "url"]
            video_items = [i for i in items if i.get("type") == "video"]
            assert url_items, f"{topic} 應提供官方介紹連結"
            assert video_items, f"{topic} 應提供影片連結"
            print(f"   ✅ URL 項目: {len(url_items)} 個")
            print(f"   ✅ 影片項目: {len(video_items)} 個")
    
    # 測試 FAQ（單一問題）
    print(f"\n--- 測試主題: faq (單一問題) ---")
    faq = profile['faq'][0]
    media = profile.get('media', {}) or {}
    profile_url = profile.get("profile_page_url")
    intro_video = media.get("introduction_video")
    
    result = formatter.format_faq(
        faq,
        profile_page_url=profile_url,
        introduction_video=intro_video
    )
    
    assert isinstance(result, dict), "FAQ 應返回字典"
    assert "text" in result, "FAQ 應包含 text"
    assert "rich_content" in result, "FAQ 應包含 rich_content"
    assert result["rich_content"], "FAQ 應包含 rich_content"
    
    items = result["rich_content"].get("items", [])
    url_items = [i for i in items if i.get("type") == "url"]
    video_items = [i for i in items if i.get("type") == "video"]
    assert url_items, "FAQ 應提供官方介紹連結"
    assert video_items, "FAQ 應提供影片連結"
    
    print(f"✅ faq: 結構正確")
    print(f"   文字長度: {len(result['text'])} 字元")
    print(f"   有豐富內容: True")
    print(f"   ✅ URL 項目: {len(url_items)} 個")
    print(f"   ✅ 影片項目: {len(video_items)} 個")
    
    print(f"\n✅ 測試 3 通過")
    return True


def test_api_response_structure():
    """測試 API 回應結構（模擬）"""
    print("\n" + "="*60)
    print("測試 4: API 回應結構")
    print("="*60)
    
    # 載入公司資料
    json_path = Path(__file__).parent.parent.parent / "data" / "company_profiles" / "company_profile_chuanchi.jsonl"
    
    service = CompanyProfileService()
    service.load_from_file(json_path)
    
    profile = service.get_profile()
    formatter = CompanyResponseFormatter()
    
    # 模擬處理聯絡資訊查詢
    topic = "contact"
    formatted_response = formatter.format_by_topic(topic, profile)
    
    # 建立模擬的 API 回應
    api_response = {
        "reply": formatted_response.get("text"),
        "ok": True,
        "suggestion_ids": [],
        "chat_session_id": "test-session",
        "meta": {
            "intent": "company_info",
            "topic": topic,
            "company_id": profile.get("company_id"),
        },
        "action": None,
        "items": [],
    }
    
    # 如果有豐富內容，加入回應
    if formatted_response.get("rich_content"):
        api_response["rich_content"] = formatted_response["rich_content"]
    
    print("\n📦 API 回應結構:")
    print(f"  reply: {len(api_response['reply'])} 字元")
    print(f"  ok: {api_response['ok']}")
    print(f"  has_rich_content: {'rich_content' in api_response}")
    
    if "rich_content" in api_response:
        rich = api_response["rich_content"]
        print(f"\n  rich_content:")
        print(f"    type: {rich.get('type')}")
        print(f"    items: {len(rich.get('items', []))} 個")
        
        # 顯示第一個項目作為範例
        if rich.get('items'):
            item = rich['items'][0]
            print(f"\n  範例項目:")
            print(f"    type: {item['type']}")
            print(f"    label: {item['label']}")
            print(f"    value: {item['value']}")
            print(f"    action: {item['action']}")
    
    # 驗證必要欄位
    assert "reply" in api_response
    assert "ok" in api_response
    assert "meta" in api_response
    assert "rich_content" in api_response
    
    print(f"\n✅ 測試 4 通過")
    return True


def main():
    """執行所有測試"""
    print("\n" + "="*60)
    print("🧪 公司簡介豐富內容測試")
    print("="*60)
    
    tests = [
        ("聯絡資訊豐富內容", test_contact_rich_content),
        ("促銷活動豐富內容", test_promotion_rich_content),
        ("主題格式化結構", test_format_by_topic),
        ("API 回應結構", test_api_response_structure),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ 測試失敗: {name}")
            print(f"   錯誤: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print("測試總結")
    print("="*60)
    print(f"✅ 通過: {passed}/{len(tests)}")
    print(f"❌ 失敗: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 所有測試通過！")
        return 0
    else:
        print(f"\n⚠️ {failed} 個測試失敗")
        return 1


if __name__ == "__main__":
    exit(main())
