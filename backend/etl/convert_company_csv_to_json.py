#!/usr/bin/env python3
"""
公司介紹 CSV 轉 JSON Lines 工具

將 data/公司介紹.csv 轉換為結構化的 JSON Lines 格式
支援多語言和可擴展的資料結構

使用方式:
    python convert_company_csv_to_json.py
"""
import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class CompanyProfileConverter:
    """公司簡介資料轉換器"""
    
    def __init__(self, csv_path: Path, output_path: Path):
        self.csv_path = csv_path
        self.output_path = output_path
        self.company_data: Dict[str, Any] = {}
    
    def parse_contacts_from_description(self, description: str) -> Dict[str, str]:
        """從描述文字中提取聯絡資訊"""
        contacts = {}
        
        # 提取公司電話
        phone_match = re.search(r'公司電話[：:]\s*(\d{2})[－-]?(\d{8})', description)
        if phone_match:
            contacts['company_phone'] = f"+886-{phone_match.group(1)}-{phone_match.group(2)}"
            contacts['company_phone_local'] = f"{phone_match.group(1)}-{phone_match.group(2)}"
        
        # 提取客服電話
        cs_phone_match = re.search(r'客服電話[：:]\s*(\d{2})[－-]?(\d{8})', description)
        if cs_phone_match:
            contacts['customer_service_phone'] = f"+886-{cs_phone_match.group(1)}-{cs_phone_match.group(2)}"
            contacts['customer_service_phone_local'] = f"{cs_phone_match.group(1)}-{cs_phone_match.group(2)}"
        
        # 提取地址
        address_match = re.search(r'公司地址[：:]\s*([^\n]+?)(?=\s*公司|$)', description)
        if address_match:
            contacts['address'] = address_match.group(1).strip()
        
        # 提取官網
        website_match = re.search(r'公司官網[：:]\s*(https?://[^\s]+)', description)
        if website_match:
            contacts['website'] = website_match.group(1).strip()
        
        # 預設服務時間（如果未指定）
        if 'customer_service_phone' in contacts:
            contacts['service_hours'] = "週一至週五 09:00-18:00"
            contacts['service_hours_en'] = "Monday to Friday 09:00-18:00"
        
        return contacts
    
    def parse_keywords(self, keywords_str: str) -> List[str]:
        """解析關鍵字字串，分割成列表"""
        if not keywords_str:
            return []
        
        # 使用中文逗號或英文逗號分割
        keywords = re.split(r'[，,]', keywords_str)
        
        # 清理每個關鍵字
        return [kw.strip() for kw in keywords if kw.strip()]
    
    def extract_business_scope(self, keywords: List[str]) -> List[str]:
        """從關鍵字中提取核心業務範圍（前 12 項）"""
        # 排除一些非業務相關的關鍵字
        excluded = {'傳啟資訊', '公司介紹', '公司簡介'}
        
        business_scope = []
        for kw in keywords:
            if kw not in excluded and len(business_scope) < 12:
                business_scope.append(kw)
        
        return business_scope
    
    def parse_company_overview(self, description: str) -> str:
        """提取公司簡介摘要（前 200 字）"""
        # 移除多餘的空白和換行
        clean_desc = re.sub(r'\s+', ' ', description).strip()
        
        # 尋找公司簡介段落
        intro_match = re.search(r'公司簡介[：:\s]+(.+?)(?=服務項目|$)', clean_desc, re.DOTALL)
        if intro_match:
            intro = intro_match.group(1).strip()
            # 取前 200 字作為摘要
            if len(intro) > 200:
                return intro[:197] + "..."
            return intro
        
        # 如果找不到，返回前 200 字
        if len(clean_desc) > 200:
            return clean_desc[:197] + "..."
        return clean_desc
    
    def extract_services(self, description: str) -> Dict[str, Any]:
        """從描述中提取服務項目結構"""
        services = {
            "core_services": [],
            "smart_solutions": []
        }
        
        # 定義服務項目的模式 (傳啟資訊格式)
        service_patterns = [
            (r'一、整體形象網站建置[：:\s]+([^二]+)', "整體形象網站建置"),
            (r'二、電子商務系統[：:\s]+([^三]+)', "電子商務系統"),
            (r'三、輔助行銷系統[：:\s]+([^四]+)', "輔助行銷系統"),
            (r'四、系統設計與應用開發[：:\s]+([^五]+)', "系統設計與應用開發"),
            (r'五、響應式網站設計[：:\s\(RWD\)]+([^六]+)', "響應式網站設計 (RWD)"),
        ]
        
        for pattern, category in service_patterns:
            match = re.search(pattern, description)
            if match:
                desc_text = match.group(1).strip()
                services["core_services"].append({
                    "category": category,
                    "description": desc_text[:150] + "..." if len(desc_text) > 150 else desc_text
                })
        
        # 提取智能解決方案
        smart_match = re.search(r'六、驅動未來的智能解決方案[：:\s]+([^,]+)', description)
        if smart_match:
            smart_text = smart_match.group(1).strip()
            services["smart_solutions"] = [s.strip() for s in smart_text.split('，') if s.strip()]
        
        # 如果沒有找到傳啟資訊格式,嘗試提取品牌核心精神(磐鈺建設格式)
        if not services["core_services"]:
            core_values_match = re.search(r'【品牌核心精神[^】]*】\s*(.+?)(?=【|$)', description, re.DOTALL)
            if core_values_match:
                core_text = core_values_match.group(1).strip()
                # 分割每個項目 (・開頭)
                items = re.findall(r'・([^・\n]+)', core_text)
                for item in items[:4]:  # 最多取4項
                    parts = item.split('：', 1)
                    if len(parts) == 2:
                        services["core_services"].append({
                            "category": parts[0].strip(),
                            "description": parts[1].strip()
                        })
        
        return services
    
    def convert_row_to_profile(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """轉換單一 CSV 行為公司簡介資料"""
        category = row.get('資料類別', '').strip()
        
        if category == "公司基本資料":
            # 解析關鍵字
            keywords = self.parse_keywords(row.get('關鍵字', ''))
            
            return {
                "company_id": "chuanchi",
                "locale": "zh-TW",
                "company_name": "傳啟資訊股份有限公司",
                "company_name_en": "ChuanChi Information Co., Ltd.",
                "established_year": "1993",
                "profile_page_url": row.get('頁面連結', '').strip(),
                "overview": self.parse_company_overview(row.get('描述', '')),
                "business_scope": self.extract_business_scope(keywords),
                "services": self.extract_services(row.get('描述', '')),
                "media": {
                    "company_logo": row.get('代表圖片', '').strip(),
                    "introduction_video": row.get('Youtube 影片介紹', '').strip()
                },
                "milestones": [
                    {
                        "year": "1993",
                        "event": "公司成立，從形象網站、物流管理系統與票券系統起家"
                    },
                    {
                        "year": "2012",
                        "event": "推出 Just MyQRcode 雲端服務平台，結合條碼會員與行動應用"
                    }
                ],
                "keywords": keywords,
                "metadata": {
                    "created_at": datetime.now().strftime("%Y-%m-%d"),
                    "updated_at": datetime.now().strftime("%Y-%m-%d"),
                    "version": "1.0",
                    "data_source": "公司介紹.csv"
                }
            }
        
        elif category == "客服資訊":
            contacts = self.parse_contacts_from_description(row.get('描述', ''))
            
            return {
                "company_id": "chuanchi",
                "locale": "zh-TW",
                "contacts": contacts,
                "media": {
                    "company_logo": row.get('代表圖片', '').strip(),
                    "introduction_video": row.get('Youtube 影片介紹', '').strip()
                },
                "profile_page_url": row.get('頁面連結', '').strip()
            }
        
        elif category == "宣傳資訊":
            keywords = self.parse_keywords(row.get('關鍵字', ''))
            
            return {
                "company_id": "chuanchi",
                "locale": "zh-TW",
                "promotions": [{
                    "title": row.get('標題', '').strip(),
                    "description": row.get('描述', '').strip(),
                    "keywords": keywords,
                    "url": row.get('頁面連結', '').strip(),
                    "video": row.get('Youtube 影片介紹', '').strip(),
                    "image": row.get('代表圖片', '').strip()
                }]
            }
        
        return None
    
    def merge_profiles(self, profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合併多個部分資料為完整的公司簡介"""
        merged = {
            "company_id": "chuanchi",
            "locale": "zh-TW"
        }
        
        for profile in profiles:
            if not profile:
                continue
            
            for key, value in profile.items():
                if key in ['company_id', 'locale']:
                    continue
                
                if key not in merged:
                    merged[key] = value
                elif isinstance(value, dict):
                    # 合併字典
                    if key not in merged:
                        merged[key] = {}
                    merged[key].update(value)
                elif isinstance(value, list):
                    # 合併列表
                    if key not in merged:
                        merged[key] = []
                    merged[key].extend(value)
                else:
                    # 覆蓋單一值
                    merged[key] = value
        
        return merged
    
    def add_faq(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """新增常見問題"""
        contacts = profile.get('contacts', {})
        
        profile['faq'] = [
            {
                "question": "公司的主要服務項目是什麼？",
                "answer": "傳啟資訊提供資訊系統整合、數位轉型顧問、電子商務系統、網站建置、智慧客服系統等完整解決方案。",
                "category": "service",
                "keywords": ["服務項目", "主要業務", "做什麼", "提供什麼"]
            },
            {
                "question": "客服電話是幾號？",
                "answer": f"客服電話是 {contacts.get('customer_service_phone_local', '04-26062295')}，服務時間為週一至週五 09:00-18:00。",
                "category": "contact",
                "keywords": ["客服電話", "聯絡電話", "電話", "怎麼聯絡"]
            },
            {
                "question": "公司地址在哪裡？",
                "answer": f"公司位於{contacts.get('address', '台中市河南路二段 262 號 3 樓之 11')}。",
                "category": "contact",
                "keywords": ["地址", "位置", "在哪", "怎麼去"]
            },
            {
                "question": "公司什麼時候成立的？",
                "answer": "傳啟資訊成立於 1993 年 3 月，已有超過 30 年的資訊系統整合經驗。",
                "category": "about",
                "keywords": ["成立", "歷史", "多久", "什麼時候"]
            },
            {
                "question": "公司官網在哪裡？",
                "answer": f"公司官網：{contacts.get('website', 'https://www.myqr.com.tw')}",
                "category": "contact",
                "keywords": ["官網", "網站", "網址", "線上"]
            }
        ]
        
        return profile
    
    def convert(self) -> None:
        """執行轉換流程"""
        print(f"[INFO] 開始轉換 CSV 到 JSON Lines...")
        print(f"[INFO] 來源檔案: {self.csv_path}")
        print(f"[INFO] 目標檔案: {self.output_path}")
        
        if not self.csv_path.exists():
            raise FileNotFoundError(f"找不到來源檔案: {self.csv_path}")
        
        # 讀取 CSV 並轉換（處理 BOM）
        profiles = []
        with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                profile = self.convert_row_to_profile(row)
                if profile:
                    profiles.append(profile)
                    print(f"[INFO] 已處理: {row.get('資料類別', 'Unknown')}")
        
        # 合併所有資料
        print(f"[INFO] 合併 {len(profiles)} 個部分資料...")
        merged_profile = self.merge_profiles(profiles)
        
        # 新增 FAQ
        print(f"[INFO] 新增常見問題...")
        merged_profile = self.add_faq(merged_profile)
        
        # 確保輸出目錄存在
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 寫入 JSON Lines（單一完整記錄）
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_profile, f, ensure_ascii=False, indent=2)
        
        print(f"[SUCCESS] ✅ 轉換完成！")
        print(f"[INFO] 輸出檔案: {self.output_path}")
        print(f"[INFO] 檔案大小: {self.output_path.stat().st_size / 1024:.2f} KB")
        
        # 顯示摘要資訊
        print(f"\n📊 轉換摘要:")
        print(f"  • 公司名稱: {merged_profile.get('company_name')}")
        print(f"  • 關鍵字數量: {len(merged_profile.get('keywords', []))}")
        print(f"  • 核心服務: {len(merged_profile.get('services', {}).get('core_services', []))}")
        print(f"  • 常見問題: {len(merged_profile.get('faq', []))}")
        print(f"  • 聯絡資訊: {len(merged_profile.get('contacts', {}))}")


def main():
    """主程序"""
    # 設定路徑
    current_dir = Path(__file__).parent.parent.parent  # 回到專案根目錄
    csv_path = current_dir / "data" / "公司介紹.csv"
    output_path = current_dir / "data" / "company_profiles" / "company_profile_chuanchi.jsonl"
    
    # 執行轉換
    converter = CompanyProfileConverter(csv_path, output_path)
    
    try:
        converter.convert()
        
        # 驗證輸出
        print(f"\n🔍 驗證輸出檔案...")
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"✅ JSON 格式正確")
        print(f"✅ 公司 ID: {data.get('company_id')}")
        print(f"✅ 語言: {data.get('locale')}")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ 轉換失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
