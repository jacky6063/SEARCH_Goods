#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速測試 - CompanyResponseFormatter
只測試核心功能，快速驗證
"""

from company_response_formatter import get_company_response_formatter

def quick_test():
    """快速測試核心功能"""
    print("🧪 快速測試 CompanyResponseFormatter\n")
    
    formatter = get_company_response_formatter()
    passed = 0
    failed = 0
    
    # 測試 1: 基本格式化
    try:
        result = formatter.format_contact_info({
            'company_phone_local': '04-1234567'
        })
        assert '04-1234567' in result['text']
        print("✅ 測試 1: 基本格式化 - PASS")
        passed += 1
    except Exception as e:
        print(f"❌ 測試 1: 基本格式化 - FAIL ({e})")
        failed += 1
    
    # 測試 2: 空資料處理
    try:
        result = formatter.format_contact_info({})
        assert '無法取得' in result['text'] or '抱歉' in result['text']
        print("✅ 測試 2: 空資料處理 - PASS")
        passed += 1
    except Exception as e:
        print(f"❌ 測試 2: 空資料處理 - FAIL ({e})")
        failed += 1
    
    # 測試 3: Rich Content
    try:
        result = formatter.format_contact_info({
            'company_phone_local': '04-1234567',
            'address': '測試地址'
        })
        assert result['rich_content'] is not None
        assert len(result['rich_content']['items']) > 0
        print("✅ 測試 3: Rich Content - PASS")
        passed += 1
    except Exception as e:
        print(f"❌ 測試 3: Rich Content - FAIL ({e})")
        failed += 1
    
    # 測試 4: 單例模式
    try:
        formatter2 = get_company_response_formatter()
        assert formatter is formatter2
        print("✅ 測試 4: 單例模式 - PASS")
        passed += 1
    except Exception as e:
        print(f"❌ 測試 4: 單例模式 - FAIL ({e})")
        failed += 1
    
    # 測試 5: URL 編碼
    try:
        import urllib.parse
        encoded = urllib.parse.quote("台中市")
        assert '%E5' in encoded
        print("✅ 測試 5: URL 編碼 - PASS")
        passed += 1
    except Exception as e:
        print(f"❌ 測試 5: URL 編碼 - FAIL ({e})")
        failed += 1
    
    # 總結
    print(f"\n{'='*50}")
    print(f"總計: {passed + failed} 個測試")
    print(f"✅ 通過: {passed}")
    print(f"❌ 失敗: {failed}")
    print(f"{'='*50}")
    
    if failed == 0:
        print("\n🎉 所有測試通過！")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 個測試失敗")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(quick_test())
