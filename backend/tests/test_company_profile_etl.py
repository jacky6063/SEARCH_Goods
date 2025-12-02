#!/usr/bin/env python3
"""
公司簡介 ETL 工具測試

測試 CSV 轉 JSON Lines 的正確性
"""
import json
import pytest
from pathlib import Path
import sys

# 添加 backend 到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.convert_company_csv_to_json import CompanyProfileConverter


class TestCompanyProfileConverter:
    """測試公司簡介轉換器"""
    
    @pytest.fixture
    def output_file(self):
        """測試用的輸出檔案"""
        return Path(__file__).parent.parent.parent / "data" / "company_profiles" / "company_profile_chuanchi.jsonl"
    
    def test_output_file_exists(self, output_file):
        """測試 1: 確認輸出檔案存在"""
        assert output_file.exists(), f"輸出檔案不存在: {output_file}"
        print(f"✅ 測試 1 通過: 輸出檔案存在")
    
    def test_json_format_valid(self, output_file):
        """測試 2: 驗證 JSON 格式正確"""
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert isinstance(data, dict), "資料應該是字典格式"
        print(f"✅ 測試 2 通過: JSON 格式正確")
    
    def test_required_fields(self, output_file):
        """測試 3: 驗證必要欄位存在"""
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        required_fields = [
            'company_id',
            'locale',
            'company_name',
            'overview',
            'business_scope',
            'contacts',
            'keywords',
            'faq'
        ]
        
        for field in required_fields:
            assert field in data, f"缺少必要欄位: {field}"
        
        print(f"✅ 測試 3 通過: 所有必要欄位存在")
    
    def test_company_id(self, output_file):
        """測試 4: 驗證公司 ID"""
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['company_id'] == 'chuanchi', "公司 ID 應為 'chuanchi'"
        assert data['locale'] == 'zh-TW', "語言應為 'zh-TW'"
        
        print(f"✅ 測試 4 通過: 公司 ID 和語言正確")
    
    def test_company_name(self, output_file):
        """測試 5: 驗證公司名稱"""
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['company_name'] == '傳啟資訊股份有限公司'
        assert 'company_name_en' in data
        
        print(f"✅ 測試 5 通過: 公司名稱正確")
    
    def test_contacts_structure(self, output_file):
        """測試 6: 驗證聯絡資訊結構"""
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        contacts = data.get('contacts', {})
        
        # 驗證必要的聯絡資訊
        assert 'customer_service_phone' in contacts, "缺少客服電話"
        assert 'company_phone' in contacts, "缺少公司電話"
        assert 'address' in contacts, "缺少地址"
        assert 'website' in contacts, "缺少官網"
        
        # 驗證電話格式
        assert contacts['customer_service_phone'].startswith('+886'), "客服電話應有國際區號"
        assert contacts['customer_service_phone_local'] == '04-26062295', "本地客服電話格式錯誤"
        
        print(f"✅ 測試 6 通過: 聯絡資訊結構正確")
        print(f"   客服電話: {contacts['customer_service_phone_local']}")
        print(f"   公司地址: {contacts['address']}")
    
    def test_business_scope(self, output_file):
        """測試 7: 驗證業務範圍"""
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        business_scope = data.get('business_scope', [])
        
        assert isinstance(business_scope, list), "業務範圍應為列表"
        assert len(business_scope) > 0, "業務範圍不能為空"
        assert len(business_scope) <= 15, "業務範圍過多"
        
        # 驗證核心業務項目存在
        assert '資訊系統整合' in business_scope
        assert '電子商務系統' in business_scope
        
        print(f"✅ 測試 7 通過: 業務範圍正確 ({len(business_scope)} 項)")
    
    def test_services_structure(self, output_file):
        """測試 8: 驗證服務項目結構"""
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        services = data.get('services', {})
        
        assert 'core_services' in services, "缺少核心服務"
        assert 'smart_solutions' in services, "缺少智能解決方案"
        
        core_services = services['core_services']
        assert isinstance(core_services, list), "核心服務應為列表"
        assert len(core_services) == 5, f"核心服務應有 5 項，實際 {len(core_services)} 項"
        
        # 驗證核心服務結構
        for service in core_services:
            assert 'category' in service, "服務缺少類別"
            assert 'description' in service, "服務缺少描述"
        
        print(f"✅ 測試 8 通過: 服務項目結構正確")
    
    def test_keywords(self, output_file):
        """測試 9: 驗證關鍵字"""
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        keywords = data.get('keywords', [])
        
        assert isinstance(keywords, list), "關鍵字應為列表"
        assert len(keywords) >= 10, f"關鍵字太少: {len(keywords)}"
        
        # 驗證關鍵字不為空
        for kw in keywords:
            assert kw.strip(), "關鍵字不應為空"
        
        print(f"✅ 測試 9 通過: 關鍵字正確 ({len(keywords)} 個)")
    
    def test_faq_structure(self, output_file):
        """測試 10: 驗證 FAQ 結構"""
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        faq = data.get('faq', [])
        
        assert isinstance(faq, list), "FAQ 應為列表"
        assert len(faq) >= 5, f"FAQ 至少應有 5 個，實際 {len(faq)} 個"
        
        # 驗證 FAQ 結構
        for item in faq:
            assert 'question' in item, "FAQ 缺少問題"
            assert 'answer' in item, "FAQ 缺少答案"
            assert 'category' in item, "FAQ 缺少分類"
            assert 'keywords' in item, "FAQ 缺少關鍵字"
        
        # 驗證常見問題存在
        questions = [item['question'] for item in faq]
        assert any('客服電話' in q for q in questions), "缺少客服電話問題"
        assert any('地址' in q for q in questions), "缺少地址問題"
        
        print(f"✅ 測試 10 通過: FAQ 結構正確 ({len(faq)} 個問題)")
    
    def test_media_links(self, output_file):
        """測試 11: 驗證媒體連結"""
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        media = data.get('media', {})
        
        assert 'company_logo' in media, "缺少公司 Logo"
        assert 'introduction_video' in media, "缺少介紹影片"
        
        # 驗證 URL 格式
        assert media['company_logo'].startswith('http'), "Logo URL 格式錯誤"
        assert media['introduction_video'].startswith('http'), "影片 URL 格式錯誤"
        
        print(f"✅ 測試 11 通過: 媒體連結正確")
    
    def test_metadata(self, output_file):
        """測試 12: 驗證元資料"""
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metadata = data.get('metadata', {})
        
        assert 'created_at' in metadata, "缺少建立日期"
        assert 'version' in metadata, "缺少版本號"
        assert 'data_source' in metadata, "缺少資料來源"
        
        print(f"✅ 測試 12 通過: 元資料正確")
        print(f"   版本: {metadata['version']}")
        print(f"   來源: {metadata['data_source']}")


def test_converter_parse_contacts():
    """測試 13: 測試聯絡資訊解析函數"""
    converter = CompanyProfileConverter(Path("dummy"), Path("dummy"))
    
    test_description = """
    公司名稱：傳啟資訊股份有限公司
    公司電話： 04-27062295
    客服電話： 04-26062295
    公司地址：台中市河南路二段 262 號 3 樓之 11
    公司官網：https://www.myqr.com.tw
    """
    
    contacts = converter.parse_contacts_from_description(test_description)
    
    assert contacts['company_phone'] == '+886-04-27062295'
    assert contacts['customer_service_phone'] == '+886-04-26062295'
    assert '台中市' in contacts['address']
    assert contacts['website'] == 'https://www.myqr.com.tw'
    
    print(f"✅ 測試 13 通過: 聯絡資訊解析正確")


def test_converter_parse_keywords():
    """測試 14: 測試關鍵字解析函數"""
    converter = CompanyProfileConverter(Path("dummy"), Path("dummy"))
    
    test_keywords = "傳啟資訊，資訊系統整合，數位轉型顧問，智慧化企業方案"
    keywords = converter.parse_keywords(test_keywords)
    
    assert len(keywords) == 4
    assert '傳啟資訊' in keywords
    assert '資訊系統整合' in keywords
    
    print(f"✅ 測試 14 通過: 關鍵字解析正確")


def main():
    """執行所有測試"""
    print("\n" + "="*60)
    print("🧪 公司簡介 ETL 工具測試")
    print("="*60 + "\n")
    
    # 使用 pytest 執行測試
    import pytest
    exit_code = pytest.main([__file__, '-v', '--tb=short'])
    
    if exit_code == 0:
        print("\n" + "="*60)
        print("✅ 所有測試通過！")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("❌ 部分測試失敗")
        print("="*60 + "\n")
    
    return exit_code


if __name__ == "__main__":
    exit(main())
