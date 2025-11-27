# -*- coding: utf-8 -*-
"""
================================================================================
SEARCH_Goods 系統 - 住宅維修 LLM 服務
================================================================================

檔案名稱: repair_llm_service.py
建立日期: 2025年11月11日
撰寫模型: GitHub Copilot (Claude 3.5 Sonnet)

功能描述:
    專門用於住宅維修場景的 LLM 整合服務
    提供查詢擴展、意圖分析、對話回覆等 AI 功能

核心功能:
    - repair_expand_query(query) - 維修查詢擴展
    - repair_analyze_query(query) - 維修意圖分析
    - repair_chat_reply(query, history, results) - 維修對話回覆

環境變數控制:
    - ENABLE_REPAIR_SERVICE: 啟用維修服務（預設 False）
    - REPAIR_USE_LLM: 啟用 LLM 功能（預設 True）
    - REPAIR_OPENAI_MODEL: 使用的模型（預設 gpt-4o-mini）

================================================================================
"""
from __future__ import annotations
import json
import os
import re
from typing import Optional, List, Dict, Any
import logging
from openai import OpenAI
from services.llm_client import get_openai_client

# 從 repair_constants 導入常數
try:
    from repair_constants import (
        REPAIR_KEYWORDS,
        REPAIR_CATEGORY_MAP,
        RESPONSIBILITY_TYPES
    )
except ImportError:
    REPAIR_KEYWORDS = {}
    REPAIR_CATEGORY_MAP = {}
    RESPONSIBILITY_TYPES = ["住家", "公設"]

_logger = logging.getLogger(__name__)

# LLM 功能開關（環境變數控制）
ENABLE_REPAIR_SERVICE = os.getenv("ENABLE_REPAIR_SERVICE", "False").lower() in ("1", "true", "yes")
REPAIR_USE_LLM = os.getenv("REPAIR_USE_LLM", "True").lower() in ("1", "true", "yes")
REPAIR_OPENAI_MODEL = os.getenv("REPAIR_OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))


def _get_repair_client() -> Optional[OpenAI]:
    """動態獲取 OpenAI 客戶端（維修服務專用）"""
    if not ENABLE_REPAIR_SERVICE or not REPAIR_USE_LLM:
        return None
    
    client = get_openai_client()
    if not client:
        _logger.warning("OpenAI client not available for repair service")
        return None
    return client


def repair_expand_query(query: str) -> str:
    """
    擴展維修查詢，提取更多維修相關詞彙
    
    例如：
    - 輸入: "水龍頭一直滴水"
    - 輸出: "水龍頭 滴水 漏水 三角凡爾 墊圈"
    
    Args:
        query: 使用者原始查詢
    
    Returns:
        擴展後的查詢字串
    """
    if not REPAIR_USE_LLM:
        return query
    
    client = _get_repair_client()
    if not client:
        return query
    
    try:
        system_prompt = """你是一個專業的住宅維修助手。你的任務是擴展使用者的維修查詢，提取相關的維修關鍵字。

擴展規則：
1. 識別維修類別（給排水、電力、門窗、空調等）
2. 提取症狀關鍵字（漏水、滴水、堵塞、跳電等）
3. 加入相關的設備名稱（水龍頭、馬桶、插座等）
4. 保持簡潔，只返回關鍵字，用空格分隔

範例：
輸入: "廁所的馬桶一直流水"
輸出: "馬桶 流水 持續進水 水箱 浮球 落水皮"

輸入: "電燈一直閃爍"
輸出: "電燈 閃爍 跳電 電壓 開關 燈管"

只返回關鍵字，不要解釋。"""

        response = client.chat.completions.create(
            model=REPAIR_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.3,
            max_tokens=100,
        )
        
        expanded = response.choices[0].message.content.strip()
        _logger.info(f"[Repair LLM] Query expanded: '{query}' -> '{expanded}'")
        return expanded
        
    except Exception as e:
        _logger.error(f"[Repair LLM] Query expansion failed: {e}")
        return query


def repair_analyze_query(query: str) -> Dict[str, Any]:
    """
    分析維修查詢的意圖和結構
    
    返回 JSON 結構：
    {
        "category": "給排水設備",          # 維修類別
        "symptoms": ["漏水", "滴水"],      # 症狀關鍵字
        "equipment": ["水龍頭"],           # 設備名稱
        "responsibility": "住家",          # 責任類型
        "urgency": "中",                   # 緊急程度
        "required_terms": ["水龍頭", "漏水"], # 必須包含的詞
        "excluded_terms": []               # 排除的詞
    }
    
    Args:
        query: 使用者查詢
    
    Returns:
        意圖分析結果
    """
    if not REPAIR_USE_LLM:
        return {
            "category": "",
            "symptoms": [],
            "equipment": [],
            "responsibility": "住家",
            "urgency": "中",
            "required_terms": [],
            "excluded_terms": []
        }
    
    client = _get_repair_client()
    if not client:
        return {
            "category": "",
            "symptoms": [],
            "equipment": [],
            "responsibility": "住家",
            "urgency": "中",
            "required_terms": [],
            "excluded_terms": []
        }
    
    try:
        system_prompt = """你是一個專業的住宅維修助手。分析使用者的維修查詢，提取結構化資訊。

維修類別選項：
- 給/排水設備
- 電力系統
- 門窗設備
- 空調設備
- 結構問題
- 其他

責任類型選項：
- 住家（室內設備）
- 公設（公共區域）

緊急程度選項：
- 高（漏電、大量漏水等危險情況）
- 中（影響正常使用）
- 低（輕微不便）

返回 JSON 格式：
{
    "category": "維修類別",
    "symptoms": ["症狀1", "症狀2"],
    "equipment": ["設備名稱"],
    "responsibility": "住家 或 公設",
    "urgency": "高/中/低",
    "required_terms": ["必須包含的搜尋詞"],
    "excluded_terms": []
}

只返回 JSON，不要解釋。"""

        response = client.chat.completions.create(
            model=REPAIR_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.2,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        intent = json.loads(content)
        
        _logger.info(f"[Repair LLM] Intent analyzed: {intent}")
        return intent
        
    except Exception as e:
        _logger.error(f"[Repair LLM] Intent analysis failed: {e}")
        return {
            "category": "",
            "symptoms": [],
            "equipment": [],
            "responsibility": "住家",
            "urgency": "中",
            "required_terms": [],
            "excluded_terms": []
        }


def repair_chat_reply(
    query: str,
    history: List[Dict[str, str]],
    results: List[Dict[str, Any]],
    catalog_info: Optional[str] = None
) -> str:
    """
    生成維修對話回覆
    
    根據搜尋結果生成自然語言回覆，包括：
    - 維修項目說明
    - 處理建議
    - 相關資源連結
    
    Args:
        query: 使用者查詢
        history: 對話歷史
        results: 搜尋結果（維修項目列表）
        catalog_info: 維修項目目錄資訊
    
    Returns:
        生成的回覆文字
    """
    if not REPAIR_USE_LLM:
        # 降級：使用範本式回覆
        return _generate_template_reply(query, results)
    
    client = _get_repair_client()
    if not client:
        return _generate_template_reply(query, results)
    
    try:
        # 準備搜尋結果摘要
        results_summary = _format_results_for_llm(results)
        
        # 準備對話歷史
        history_text = ""
        if history:
            recent_history = history[-3:]  # 只用最近 3 輪
            history_text = "\n".join([
                f"{'使用者' if msg['role'] == 'user' else '助手'}: {msg['content']}"
                for msg in recent_history
            ])
        
        system_prompt = """你是一個專業且友善的住宅維修助手。你的任務是幫助住戶解決維修問題。

回覆風格：
- 專業但易懂，避免過多專業術語
- 友善且有同理心
- 提供具體的處理建議
- 包含安全提醒（如有需要）
- 引導住戶查看詳細資料或聯絡物業

回覆結構：
1. 先理解問題並表示同理心
2. 說明可能的原因
3. 提供處理建議
4. 引導查看詳細資料或影片
5. 提醒緊急情況的處理方式

如果有多個維修項目匹配，簡要說明每個項目的差異。
如果沒有找到匹配結果，提供一般性建議並建議聯絡物業。"""

        user_prompt = f"""使用者問題：{query}

搜尋到的維修項目：
{results_summary}

請生成一個專業且友善的回覆。"""
        
        # 添加對話歷史（如果有）
        if history_text:
            user_prompt = f"""使用者問題：{query}

對話歷史：
{history_text}

搜尋到的維修項目：
{results_summary}

請生成一個專業且友善的回覆。"""

        response = client.chat.completions.create(
            model=REPAIR_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500,
        )
        
        reply = response.choices[0].message.content.strip()
        _logger.info(f"[Repair LLM] Generated reply for query: {query}")
        return reply
        
    except Exception as e:
        _logger.error(f"[Repair LLM] Chat reply generation failed: {e}")
        return _generate_template_reply(query, results)


def _format_results_for_llm(results: List[Dict[str, Any]]) -> str:
    """格式化搜尋結果給 LLM"""
    if not results:
        return "沒有找到相關的維修項目。"
    
    formatted = []
    for idx, item in enumerate(results, 1):
        text = f"""項目 {idx}:
- 維修類別: {item.get('維修項目類別', item.get('維修類別', ''))}
- 維修項目: {item.get('維修項目名稱', item.get('維修項目', ''))}
- 常見症狀: {item.get('常見維修反應細項', item.get('常見症狀', ''))}
- 處理建議: {item.get('處理建議 (SOP) 補充', item.get('處理建議', ''))}"""
        
        # 已暫時隱藏詳細資料與影片說明的提示，避免在 LLM 上下文中帶入外部連結。
        
        formatted.append(text)
    
    return "\n\n".join(formatted)


def _generate_template_reply(query: str, results: List[Dict[str, Any]]) -> str:
    """生成範本式回覆（降級保護）"""
    if not results:
        return f"""很抱歉，目前沒有找到與「{query}」相關的維修項目。

建議您：
1. 嘗試使用其他關鍵字描述問題
2. 直接聯絡物業管理處尋求協助
3. 如遇緊急情況，請立即撥打緊急維修專線

感謝您的查詢！🛠️"""
    
    # 格式化結果
    reply_parts = [f"找到 {len(results)} 個相關的維修項目：\n"]
    
    for idx, item in enumerate(results, 1):
        category = item.get('維修項目類別', item.get('維修類別', ''))
        name = item.get('維修項目名稱', item.get('維修項目', ''))
        symptoms = item.get('常見維修反應細項', item.get('常見症狀', ''))
        
        reply_parts.append(f"\n{idx}. **{name}** ({category})")
        reply_parts.append(f"   症狀：{symptoms}")
        
        if item.get('頁面連結'):
            reply_parts.append(f"   📄 [查看詳細資料]({item.get('頁面連結')})")
        
        if item.get('Youtube 影片說明', item.get('影片說明')):
            reply_parts.append(f"   🎥 [觀看影片說明]({item.get('Youtube 影片說明', item.get('影片說明'))})")
    
    reply_parts.append("\n\n如需更多協助，請聯絡物業管理處。🏠")
    
    return "\n".join(reply_parts)


def generate_repair_summary(results: List[Dict[str, Any]]) -> str:
    """
    生成維修項目摘要（用於快速預覽）
    
    Args:
        results: 維修項目列表
    
    Returns:
        摘要文字
    """
    if not results:
        return "暫無維修項目"
    
    if len(results) == 1:
        item = results[0]
        return f"{item.get('維修項目名稱', item.get('維修項目', ''))} - {item.get('維修項目類別', item.get('維修類別', ''))}"
    
    categories = set()
    for item in results:
        cat = item.get('維修項目類別', item.get('維修類別', ''))
        if cat:
            categories.add(cat)
    
    return f"共 {len(results)} 個項目（{', '.join(categories)}）"


# 測試用便利函數
if __name__ == "__main__":
    # 測試查詢擴展
    test_query = "水龍頭一直滴水"
    print(f"原始查詢: {test_query}")
    
    expanded = repair_expand_query(test_query)
    print(f"擴展查詢: {expanded}")
    
    # 測試意圖分析
    intent = repair_analyze_query(test_query)
    print(f"意圖分析: {json.dumps(intent, ensure_ascii=False, indent=2)}")
    
    # 測試範本回覆
    mock_results = [
        {
            "維修項目類別": "給/排水設備",
            "維修項目名稱": "水龍頭持續滴水",
            "常見維修反應細項": "水龍頭或三角凡爾持續滴水。",
            "處理建議 (SOP) 補充": "關閉進水開關，更換墊圈、止水帶或水龍頭軸心。",
            "頁面連結": "https://example.com/repair/1",
            "Youtube 影片說明": "https://youtu.be/example"
        }
    ]
    
    reply = _generate_template_reply(test_query, mock_results)
    print(f"\n範本回覆:\n{reply}")


# ================================================================================
# AI 優化客服回覆
# ================================================================================

def optimize_customer_service_reply(
    original_text: str,
    context: str = "repair_customer_service"
) -> str:
    """
    使用 AI 優化客服回覆內容
    
    將客服人員輸入的原始文字優化為更專業、友善、有同理心的客服用語
    
    Args:
        original_text: 客服人員輸入的原始文字
        context: 對話情境（預設為維修客服）
    
    Returns:
        優化後的客服回覆文字
    
    Examples:
        >>> optimize_customer_service_reply("等等我問師傅")
        "好的，我現在為您聯繫維修師傅確認，請您稍候片刻。"
        
        >>> optimize_customer_service_reply("30分鐘到")
        "感謝您的耐心等候，維修師傅預計在 30 分鐘內到達現場。"
    """
    if not REPAIR_USE_LLM:
        _logger.warning("Repair LLM disabled, returning original text")
        return original_text
    
    client = _get_repair_client()
    if not client:
        _logger.warning("No OpenAI client available, returning original text")
        return original_text
    
    try:
        system_prompt = """你是一位專業的住宅維修客服人員培訓師。你的任務是將客服人員輸入的簡短口語化訊息，優化為專業、友善且有同理心的客服用語。

優化原則：
1. **保持簡潔**：不要過度冗長，控制在 1-3 句話
2. **友善親切**：使用「您」稱呼，語氣溫和有禮
3. **同理心**：理解客戶焦慮，適時表達理解與安慰
4. **專業性**：使用正式但不生硬的用語
5. **資訊清晰**：保留原文的核心資訊（時間、地點、動作）
6. **行動導向**：明確告知下一步驟或預期結果

常見情境範例：

情境 1: 時間回覆
- 原文: "30分鐘到"
- 優化: "感謝您的耐心等候，維修師傅預計在 30 分鐘內到達現場。"

情境 2: 確認中
- 原文: "等等我問師傅"
- 優化: "好的，我現在為您聯繫維修師傅確認，請您稍候片刻。"

情境 3: 問題確認
- 原文: "是漏水對吧"
- 優化: "您好，我想確認一下，您遇到的是漏水問題對嗎？"

情境 4: 解決方案
- 原文: "先關總開關"
- 優化: "為了您的安全，請您先將總開關關閉，避免狀況惡化。"

情境 5: 完成通知
- 原文: "修好了"
- 優化: "太好了！維修師傅已經完成修復，請您確認是否正常運作。"

情境 6: 道歉說明
- 原文: "師傅塞車會晚點"
- 優化: "非常抱歉，由於路況擁塞，維修師傅可能會稍微延遲到達，感謝您的諒解。"

注意事項：
- 不要加入原文沒有的資訊
- 保持原文的時間、數字等關鍵資訊
- 如果原文已經很專業，只需微調語氣
- 避免使用過於正式或生硬的公文用語

請直接輸出優化後的文字，不需要任何解釋或標記。"""

        user_prompt = f"請優化以下客服回覆:\n\n{original_text}"
        
        response = client.chat.completions.create(
            model=REPAIR_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        optimized = response.choices[0].message.content.strip()
        
        # 移除可能的引號包裹
        optimized = optimized.strip('"\'')
        
        _logger.info(f"[Repair] Optimized reply: '{original_text}' -> '{optimized}'")
        
        return optimized
        
    except Exception as e:
        _logger.error(f"[Repair] Optimize reply failed: {e}", exc_info=True)
        # 發生錯誤時返回原文
        return original_text
