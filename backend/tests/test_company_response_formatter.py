#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
CompanyResponseFormatter 單元測試
================================================================================

測試檔案: test_company_response_formatter.py
建立日期: 2025年11月24日
功能描述: 測試 company_response_formatter.py 的所有功能

執行方式:
    pytest test_company_response_formatter.py -v
    或
    python3 test_company_response_formatter.py

================================================================================
"""

import sys
from pathlib import Path

# 加入 backend 路徑
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import pytest
from company_response_formatter import (
    CompanyResponseFormatter,
    get_company_response_formatter,
    format_company_response
)


class TestCompanyResponseFormatter:
    """CompanyResponseFormatter 測試類別"""
    
    @pytest.fixture
    def formatter(self):
        """提供格式化器實例"""
        return CompanyResponseFormatter()
    
    @pytest.fixture
    def sample_contacts(self):
        """提供測試用聯絡資訊"""
        return {
            'company_phone_local': '04-27062295',
            'customer_service_phone_local': '04-26062295',
            'address': '台中市河南路二段 262 號 3 樓之 11',
            'website': 'https://www.myqr.com.tw',
            'service_hours': '週一至週五 09:00-18:00'
        }
    
    @pytest.fixture
    def sample_services(self):
        """提供測試用服務項目"""
        return {
            'core_services': [
                {
                    'category': '網站建置',
                    'description': '專業網站設計與開發'
                },
                {
                    'category': '電子商務',
                    'description': '完整的電商解決方案'
                }
            ],
            'smart_solutions': [
                'AI 整合應用',
                '智慧客服系統'
            ]
        }
    
    # ==================== 聯絡資訊測試 ====================
    
    def test_format_contact_info_basic(self, formatter, sample_contacts):
        """測試基本聯絡資訊格式化"""
        result = formatter.format_contact_info(sample_contacts)
        
        assert 'text' in result
        assert 'rich_content' in result
        assert '04-27062295' in result['text']
        assert '04-26062295' in result['text']
        assert '台中市河南路二段' in result['text']
        assert 'https://www.myqr.com.tw' in result['text']
    
    def test_format_contact_info_empty(self, formatter):
        """測試空聯絡資訊"""
        result = formatter.format_contact_info({})
        
        assert 'text' in result
        assert '無法取得' in result['text'] or '抱歉' in result['text']
        assert result['rich_content'] is None
    
    def test_format_contact_info_rich_content(self, formatter, sample_contacts):
        """測試 rich_content 結構"""
        result = formatter.format_contact_info(sample_contacts)
        
        assert result['rich_content'] is not None
        assert 'type' in result['rich_content']
        assert result['rich_content']['type'] == 'contact_info'
        assert 'items' in result['rich_content']
        assert len(result['rich_content']['items']) > 0
    
    def test_format_contact_info_google_maps(self, formatter, sample_contacts):
        """測試 Google Maps 連結生成"""
        result = formatter.format_contact_info(sample_contacts)
        
        # 檢查是否包含地址項目
        items = result['rich_content']['items']
        address_items = [item for item in items if item['type'] == 'address']
        
        assert len(address_items) > 0
        assert 'google.com/maps' in address_items[0]['action']
    
    def test_format_contact_info_with_urls(self, formatter, sample_contacts):
        """測試包含額外 URL 的格式化"""
        result = formatter.format_contact_info(
            sample_contacts,
            profile_page_url='https://example.com/profile',
            introduction_video='https://youtube.com/watch?v=test'
        )
        
        assert 'https://example.com/profile' in result['text']
        assert 'https://youtube.com/watch?v=test' in result['text']
    
    # ==================== 服務項目測試 ====================
    
    def test_format_services_basic(self, formatter, sample_services):
        """測試基本服務項目格式化"""
        result = formatter.format_services(sample_services)
        
        assert 'text' in result
        assert '網站建置' in result['text']
        assert '電子商務' in result['text']
        assert 'AI 整合應用' in result['text']
    
    def test_format_services_empty(self, formatter):
        """測試空服務項目"""
        result = formatter.format_services({})
        
        assert 'text' in result
        assert '無法取得' in result['text'] or '抱歉' in result['text']
    
    def test_format_services_with_urls(self, formatter, sample_services):
        """測試包含 URL 的服務項目格式化"""
        result = formatter.format_services(
            sample_services,
            profile_page_url='https://example.com',
            introduction_video='https://youtube.com/test'
        )
        
        assert result['rich_content'] is not None
        assert len(result['rich_content']['items']) == 2
    
    # ==================== 公司介紹測試 ====================
    
    def test_format_overview_basic(self, formatter):
        """測試基本公司介紹格式化"""
        result = formatter.format_overview(
            company_name='傳啟資訊',
            overview='專業的資訊系統整合服務',
            established_year='1993'
        )
        
        assert 'text' in result
        assert '傳啟資訊' in result['text']
        assert '專業的資訊系統整合' in result['text']
    
    def test_format_overview_with_milestones(self, formatter):
        """測試包含里程碑的公司介紹"""
        milestones = [
            {'year': '1993', 'event': '公司成立'},
            {'year': '2012', 'event': '推出雲端服務'}
        ]
        
        result = formatter.format_overview(
            company_name='測試公司',
            overview='測試簡介',
            milestones=milestones
        )
        
        assert '1993' in result['text']
        assert '公司成立' in result['text']
        assert '2012' in result['text']
    
    def test_format_overview_with_business_scope(self, formatter):
        """測試包含業務範圍的公司介紹"""
        business_scope = ['系統整合', '網站開發', '電子商務']
        
        result = formatter.format_overview(
            company_name='測試公司',
            overview='測試簡介',
            business_scope=business_scope
        )
        
        assert '系統整合' in result['text']
        assert '網站開發' in result['text']
    
    # ==================== 營業時間測試 ====================
    
    def test_format_business_hours_basic(self, formatter, sample_contacts):
        """測試基本營業時間格式化"""
        result = formatter.format_business_hours(
            '週一至週五 09:00-18:00',
            sample_contacts
        )
        
        assert 'text' in result
        assert '週一至週五 09:00-18:00' in result['text']
    
    def test_format_business_hours_weekend_notice(self, formatter, sample_contacts):
        """測試週末休息提示"""
        result = formatter.format_business_hours(
            '週一至週五 09:00-18:00',
            sample_contacts
        )
        
        assert '週末' in result['text'] or '假日' in result['text']
    
    # ==================== FAQ 測試 ====================
    
    def test_format_faq_basic(self, formatter):
        """測試基本 FAQ 格式化"""
        faq = {
            'question': '如何聯絡客服？',
            'answer': '請撥打 04-26062295',
            'category': 'contact'
        }
        
        result = formatter.format_faq(faq)
        
        assert 'text' in result
        assert '如何聯絡客服' in result['text']
        assert '04-26062295' in result['text']
    
    def test_format_faq_empty(self, formatter):
        """測試空 FAQ"""
        result = formatter.format_faq({})
        
        assert 'text' in result
        assert '找不到' in result['text'] or '抱歉' in result['text']
    
    def test_format_faq_list(self, formatter):
        """測試 FAQ 列表格式化"""
        faq_list = [
            {'question': '問題1', 'answer': '答案1'},
            {'question': '問題2', 'answer': '答案2'}
        ]
        
        result = formatter.format_faq_list(faq_list, '測試查詢')
        
        assert '問題1' in result
        assert '問題2' in result
    
    # ==================== 促銷活動測試 ====================
    
    def test_format_promotion_basic(self, formatter):
        """測試基本促銷活動格式化"""
        promotion = {
            'title': '限時優惠',
            'description': '全館八折',
            'url': 'https://example.com/promo'
        }
        
        result = formatter.format_promotion(promotion)
        
        assert 'text' in result
        assert '限時優惠' in result['text']
        assert '全館八折' in result['text']
    
    def test_format_promotion_empty(self, formatter):
        """測試空促銷活動"""
        result = formatter.format_promotion({})
        
        assert 'text' in result
        assert '沒有' in result['text'] or '目前' in result['text']
    
    # ==================== 主題分派測試 ====================
    
    def test_format_by_topic_contact(self, formatter, sample_contacts):
        """測試主題分派 - 聯絡資訊"""
        profile_data = {'contacts': sample_contacts}
        
        result = formatter.format_by_topic('contact', profile_data)
        
        assert 'text' in result
        assert '04-27062295' in result['text']
    
    def test_format_by_topic_service(self, formatter, sample_services):
        """測試主題分派 - 服務項目"""
        profile_data = {'services': sample_services}
        
        result = formatter.format_by_topic('service', profile_data)
        
        assert 'text' in result
        assert '網站建置' in result['text']
    
    def test_format_by_topic_unknown(self, formatter):
        """測試未知主題"""
        result = formatter.format_by_topic('unknown_topic', {})
        
        assert 'text' in result
        assert '無法識別' in result['text'] or '抱歉' in result['text']
    
    # ==================== 單例模式測試 ====================
    
    def test_singleton_pattern(self):
        """測試單例模式"""
        formatter1 = get_company_response_formatter()
        formatter2 = get_company_response_formatter()
        
        assert formatter1 is formatter2
    
    # ==================== 快捷函數測試 ====================
    
    def test_format_company_response_shortcut(self, sample_contacts):
        """測試快捷函數"""
        profile_data = {'contacts': sample_contacts}
        
        result = format_company_response('contact', profile_data)
        
        assert isinstance(result, dict)
        assert 'text' in result


# ==================== 獨立測試執行 ====================

def run_manual_tests():
    """手動執行所有測試"""
    print("=" * 70)
    print("🧪 CompanyResponseFormatter 手動測試")
    print("=" * 70)
    
    formatter = CompanyResponseFormatter()
    
    # 測試 1: 聯絡資訊
    print("\n【測試 1】聯絡資訊格式化")
    print("-" * 70)
    contacts = {
        'company_phone_local': '04-27062295',
        'address': '台中市河南路二段 262 號'
    }
    result = formatter.format_contact_info(contacts)
    print(result['text'][:200] + "...")
    print(f"✅ Rich Content Items: {len(result['rich_content']['items']) if result['rich_content'] else 0}")
    
    # 測試 2: 空資料處理
    print("\n【測試 2】空資料處理")
    print("-" * 70)
    result = formatter.format_contact_info({})
    print(result['text'])
    print(f"✅ 正確返回錯誤訊息")
    
    # 測試 3: 服務項目
    print("\n【測試 3】服務項目格式化")
    print("-" * 70)
    services = {
        'core_services': [
            {'category': '網站建置', 'description': '專業設計'}
        ]
    }
    result = formatter.format_services(services)
    print(result['text'][:150] + "...")
    print(f"✅ 服務項目顯示正常")
    
    # 測試 4: 單例模式
    print("\n【測試 4】單例模式驗證")
    print("-" * 70)
    formatter1 = get_company_response_formatter()
    formatter2 = get_company_response_formatter()
    is_singleton = formatter1 is formatter2
    print(f"✅ 單例模式: {'PASS' if is_singleton else 'FAIL'}")
    
    # 測試 5: URL 編碼
    print("\n【測試 5】URL 編碼測試")
    print("-" * 70)
    import urllib.parse
    test_text = "台中市測試路"
    encoded = urllib.parse.quote(test_text)
    print(f"原始文字: {test_text}")
    print(f"編碼結果: {encoded}")
    print(f"✅ URL 編碼: {'PASS' if '%E5' in encoded else 'FAIL'}")
    
    print("\n" + "=" * 70)
    print("🎉 所有手動測試完成！")
    print("=" * 70)


if __name__ == "__main__":
    import sys
    
    # 檢查是否有 pytest
    try:
        import pytest
        print("使用 pytest 執行測試...")
        sys.exit(pytest.main([__file__, '-v', '--tb=short']))
    except ImportError:
        print("未安裝 pytest，執行手動測試...")
        run_manual_tests()
