# -*- coding: utf-8 -*-
"""
================================================================================
公司簡介查詢服務 - CompanyProfileService
================================================================================

檔案名稱: company_profile_service.py
建立日期: 2025年11月9日
功能描述:
    提供公司簡介資料的載入、查詢、搜尋功能
    支援多主題查詢、FAQ 搜尋、關鍵字匹配

核心功能:
    - 載入 JSON Lines 格式的公司資料
    - 依主題 (topic) 查詢特定資訊
    - FAQ 關鍵字搜尋
    - 聯絡資訊快速查詢
    - 服務項目查詢

設計原則:
    - 單例模式 (全域共用)
    - 啟動時載入 + 熱更新支援
    - 快取機制避免重複讀取

================================================================================
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CompanyProfileService:
    """
    公司簡介查詢服務
    
    功能:
        - 載入公司簡介 JSON Lines 資料
        - 支援多主題查詢 (聯絡資訊、服務項目、公司介紹等)
        - FAQ 關鍵字搜尋
        - 資料快取與熱更新
    
    使用範例:
        ```python
        service = CompanyProfileService()
        service.load_from_file(Path("data/company_profiles/company_profile_chuanchi.jsonl"))
        
        # 查詢聯絡資訊
        contacts = service.get_contact_info()
        
        # 查詢服務項目
        services = service.get_services()
        
        # 搜尋 FAQ
        faq_results = service.search_faq("電話")
        ```
    """
    
    def __init__(self):
        """初始化服務"""
        self.profile_data: Optional[Dict[str, Any]] = None
        self.loaded_at: Optional[datetime] = None
        self.file_path: Optional[Path] = None
        
        # 關鍵字索引 (用於快速匹配)
        self._keyword_index: Dict[str, List[str]] = {}
        self._faq_index: Dict[str, Dict] = {}
    
    def load_from_file(self, json_path: Path) -> bool:
        """
        從 JSON Lines 檔案載入公司簡介資料
        
        Args:
            json_path: JSON Lines 檔案路徑
        
        Returns:
            bool: 載入是否成功
        
        Raises:
            FileNotFoundError: 檔案不存在
            json.JSONDecodeError: JSON 格式錯誤
        """
        try:
            if not json_path.exists():
                logger.error(f"公司簡介檔案不存在: {json_path}")
                return False
            
            logger.info(f"正在載入公司簡介資料: {json_path}")
            
            # 讀取 JSON 檔案 (支援格式化的 JSON 或 JSON Lines)
            with open(json_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    logger.error("公司簡介檔案為空")
                    return False
                
                # 嘗試解析整個檔案作為單一 JSON 物件
                self.profile_data = json.loads(content)
            
            self.file_path = json_path
            self.loaded_at = datetime.now()
            
            # 建立索引
            self._build_indexes()
            
            logger.info(f"✅ 公司簡介資料載入成功")
            logger.info(f"   公司: {self.profile_data.get('company_name', 'Unknown')}")
            logger.info(f"   語言: {self.profile_data.get('locale', 'Unknown')}")
            logger.info(f"   FAQ 數量: {len(self.profile_data.get('faq', []))}")
            logger.info(f"   關鍵字數量: {len(self.profile_data.get('keywords', []))}")
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 格式錯誤: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 載入公司簡介失敗: {e}")
            return False
    
    def _build_indexes(self):
        """建立關鍵字與 FAQ 索引，提升查詢速度"""
        if not self.profile_data:
            return
        
        # 建立關鍵字索引
        keywords = self.profile_data.get('keywords', [])
        for keyword in keywords:
            normalized = keyword.lower().strip()
            if normalized:
                self._keyword_index[normalized] = self._keyword_index.get(normalized, [])
        
        # 建立 FAQ 索引
        faq_list = self.profile_data.get('faq', [])
        for idx, faq in enumerate(faq_list):
            question = faq.get('question', '')
            faq_keywords = faq.get('keywords', [])
            
            # 為每個 FAQ 關鍵字建立索引
            for kw in faq_keywords:
                normalized = kw.lower().strip()
                if normalized:
                    self._faq_index[normalized] = self._faq_index.get(normalized, {})
                    self._faq_index[normalized] = faq
        
        logger.debug(f"索引建立完成: {len(self._faq_index)} 個 FAQ 索引")
    
    def reload(self) -> bool:
        """
        重新載入公司簡介資料 (熱更新)
        
        Returns:
            bool: 重新載入是否成功
        """
        if not self.file_path:
            logger.warning("無法重新載入：檔案路徑未設定")
            return False
        
        logger.info("重新載入公司簡介資料...")
        return self.load_from_file(self.file_path)
    
    def is_loaded(self) -> bool:
        """檢查資料是否已載入"""
        return self.profile_data is not None
    
    def get_profile(self) -> Optional[Dict[str, Any]]:
        """
        取得完整的公司簡介資料
        
        Returns:
            Optional[Dict]: 公司簡介資料，若未載入則回傳 None
        """
        return self.profile_data
    
    def query(
        self, 
        company_id: Optional[str] = None, 
        topics: Optional[List[str]] = None,
        locale: str = "zh-TW"
    ) -> Optional[Dict[str, Any]]:
        """
        查詢公司資料 (主要查詢介面)
        
        Args:
            company_id: 公司 ID (可選，目前只支援單一公司)
            topics: 查詢主題列表，如 ["overview", "contacts", "services"]
            locale: 語言代碼 (預設繁中)
        
        Returns:
            Optional[Dict]: 查詢結果，包含請求的主題資料
        
        主題選項:
            - "overview": 公司介紹
            - "contacts": 聯絡資訊
            - "services": 服務項目
            - "faq": 常見問題
            - "promotions": 促銷活動
            - "milestones": 發展歷程
            - "all": 完整資料
        """
        if not self.is_loaded():
            logger.warning("公司簡介資料尚未載入")
            return None
        
        # 檢查公司 ID (目前只支援單一公司)
        if company_id and company_id != self.profile_data.get('company_id'):
            logger.warning(f"公司 ID 不匹配: {company_id}")
            return None
        
        # 如果沒有指定主題，回傳完整資料
        if not topics or "all" in topics:
            return self.profile_data
        
        # 依主題過濾資料
        result = {
            "company_id": self.profile_data.get('company_id'),
            "company_name": self.profile_data.get('company_name'),
            "locale": self.profile_data.get('locale'),
        }
        
        topic_mapping = {
            "overview": ["overview", "business_scope", "established_year"],
            "contacts": ["contacts"],
            "services": ["services"],
            "faq": ["faq"],
            "promotions": ["promotions"],
            "milestones": ["milestones"],
            "media": ["media"],
        }
        
        for topic in topics:
            if topic in topic_mapping:
                for field in topic_mapping[topic]:
                    if field in self.profile_data:
                        result[field] = self.profile_data[field]
        
        return result
    
    def get_contact_info(self) -> Dict[str, str]:
        """
        取得聯絡資訊
        
        Returns:
            Dict: 聯絡資訊字典，包含電話、地址、官網等
        """
        if not self.is_loaded():
            return {}
        
        return self.profile_data.get('contacts', {})
    
    def get_services(self) -> Dict[str, Any]:
        """
        取得服務項目
        
        Returns:
            Dict: 服務項目字典，包含核心服務和智慧方案
        """
        if not self.is_loaded():
            return {}
        
        return self.profile_data.get('services', {})
    
    def get_overview(self) -> str:
        """
        取得公司介紹
        
        Returns:
            str: 公司介紹文字
        """
        if not self.is_loaded():
            return ""
        
        return self.profile_data.get('overview', '')
    
    def get_faq_list(self) -> List[Dict[str, Any]]:
        """
        取得所有常見問題
        
        Returns:
            List[Dict]: FAQ 列表
        """
        if not self.is_loaded():
            return []
        
        return self.profile_data.get('faq', [])
    
    def search_faq(self, keyword: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        搜尋常見問題
        
        Args:
            keyword: 搜尋關鍵字
            limit: 最多回傳幾筆結果
        
        Returns:
            List[Dict]: 匹配的 FAQ 列表
        
        範例:
            ```python
            results = service.search_faq("電話")
            # [{"question": "客服電話是幾號？", "answer": "...", ...}]
            ```
        """
        if not self.is_loaded():
            return []
        
        keyword_lower = keyword.lower().strip()
        matched_faqs = []
        
        # 1. 精確匹配索引
        if keyword_lower in self._faq_index:
            matched_faqs.append(self._faq_index[keyword_lower])
        
        # 2. 模糊匹配 FAQ 內容
        faq_list = self.profile_data.get('faq', [])
        for faq in faq_list:
            if faq in matched_faqs:
                continue
            
            question = faq.get('question', '').lower()
            answer = faq.get('answer', '').lower()
            faq_keywords = [k.lower() for k in faq.get('keywords', [])]
            
            # 檢查是否匹配
            if (keyword_lower in question or 
                keyword_lower in answer or 
                any(keyword_lower in kw for kw in faq_keywords)):
                matched_faqs.append(faq)
            
            # 達到上限就停止
            if len(matched_faqs) >= limit:
                break
        
        return matched_faqs[:limit]
    
    def get_promotions(self) -> List[Dict[str, Any]]:
        """
        取得促銷活動列表
        
        Returns:
            List[Dict]: 促銷活動列表
        """
        if not self.is_loaded():
            return []
        
        return self.profile_data.get('promotions', [])
    
    def get_milestones(self) -> List[Dict[str, Any]]:
        """
        取得公司發展歷程
        
        Returns:
            List[Dict]: 發展歷程列表
        """
        if not self.is_loaded():
            return []
        
        return self.profile_data.get('milestones', [])
    
    def match_topic_by_keywords(self, query: str) -> str:
        """
        根據用戶查詢判斷最相關的主題
        
        Args:
            query: 用戶查詢文字
        
        Returns:
            str: 主題類型 (contact | service | overview | hours | promotion | faq)
        """
        query_lower = query.lower()
        
        # 定義主題關鍵字
        TOPIC_KEYWORDS = {
            "contact": ["電話", "聯絡", "客服", "地址", "官網", "聯繫", "email", "信箱"],
            "service": ["服務", "做什麼", "業務", "提供", "項目", "能力", "功能"],
            "overview": ["公司", "介紹", "背景", "關於", "你們是", "成立", "歷史"],
            "hours": ["營業時間", "幾點", "上班", "服務時間", "週末", "時間"],
            "promotion": ["優惠", "促銷", "活動", "折扣", "特價", "特惠"],
        }
        
        # 優先級匹配
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                return topic
        
        # 預設回傳 FAQ
        return "faq"
    
    def get_stats(self) -> Dict[str, Any]:
        """
        取得資料統計資訊
        
        Returns:
            Dict: 統計資訊
        """
        if not self.is_loaded():
            return {"loaded": False}
        
        return {
            "loaded": True,
            "company_id": self.profile_data.get('company_id'),
            "company_name": self.profile_data.get('company_name'),
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "file_path": str(self.file_path) if self.file_path else None,
            "keywords_count": len(self.profile_data.get('keywords', [])),
            "faq_count": len(self.profile_data.get('faq', [])),
            "services_count": len(self.profile_data.get('services', {}).get('core_services', [])),
            "promotions_count": len(self.profile_data.get('promotions', [])),
            "milestones_count": len(self.profile_data.get('milestones', [])),
        }


# ==================== 全域單例 ====================

_service_instance: Optional[CompanyProfileService] = None


def get_company_profile_service() -> CompanyProfileService:
    """
    取得全域公司簡介服務實例 (單例模式)
    
    Returns:
        CompanyProfileService: 服務實例
    
    使用範例:
        ```python
        from company_profile_service import get_company_profile_service
        
        service = get_company_profile_service()
        contacts = service.get_contact_info()
        ```
    """
    global _service_instance
    
    if _service_instance is None:
        _service_instance = CompanyProfileService()
    
    return _service_instance


def init_company_profile_service(json_path: Path) -> bool:
    """
    初始化全域公司簡介服務 (應在應用程式啟動時呼叫)
    
    Args:
        json_path: 公司簡介 JSON Lines 檔案路徑
    
    Returns:
        bool: 初始化是否成功
    
    使用範例:
        ```python
        # 在 app.py 的 startup_event 中
        from pathlib import Path
        from company_profile_service import init_company_profile_service
        
        json_path = Path("data/company_profiles/company_profile_chuanchi.jsonl")
        init_company_profile_service(json_path)
        ```
    """
    service = get_company_profile_service()
    return service.load_from_file(json_path)


# ==================== 使用範例 ====================

if __name__ == "__main__":
    # 測試服務
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    # 設定檔案路徑
    json_path = Path(__file__).parent.parent / "data" / "company_profiles" / "company_profile_chuanchi.jsonl"
    
    if not json_path.exists():
        print(f"❌ 檔案不存在: {json_path}")
        sys.exit(1)
    
    # 初始化服務
    print("=" * 60)
    print("測試 CompanyProfileService")
    print("=" * 60)
    
    service = CompanyProfileService()
    if not service.load_from_file(json_path):
        print("❌ 載入失敗")
        sys.exit(1)
    
    print("\n📊 統計資訊:")
    stats = service.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n📞 聯絡資訊:")
    contacts = service.get_contact_info()
    print(f"  電話: {contacts.get('company_phone_local')}")
    print(f"  地址: {contacts.get('address')}")
    print(f"  官網: {contacts.get('website')}")
    
    print("\n🛠️ 服務項目:")
    services = service.get_services()
    core_services = services.get('core_services', [])
    print(f"  核心服務數量: {len(core_services)}")
    for svc in core_services[:2]:
        print(f"  - {svc.get('category')}")
    
    print("\n❓ FAQ 搜尋測試:")
    test_keywords = ["電話", "官網", "服務"]
    for keyword in test_keywords:
        results = service.search_faq(keyword, limit=1)
        if results:
            print(f"  關鍵字 '{keyword}': {results[0].get('question')}")
        else:
            print(f"  關鍵字 '{keyword}': 無匹配結果")
    
    print("\n✅ 測試完成")
