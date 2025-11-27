# -*- coding: utf-8 -*-
"""
================================================================================
公司簡介回應格式化器 - CompanyResponseFormatter
================================================================================

檔案名稱: company_response_formatter.py
建立日期: 2025年11月9日
功能描述:
    將公司簡介資料格式化為使用者友善的聊天回應
    支援多種主題類型的格式化模板

核心功能:
    - 聯絡資訊格式化
    - 服務項目格式化
    - 公司介紹格式化
    - FAQ 回應格式化
    - Emoji 增強可讀性

設計原則:
    - 結構化呈現
    - 分層次資訊
    - 引導下一步行動

================================================================================
"""

from typing import Dict, List, Any, Optional
import logging
import urllib.parse

logger = logging.getLogger(__name__)


class CompanyResponseFormatter:
    """
    公司簡介回應格式化器
    
    功能:
        - 將結構化的公司資料轉換為聊天回應
        - 支援不同主題的專用格式化模板
        - 添加 Emoji 增強可讀性
    
    使用範例:
        ```python
        formatter = CompanyResponseFormatter()
        
        # 格式化聯絡資訊
        response = formatter.format_contact_info(contacts)
        
        # 格式化服務項目
        response = formatter.format_services(services)
        ```
    """
    
    def __init__(self):
        """初始化格式化器"""
        pass
    
    def format_contact_info(
        self, 
        contacts: Dict[str, str],
        profile_page_url: Optional[str] = None,
        introduction_video: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        格式化聯絡資訊
        
        Args:
            contacts: 聯絡資訊字典
            profile_page_url: 官方介紹頁面 URL
            introduction_video: 公司介紹影片 URL
        
        Returns:
            Dict: 包含文字回應和結構化資料
                - text: 格式化的回應文字
                - rich_content: 豐富內容（連結、地圖等）
        """
        if not contacts:
            return {
                "text": "抱歉，目前無法取得聯絡資訊。",
                "rich_content": None
            }
        
        lines = ["📞 傳啟資訊聯絡方式\n"]
        rich_items = []
        
        # 公司電話
        if contacts.get('company_phone_local'):
            phone = contacts['company_phone_local']
            lines.append(f"🏢 公司電話：{phone}")
            rich_items.append({
                "type": "phone",
                "label": "公司電話",
                "value": phone,
                "icon": "🏢",
                "action": f"tel:{phone.replace('-', '')}"
            })
        
        # 客服專線
        if contacts.get('customer_service_phone_local'):
            cs_phone = contacts['customer_service_phone_local']
            lines.append(f"📞 客服專線：{cs_phone}")
            rich_items.append({
                "type": "phone",
                "label": "客服專線",
                "value": cs_phone,
                "icon": "📞",
                "action": f"tel:{cs_phone.replace('-', '')}"
            })
        
        # 地址 (加入 Google Maps 連結)
        if contacts.get('address'):
            address = contacts['address']
            lines.append(f"📍 公司地址：{address}")
            
            # 生成 Google Maps URL
            maps_query = urllib.parse.quote(f"{address} 傳啟資訊")
            maps_url = f"https://www.google.com/maps/search/?api=1&query={maps_query}"
            
            rich_items.append({
                "type": "address",
                "label": "公司地址",
                "value": address,
                "icon": "📍",
                "action": maps_url,
                "action_label": "在 Google Maps 中查看"
            })
        
        # 官網
        if contacts.get('website'):
            website = contacts['website']
            lines.append(f"🌐 官方網站：{website}")
            rich_items.append({
                "type": "url",
                "label": "官方網站",
                "value": website,
                "icon": "🌐",
                "action": website,
                "action_label": "訪問官網"
            })
        
        # 服務時間
        if contacts.get('service_hours'):
            lines.append(f"⏰ 服務時間：{contacts['service_hours']}")
        
        # 添加頁面連結和影片
        if profile_page_url:
            lines.append(f"\n🔗 了解更多：{profile_page_url}")
            rich_items.append({
                "type": "url",
                "label": "官方介紹頁",
                "value": profile_page_url,
                "icon": "🔗",
                "action": profile_page_url,
                "action_label": "立即瀏覽"
            })
        
        if introduction_video:
            lines.append(f"🎥 公司介紹影片：{introduction_video}")
            rich_items.append({
                "type": "video",
                "label": "公司介紹影片",
                "value": introduction_video,
                "icon": "🎥",
                "action": introduction_video,
                "action_label": "觀看介紹"
            })
        
        lines.append("\n您可以透過以上方式與我們聯繫，或直接訪問官網了解更多資訊！")
        
        return {
            "text": "\n".join(lines),
            "rich_content": {
                "type": "contact_info",
                "items": rich_items
            }
        }
    
    def format_services(
        self, 
        services: Dict[str, Any],
        profile_page_url: Optional[str] = None,
        introduction_video: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        格式化服務項目
        
        Args:
            services: 服務項目字典
            profile_page_url: 官方介紹頁面 URL
            introduction_video: 公司介紹影片 URL
        
        Returns:
            Dict[str, Any]: 包含 text 和 rich_content 的字典
        """
        if not services:
            return {
                "text": "抱歉，目前無法取得服務項目資訊。",
                "rich_content": None
            }
        
        lines = ["🏢 傳啟資訊主要服務項目\n"]
        lines.append("我們提供以下專業服務：\n")
        
        # 核心服務
        core_services = services.get('core_services', [])
        if core_services:
            lines.append("【核心服務】")
            for idx, service in enumerate(core_services, 1):
                category = service.get('category', '未知服務')
                description = service.get('description', '')
                
                lines.append(f"{idx}️⃣ {category}")
                if description:
                    lines.append(f"   {description}\n")
        
        # 智慧解決方案
        smart_solutions = services.get('smart_solutions', [])
        if smart_solutions:
            lines.append("【智慧解決方案】")
            for solution in smart_solutions:
                lines.append(f"✨ {solution}")
        
        # 建立 rich_content
        rich_items: List[Dict[str, Any]] = []
        
        if profile_page_url:
            lines.append(f"\n🔗 了解更多服務：{profile_page_url}")
            rich_items.append({
                "type": "url",
                "label": "服務詳情頁面",
                "value": profile_page_url,
                "icon": "🔗",
                "action": profile_page_url,
                "action_label": "查看詳情"
            })
        
        if introduction_video:
            lines.append(f"🎥 服務介紹影片：{introduction_video}")
            rich_items.append({
                "type": "video",
                "label": "服務介紹影片",
                "value": introduction_video,
                "icon": "🎥",
                "action": introduction_video,
                "action_label": "觀看影片"
            })
        
        lines.append("\n需要了解更多詳情嗎？我可以為您進一步說明！")
        
        return {
            "text": "\n".join(lines),
            "rich_content": {
                "type": "service_info",
                "items": rich_items
            } if rich_items else None
        }
    
    def format_overview(
        self, 
        company_name: str,
        overview: str, 
        established_year: Optional[str] = None,
        business_scope: Optional[List[str]] = None,
        milestones: Optional[List[Dict]] = None,
        profile_page_url: Optional[str] = None,
        introduction_video: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        格式化公司介紹
        
        Args:
            company_name: 公司名稱
            overview: 公司簡介文字
            established_year: 成立年份
            business_scope: 業務範圍列表
            milestones: 發展歷程列表
        
        Returns:
            Dict: 包含文字與 rich_content 的回應
        """
        lines = [f"🏢 關於{company_name}\n"]
        rich_items: List[Dict[str, Any]] = []
        
        # 簡介 (取前 200 字)
        if overview:
            summary = overview[:200] + "..." if len(overview) > 200 else overview
            lines.append(summary)
            lines.append("")
        
        # 核心優勢
        if established_year:
            lines.append("【核心優勢】")
            years_in_business = 2025 - int(established_year)
            lines.append(f"✅ 近 {years_in_business} 年的資訊系統整合經驗")
            lines.append("✅ 深厚的軟硬體整合能力")
            lines.append("✅ 專業技術團隊與完整解決方案")
            lines.append("✅ 協助企業提升品牌價值與營運效率\n")
        
        # 發展歷程
        if milestones and len(milestones) > 0:
            lines.append("【發展歷程】")
            for milestone in milestones:
                year = milestone.get('year', '')
                event = milestone.get('event', '')
                if year and event:
                    lines.append(f"📅 {year} 年：{event}")
            lines.append("")
        
        # 業務範圍
        if business_scope and len(business_scope) > 0:
            lines.append("【業務範圍】")
            scope_text = "、".join(business_scope[:8])  # 最多顯示 8 項
            lines.append(scope_text)
            lines.append("")
        
        if profile_page_url:
            lines.append(f"🔗 官方介紹頁面：{profile_page_url}")
            rich_items.append({
                "type": "url",
                "label": "官方介紹頁",
                "value": profile_page_url,
                "icon": "🔗",
                "action": profile_page_url,
                "action_label": "立即瀏覽"
            })
        if introduction_video:
            lines.append(f"🎥 影片介紹：{introduction_video}")
            rich_items.append({
                "type": "video",
                "label": "公司介紹影片",
                "value": introduction_video,
                "icon": "🎥",
                "action": introduction_video,
                "action_label": "觀看介紹"
            })
        
        lines.append("想了解更多服務內容嗎？")
        
        return {
            "text": "\n".join(lines),
            "rich_content": {
                "type": "company_overview",
                "items": rich_items
            } if rich_items else None
        }
    
    def format_business_hours(
        self, 
        service_hours: str, 
        contacts: Dict[str, str],
        profile_page_url: Optional[str] = None,
        introduction_video: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        格式化營業時間
        
        Args:
            service_hours: 服務時間文字
            contacts: 聯絡資訊 (用於補充資訊)
            profile_page_url: 官方介紹頁面 URL
            introduction_video: 公司介紹影片 URL
        
        Returns:
            Dict[str, Any]: 包含 text 和 rich_content 的字典
        """
        lines = ["⏰ 傳啟資訊服務時間\n"]
        
        if service_hours:
            lines.append(f"📅 營業時間：{service_hours}")
            
            # 判斷是否包含週末資訊
            if "週一" in service_hours and "週五" in service_hours:
                lines.append("🚫 週末及國定假日休息\n")
        
        lines.append("如需緊急聯繫，您可以：")
        
        if contacts.get('customer_service_phone_local'):
            lines.append(f"📞 客服專線：{contacts['customer_service_phone_local']}")
        
        if contacts.get('website'):
            lines.append(f"🌐 官方網站：{contacts['website']}")
        
        # 建立 rich_content
        rich_items: List[Dict[str, Any]] = []
        
        if profile_page_url:
            lines.append(f"\n🔗 更多資訊：{profile_page_url}")
            rich_items.append({
                "type": "url",
                "label": "官方介紹頁",
                "value": profile_page_url,
                "icon": "🔗",
                "action": profile_page_url,
                "action_label": "立即瀏覽"
            })
        
        if introduction_video:
            lines.append(f"🎥 公司介紹影片：{introduction_video}")
            rich_items.append({
                "type": "video",
                "label": "公司介紹影片",
                "value": introduction_video,
                "icon": "🎥",
                "action": introduction_video,
                "action_label": "觀看介紹"
            })
        
        lines.append("\n📧 或透過官網留言，我們會盡快回覆！")
        
        return {
            "text": "\n".join(lines),
            "rich_content": {
                "type": "business_hours",
                "items": rich_items
            } if rich_items else None
        }
    
    def format_faq(
        self, 
        faq: Dict[str, Any],
        profile_page_url: Optional[str] = None,
        introduction_video: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        格式化單一 FAQ
        
        Args:
            faq: FAQ 字典
            profile_page_url: 官方介紹頁面 URL
            introduction_video: 公司介紹影片 URL
        
        Returns:
            Dict[str, Any]: 包含 text 和 rich_content 的字典
        """
        if not faq:
            return {
                "text": "抱歉，找不到相關的常見問題。",
                "rich_content": None
            }
        
        question = faq.get('question', '')
        answer = faq.get('answer', '')
        category = faq.get('category', '')
        
        # 根據分類添加不同的 Emoji
        category_emoji = {
            'contact': '📞',
            'service': '🛠️',
            'about': '🏢',
            'general': '❓'
        }
        
        emoji = category_emoji.get(category, '❓')
        
        lines = [f"{emoji} {question}\n"]
        lines.append(answer)
        
        # 建立 rich_content
        rich_items: List[Dict[str, Any]] = []
        
        if profile_page_url:
            lines.append(f"\n🔗 了解更多：{profile_page_url}")
            rich_items.append({
                "type": "url",
                "label": "官方介紹頁",
                "value": profile_page_url,
                "icon": "🔗",
                "action": profile_page_url,
                "action_label": "立即瀏覽"
            })
        
        if introduction_video:
            lines.append(f"🎥 公司介紹影片：{introduction_video}")
            rich_items.append({
                "type": "video",
                "label": "公司介紹影片",
                "value": introduction_video,
                "icon": "🎥",
                "action": introduction_video,
                "action_label": "觀看介紹"
            })
        
        lines.append("\n如有其他問題，歡迎隨時詢問！")
        
        return {
            "text": "\n".join(lines),
            "rich_content": {
                "type": "faq_answer",
                "items": rich_items
            } if rich_items else None
        }
    
    def format_faq_list(self, faq_list: List[Dict[str, Any]], query: str) -> str:
        """
        格式化 FAQ 列表
        
        Args:
            faq_list: FAQ 列表
            query: 原始查詢
        
        Returns:
            str: 格式化的回應文字
        """
        if not faq_list:
            return f"抱歉，找不到與「{query}」相關的常見問題。\n\n您可以試試其他關鍵字，或直接聯絡客服：04-26062295"
        
        lines = ["❓ 常見問題\n"]
        
        for idx, faq in enumerate(faq_list, 1):
            question = faq.get('question', '')
            answer = faq.get('answer', '')
            
            lines.append(f"{idx}. {question}")
            lines.append(f"   {answer}\n")
        
        lines.append("需要了解其他問題嗎？")
        
        return "\n".join(lines)
    
    def format_promotion(self, promotion: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化促銷活動
        
        Args:
            promotion: 促銷活動字典
        
        Returns:
            Dict: 包含文字回應和結構化資料
        """
        if not promotion:
            return {
                "text": "目前沒有進行中的促銷活動。",
                "rich_content": None
            }
        
        title = promotion.get('title', '限時優惠')
        description = promotion.get('description', '')
        url = promotion.get('url', '')
        video = promotion.get('video', '')
        
        lines = [f"🎉 {title}\n"]
        rich_items = []
        
        if description:
            # 將描述拆分成商品列表
            if '：' in description:
                parts = description.split('：', 1)
                lines.append(parts[0] + "：\n")
                
                # 拆分商品
                items = parts[1].split('，')
                for item in items:
                    item = item.strip()
                    if item:
                        lines.append(f"👜 {item}")
            else:
                lines.append(description)
        
        lines.append("")
        
        if url:
            lines.append(f"🔗 查看更多優惠：{url}")
            rich_items.append({
                "type": "url",
                "label": "查看更多優惠",
                "value": url,
                "icon": "🔗",
                "action": url,
                "action_label": "立即查看"
            })
        
        if video:
            lines.append(f"🎥 商品介紹影片：{video}")
            rich_items.append({
                "type": "video",
                "label": "商品介紹影片",
                "value": video,
                "icon": "🎥",
                "action": video,
                "action_label": "觀看影片"
            })
        
        lines.append("\n立即選購，享受超值優惠！")
        
        return {
            "text": "\n".join(lines),
            "rich_content": {
                "type": "promotion",
                "title": title,
                "items": rich_items
            }
        }
    
    def format_by_topic(
        self, 
        topic: str, 
        profile_data: Dict[str, Any],
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        根據主題自動選擇格式化方法
        
        Args:
            topic: 主題類型 (contact | service | overview | hours | promotion | faq)
            profile_data: 完整的公司資料
            query: 原始查詢 (可選，用於 FAQ 搜尋)
        
        Returns:
            Dict: 包含文字回應和結構化資料
                - text: 格式化的回應文字
                - rich_content: 豐富內容（連結、地圖等）
        """
        if topic == "contact":
            contacts = profile_data.get('contacts', {})
            media = profile_data.get('media', {}) or {}
            profile_url = profile_data.get("profile_page_url") or contacts.get("website")
            intro_video = media.get("introduction_video") or media.get("introductionVideo")
            return self.format_contact_info(
                contacts,
                profile_page_url=profile_url,
                introduction_video=intro_video
            )
        
        elif topic == "service":
            services = profile_data.get('services', {})
            media = profile_data.get('media', {}) or {}
            profile_url = profile_data.get("profile_page_url") or profile_data.get("contacts", {}).get("website")
            intro_video = media.get("introduction_video") or media.get("introductionVideo")
            return self.format_services(
                services,
                profile_page_url=profile_url,
                introduction_video=intro_video
            )
        
        elif topic == "overview":
            media = profile_data.get('media', {}) or {}
            profile_url = profile_data.get("profile_page_url") or profile_data.get("contacts", {}).get("website")
            intro_video = media.get("introduction_video") or media.get("introductionVideo")
            result = self.format_overview(
                company_name=profile_data.get('company_name', '本公司'),
                overview=profile_data.get('overview', ''),
                established_year=profile_data.get('established_year'),
                business_scope=profile_data.get('business_scope', []),
                milestones=profile_data.get('milestones', []),
                profile_page_url=profile_url,
                introduction_video=intro_video,
            )
            return result
        
        elif topic == "hours":
            contacts = profile_data.get('contacts', {})
            service_hours = contacts.get('service_hours', '')
            media = profile_data.get('media', {}) or {}
            profile_url = profile_data.get("profile_page_url") or contacts.get("website")
            intro_video = media.get("introduction_video") or media.get("introductionVideo")
            return self.format_business_hours(
                service_hours, 
                contacts,
                profile_page_url=profile_url,
                introduction_video=intro_video
            )
        
        elif topic == "promotion":
            promotions = profile_data.get('promotions', [])
            if promotions:
                return self.format_promotion(promotions[0])
            else:
                return {
                    "text": "目前沒有進行中的促銷活動。",
                    "rich_content": None
                }
        
        elif topic == "faq":
            media = profile_data.get('media', {}) or {}
            profile_url = profile_data.get("profile_page_url") or profile_data.get("contacts", {}).get("website")
            intro_video = media.get("introduction_video") or media.get("introductionVideo")
            
            # 如果有查詢，搜尋 FAQ
            if query:
                from company_profile_service import get_company_profile_service
                service = get_company_profile_service()
                faq_results = service.search_faq(query, limit=3)
                
                if faq_results:
                    if len(faq_results) == 1:
                        return self.format_faq(
                            faq_results[0],
                            profile_page_url=profile_url,
                            introduction_video=intro_video
                        )
                    else:
                        result = self.format_faq_list(faq_results, query)
                else:
                    result = f"抱歉，找不到與「{query}」相關的常見問題。"
            else:
                # 否則顯示所有 FAQ
                faq_list = profile_data.get('faq', [])
                result = self.format_faq_list(faq_list[:5], query or "常見問題")
            
            if isinstance(result, str):
                return {"text": result, "rich_content": None}
            return result
        
        else:
            return {
                "text": "抱歉，無法識別您的問題類型。您可以詢問：\n- 聯絡方式\n- 服務項目\n- 公司介紹\n- 營業時間",
                "rich_content": None
            }


# ==================== 全域實例 ====================

_formatter_instance: Optional[CompanyResponseFormatter] = None


def get_company_response_formatter() -> CompanyResponseFormatter:
    """
    取得全域格式化器實例 (單例模式)
    
    Returns:
        CompanyResponseFormatter: 格式化器實例
    """
    global _formatter_instance
    
    if _formatter_instance is None:
        _formatter_instance = CompanyResponseFormatter()
    
    return _formatter_instance


# ==================== 快捷函數 ====================

def format_company_response(
    topic: str, 
    profile_data: Dict[str, Any],
    query: Optional[str] = None
) -> str:
    """
    快捷函數：格式化公司簡介回應
    
    Args:
        topic: 主題類型
        profile_data: 公司資料
        query: 原始查詢
    
    Returns:
        str: 格式化的回應
    
    使用範例:
        ```python
        from company_response_formatter import format_company_response
        
        response = format_company_response("contact", profile_data)
        ```
    """
    formatter = get_company_response_formatter()
    return formatter.format_by_topic(topic, profile_data, query)


# ==================== 測試範例 ====================

if __name__ == "__main__":
    import sys
    from pathlib import Path
    from company_profile_service import CompanyProfileService
    
    logging.basicConfig(level=logging.INFO)
    
    # 載入公司資料
    json_path = Path(__file__).parent.parent / "data" / "company_profiles" / "company_profile_chuanchi.jsonl"
    
    if not json_path.exists():
        print(f"❌ 檔案不存在: {json_path}")
        sys.exit(1)
    
    service = CompanyProfileService()
    if not service.load_from_file(json_path):
        print("❌ 載入失敗")
        sys.exit(1)
    
    profile = service.get_profile()
    formatter = CompanyResponseFormatter()
    
    print("=" * 60)
    print("測試 CompanyResponseFormatter")
    print("=" * 60)
    
    # 測試各種格式化
    topics = [
        ("contact", "聯絡資訊"),
        ("service", "服務項目"),
        ("overview", "公司介紹"),
        ("hours", "營業時間"),
        ("faq", "常見問題 (關鍵字: 電話)")
    ]
    
    for topic, name in topics:
        print(f"\n{'='*60}")
        print(f"📝 測試主題: {name}")
        print(f"{'='*60}")
        
        if topic == "faq":
            response = formatter.format_by_topic(topic, profile, query="電話")
        else:
            response = formatter.format_by_topic(topic, profile)
        
        print(response)
    
    print(f"\n{'='*60}")
    print("✅ 測試完成")
    print(f"{'='*60}")
