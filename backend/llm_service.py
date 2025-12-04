"""
================================================================================
SEARCH_Goods 系統 - 大語言模型服務
================================================================================

檔案名稱: llm_service.py
撰寫日期: 2025年11月5日
撰寫時間: 15:00-17:30
撰寫模型: GitHub Copilot (Claude 3.5 Sonnet)
最後更新: 2025年11月5日 17:30

功能描述:
    OpenAI GPT 整合服務，提供查詢擴展、意圖分析、內容生成等 AI 功能
    支援條件性啟用（通過環境變數控制）

核心功能:
    - llm_expand_query(query) - 查詢擴展
    - llm_analyze_query(query) - 意圖分析
    - llm_shorten_20(text) - 文字簡化
    - chat_reply(query, history) - 對話回覆

LLM service using OpenAI SDK.

Provides:
- llm_expand_query(query) -> expanded query (string)
- llm_shorten_20(text) -> short summary (<=20 chars ideally)
- llm_analyze_query(query) -> structured intent JSON

Enable by setting OPENAI_API_KEY in env and USE_LLM_EXPAND/USE_LLM_SHORTDESC to true.
"""
from __future__ import annotations
import json
import os
import re
from typing import Optional, List, Dict, Any, Set
import threading
import time
import pandas as pd
from openai import OpenAI
import logging
from goods_search_service import (
    load_data,
    search_products,
    search_products_with_hierarchy,
    get_category_index,
    DEFAULT_DATA_PATH,
)
from field_utils import FieldAccessor
from planner.event_food_planner import parse_event_context
from services.categories_service import get_category_terms, get_all_categories
from utils.logging_utils import get_logger

_logger = get_logger(__name__)

# 分類提示詞快取配置
CATEGORY_PROMPT_TTL = int(os.getenv("CATEGORY_PROMPT_TTL", "300"))  # 秒
_CATEGORY_PROMPT_CACHE: Optional[str] = None
_CATEGORY_PROMPT_TS: float = 0.0
_CATEGORY_PROMPT_LOCK = threading.Lock()

# === 搜索功能 LLM 配置 ===
SEARCH_USE_EXPAND = os.getenv("SEARCH_USE_LLM_EXPAND", os.getenv("USE_LLM_EXPAND", "False")).lower() in ("1", "true", "yes")
SEARCH_USE_SHORT = os.getenv("SEARCH_USE_LLM_SHORTDESC", os.getenv("USE_LLM_SHORTDESC", "False")).lower() in ("1", "true", "yes")
SEARCH_USE_RERANK = os.getenv("SEARCH_USE_LLM_RERANK", os.getenv("USE_LLM_RERANK", "False")).lower() in ("1", "true", "yes")
SEARCH_USE_INTENT = os.getenv("SEARCH_USE_LLM_INTENT", os.getenv("USE_LLM_INTENT", "False")).lower() in ("1", "true", "yes")
SEARCH_USE_PROMO = os.getenv("SEARCH_USE_LLM_PROMO", os.getenv("USE_LLM_PROMO", "False")).lower() in ("1", "true", "yes")
SEARCH_OPENAI_MODEL = os.getenv("SEARCH_OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

# === 聊天功能 LLM 配置 ===
# 強制啟用所有 LLM 功能以確保一律透過 LLM 互動
CHAT_USE_EXPAND = os.getenv("CHAT_USE_LLM_EXPAND", os.getenv("USE_LLM_EXPAND", "True")).lower() in ("1", "true", "yes")
CHAT_USE_SHORT = os.getenv("CHAT_USE_LLM_SHORTDESC", os.getenv("USE_LLM_SHORTDESC", "True")).lower() in ("1", "true", "yes")
CHAT_USE_RERANK = os.getenv("CHAT_USE_LLM_RERANK", os.getenv("USE_LLM_RERANK", "False")).lower() in ("1", "true", "yes")
CHAT_USE_INTENT = os.getenv("CHAT_USE_LLM_INTENT", os.getenv("USE_LLM_INTENT", "True")).lower() in ("1", "true", "yes")
CHAT_USE_PROMO = os.getenv("CHAT_USE_LLM_PROMO", os.getenv("USE_LLM_PROMO", "True")).lower() in ("1", "true", "yes")
CHAT_OPENAI_MODEL = os.getenv("CHAT_OPENAI_MODEL", os.getenv("CHAT_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")))

# === 向後相容性：保持舊變數名稱 ===
USE_EXPAND = SEARCH_USE_EXPAND  # 默認使用搜索配置
USE_SHORT = SEARCH_USE_SHORT
USE_RERANK = SEARCH_USE_RERANK
USE_INTENT = SEARCH_USE_INTENT
USE_PROMO = SEARCH_USE_PROMO
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = SEARCH_OPENAI_MODEL
CHAT_MODEL = CHAT_OPENAI_MODEL

# ============================================================
# OpenAI 客戶端快取機制
# ============================================================
_openai_client_cache: Optional[OpenAI] = None
_cached_api_key: Optional[str] = None

# 分類提示詞快取配置
CATEGORY_PROMPT_TTL = int(os.getenv("CATEGORY_PROMPT_TTL", "300"))  # 秒
_CATEGORY_PROMPT_CACHE: Optional[str] = None
_CATEGORY_PROMPT_TS: float = 0.0

def _get_client() -> Optional[OpenAI]:
    """
    獲取 OpenAI 客戶端（帶快取機制）
    
    快取策略：
    - 如果 API key 未變更，返回快取的客戶端
    - 如果 API key 變更或無快取，創建新客戶端
    - 支援執行時期的 API key 更新
    """
    global _openai_client_cache, _cached_api_key
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    # 檢查 API key 狀態
    if not api_key:
        _logger.debug("OPENAI_API_KEY not found in environment")
        return None
    
    if api_key == "your-openai-api-key":
        _logger.debug("OPENAI_API_KEY is placeholder value")
        return None
    
    # 快取命中：API key 未變更且有快取客戶端
    if api_key == _cached_api_key and _openai_client_cache is not None:
        _logger.debug("Using cached OpenAI client")
        return _openai_client_cache
    
    # 創建新客戶端
    try:
        # 只顯示前幾個字符以保護敏感資訊
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        _logger.info(f"Creating new OpenAI client (key: {masked_key})")
        
        client = OpenAI(api_key=api_key)
        
        # 更新快取
        _openai_client_cache = client
        _cached_api_key = api_key
        
        _logger.info("OpenAI client created and cached successfully")
        return client
    
    except Exception as e:
        _logger.error(f"Failed to create OpenAI client: {e}", exc_info=True)
        return None

# 保持向後相容性
_client: Optional[OpenAI] = None  # 將在首次使用時初始化
_CHAT_DF_CACHE: Optional[pd.DataFrame] = None

# === 🆕 分類層級同義詞庫（自動提取）===
_CATEGORY_SYNONYMS_CACHE: Optional[Dict[str, List[str]]] = None
_CATEGORY_WHITELIST_CACHE: Optional[Set[str]] = None


def _normalize_scope_token(text: str) -> str:
    if not text:
        return ""
    folded = re.sub(r"\s+", "", text.lower())
    return folded


def _get_category_whitelist() -> Set[str]:
    global _CATEGORY_WHITELIST_CACHE
    try:
        terms = get_category_terms()
    except Exception as exc:
        _logger.warning("Failed to load category whitelist: %s", exc)
        return set()
    normalized = {_normalize_scope_token(term) for term in terms if term}
    if normalized:
        _CATEGORY_WHITELIST_CACHE = normalized
        return normalized
    return _CATEGORY_WHITELIST_CACHE or set()


def _query_mentions_known_category(query: str, keywords: Optional[List[str]] = None) -> bool:
    """檢查訊息中是否出現白名單分類或其同義詞。"""
    tokens = keywords or _extract_keywords(query)
    meaningful = [
        tok for tok in tokens
        if tok and len(tok) >= 2 and not tok.isdigit() and tok not in CHAT_STOP_WORDS
    ]
    if not meaningful:
        # 沒有足夠語意資訊，視為未知並允許後續處理
        return True

    whitelist = _get_category_whitelist()
    if not whitelist:
        return True

    for token in meaningful:
        normalized = _normalize_scope_token(token)
        if not normalized:
            continue
        if normalized in whitelist:
            return True
        # 子字串比對，例如「米」對應「米類」
        for candidate in whitelist:
            if not candidate:
                continue
            if normalized in candidate or candidate in normalized:
                return True
    return False


def _should_flag_oos(query: str, keywords: List[str], products: List[Dict[str, Any]], *, has_category_context: bool = False) -> bool:
    """是否視為超出販售範圍。當前查詢沒有命中白名單且無分類線索時才觸發。"""
    if has_category_context:
        return False
    return not _query_mentions_known_category(query, keywords)


def _extract_category_synonyms() -> Dict[str, List[str]]:
    """
    從 CSV 自動提取 L1/L2/L3 分類層級，生成同義詞對應表。
    快取結果以避免重複計算。
    
    Returns:
        {
            "食品": ["食品", "飲食", "食材"],
            "調味品": ["調味品", "調味料", "醬料"],
            ...
        }
    """
    global _CATEGORY_SYNONYMS_CACHE
    
    if _CATEGORY_SYNONYMS_CACHE is not None:
        return _CATEGORY_SYNONYMS_CACHE
    
    synonyms: Dict[str, set[str]] = {}
    
    try:
        df = load_data(str(DEFAULT_DATA_PATH))
        if df.empty:
            _logger.warning("CSV is empty, skipping category extraction")
            _CATEGORY_SYNONYMS_CACHE = {}
            return _CATEGORY_SYNONYMS_CACHE
        
        # 提取 L1/L2/L3 欄位（支援中英文名稱）
        for level_col in ["大分類名稱", "CateName_L1", "L1", "category_l1"]:
            if level_col in df.columns:
                for cat in df[level_col].dropna().unique():
                    cat_str = str(cat).strip()
                    if cat_str:
                        if cat_str not in synonyms:
                            synonyms[cat_str] = set()
                        synonyms[cat_str].add(cat_str)
                break
        
        for level_col in ["中分類名稱", "CateName_L2", "L2", "category_l2"]:
            if level_col in df.columns:
                for cat in df[level_col].dropna().unique():
                    cat_str = str(cat).strip()
                    if cat_str:
                        if cat_str not in synonyms:
                            synonyms[cat_str] = set()
                        synonyms[cat_str].add(cat_str)
                break
        
        for level_col in ["小分類名稱", "CateName_L3", "L3", "category_l3"]:
            if level_col in df.columns:
                for cat in df[level_col].dropna().unique():
                    cat_str = str(cat).strip()
                    if cat_str:
                        if cat_str not in synonyms:
                            synonyms[cat_str] = set()
                        synonyms[cat_str].add(cat_str)
                break
        
        # 轉換 set 為 list
        result = {k: sorted(list(v)) for k, v in synonyms.items()}
        _CATEGORY_SYNONYMS_CACHE = result
        
        _logger.info("Extracted %d category synonyms from CSV", len(result))
        return result
        
    except Exception as e:
        _logger.error("Failed to extract category synonyms: %s", e)
        _CATEGORY_SYNONYMS_CACHE = {}
        return {}


# 模組載入時初始化分類同義詞
_CATEGORY_SYNONYMS_CACHE = _extract_category_synonyms()


# === 🆕 重要分類範例 (自動生成 + 手動優化) ===
# 用於 LLM Prompt,幫助 LLM 更準確識別商品分類
# 優先顯示高頻分類和容易誤判的分類
IMPORTANT_CATEGORY_EXAMPLES = {
    "常溫食品": {
        "五穀/豆類/米麵/乾貨": {
            # ⭐ 重點分類: 烹調食材 = 菇類、食材類
            # 木茸、香菇等容易被 LLM 誤判,需特別標註
            "烹調食材": ["木茸", "香菇", "黑木耳", "白木耳", "海帶芽"],
            "米類": ["白米", "糙米", "香米", "五色十穀米"],
            "麵條/冬粉": ["意麵", "雞絲麵", "十穀Q麵", "米粉"],
            "燕麥/五穀/玉米": ["奇亞籽", "紅藜麥", "黃豆", "綠豆"],
        },
        "調味/醬料/醬菜": {
            # ⭐ 高頻分類 (78件商品)
            "醬油/味噌/糖": ["昆布醬油", "黑豆蔭油", "素蠔油", "海鹽", "糯米醋"],
            "沾/拌醬": ["全素美乃滋", "芥末醬", "蕃茄醬"],
            "辛香料": ["白胡椒粉", "肉桂粉", "黑胡椒粉"],
        },
        "食用油": {
            "植物油": ["苦茶油", "南瓜籽油", "橄欖油", "葵花油"],
        },
        "沖調/飲品/咖啡/早餐": {
            "茶葉/茶包": ["玄米綠茶", "國寶茶", "玫瑰花茶"],
            "咖啡": ["即溶咖啡", "黑咖啡", "冰萃黑咖啡"],
            "早餐麥片": ["燕麥片", "即食燕麥片", "覆盆莓麥片"],
        },
        "休閒食品": {
            "餅乾/脆果": ["胡椒餅", "沙奇瑪", "鍋粑"],
            "堅果": ["甜杏仁", "南瓜子", "腰果"],
            "果乾": ["黑棗", "蔓越莓乾"],
        },
    },
    "包包配件": {
        "女用皮包": {
            "側背包": ["斜背包", "肩背包"],
            "手提包": ["托特包", "手提袋"],
            "後背包": ["雙肩包", "輕量後背包"],
        },
        "男用配件": {
            "休閒包": ["牛皮包", "胸包"],
            "皮夾": ["短夾", "四夾", "六夾"],
        },
    },
    "戶外與運動用品": {
        "運動鞋/戶外鞋": {
            "籃球鞋": ["籃球鞋", "運動鞋"],
            "慢跑鞋": ["跑鞋", "運動慢跑鞋"],
            "登山鞋": ["登山靴", "健走鞋", "防水登山鞋"],
        },
    },
}


CHAT_STOP_WORDS: set[str] = {
    "我",
    "要",
    "想",
    "想買",
    "想購買",
    "可以",
    "請",
    "幫",
    "嗎",
    "呢",
    "有",
    "的",
    "是",
    "想要",
    "品",
    "分",
    "幾",
    "大",
    "類",
    "商品",
    "調味品",
    "廚房",
    "哪些",
    "什麼",
    "東西",
    "賣",
    "我們",
    "你們",
    "主要",
    "購",
    "買",
    "漂亮",
}

CHAT_CATEGORY_TOPICS: Dict[str, List[str]] = {
    "健康穀物類": ["燕麥/五穀/玉米", "早餐麥片", "米類"],
    "醬料與調味品": ["醬油/味噌/糖", "沾/拌醬", "植物油", "醬菜"],
    "餅乾與零食類": ["餅乾/脆果", "糖果/果凍/豆乾", "堅果"],
    "飲品類": ["沖調飲品", "飲品", "茶葉/茶包", "養身飲品", "花果茶/草本飲品"],
    "保健食品類": ["養身飲品", "養身食品"],
    "生活用品類": ["籃球鞋", "慢跑鞋", "登山鞋", "經典手提包", "經典側/斜背包"],
}

STRUCTURED_QUERY_RULES: Tuple[Dict[str, Any], ...] = (
    {
        "keywords": ["背包", "女包", "女用背包", "女用", "包包", "包款", "肩背包", "後背包", "雙肩包", "手提包", "隨身包"],
        "category": "包",
        "must": ["背包", "包"],
        "excluded": ["湯", "燉包", "茶", "醬", "調味", "湯包"],
    },
)

HEALTH_KEYWORDS: Tuple[str, ...] = (
    "健康", "功效", "好處", "益處", "副作用", "對身體", "營養", "保健", "影響"
)

USAGE_KEYWORDS: Tuple[str, ...] = (
    "怎麼用", "怎麼吃", "使用方法", "用法", "步驟", "料理", "吃法", "用量", "使用方式"
)

FEMALE_MARKERS: Tuple[str, ...] = (
    "女", "女性", "女用", "女士", "女孩", "女款", "lady", "woman", "女性款"
)

STRUCTURED_QUERY_RULES: Tuple[Dict[str, Any], ...] = (
    {
        "keywords": ["背包", "女包", "女用背包", "女用", "包包", "包款", "肩背包", "後背包", "雙肩包", "手提包", "隨身包"],
        "category": "包",
        "must": ["背包", "包"],
        "female_terms": FEMALE_MARKERS,
        "excluded": ["湯", "燉包", "茶", "醬", "麵", "調味", "湯包"],
    },
)

GENERAL_OVERVIEW_TRIGGERS: tuple[str, ...] = (
    "賣什麼",
    "有什麼",
    "有哪些",
    "賣些什麼",
    "商品有哪些",
    "有哪些商品",
    "賣哪些",
    "主要商品",
    "商品類別",
    "商品分類",
    "賣什麼東西",
)

# 進階意圖識別：區分資訊諮詢 vs 商品查詢
INFORMATION_INTENT_PATTERNS = {
    "health_info": [
        "對健康", "有什麼幫助", "功效", "好處", "營養價值", "健康效果", 
        "有益", "有害", "副作用", "注意事項", "營養成分", "保健效果"
    ],
    "usage_guide": [
        "怎麼用", "如何使用", "用法", "使用方法", "怎麼吃", "怎麼喝",
        "用量", "用時", "什麼時候用", "一天幾次", "使用頻率", "使用時機",
        "一天用多少", "每天用多少", "用多少"
    ],
    "knowledge": [
        "是什麼", "成分", "原理", "為什麼", "原因", "機制", 
        "製作過程", "來源", "特色", "特點", "原料"
    ],
    "comparison": [
        "比較", "差異", "哪個好", "推薦哪個", "區別", "不同", 
        "優缺點", "vs", "相比", "對比", "差別", "有什麼差"
    ]
}

EVENT_INTENT_PATTERNS = [
    "園遊會",
    "市集",
    "擺攤",
    "家庭日",
    "派對",
    "生日派對",
    "活動建議",
    "活動要準備",
    "活動餐飲",
    "公司活動",
    "親子活動",
    "活動要買",
]

# 明確購買意圖關鍵詞
PURCHASE_INTENT_PATTERNS = [
    "我要買", "想買", "購買", "下單", "訂購", "有賣", 
    "價格", "多少錢", "便宜", "特價", "優惠", "商品",
    # 生日聚會和活動相關的購買意圖
    "幫忙準備", "準備", "需要準備", "要準備", "辦聚會", "辦活動",
    "生日聚會", "聚會", "慶祝", "活動", "需要一些", "來一些"
]

# 商品推薦諮詢（介於資訊和購買之間）
RECOMMENDATION_PATTERNS = [
    "推薦", "推薦商品", "推薦好用", "哪個好", "建議", "適合"
]

# 🆕 公司資料查詢意圖關鍵詞
COMPANY_INFO_PATTERNS = {
    "contact": [
        "電話", "聯絡", "客服", "聯繫", "聯絡方式", "聯絡電話",
        "怎麼聯絡", "怎麼聯繫", "如何聯繫", "找你們", "打電話",
        "地址", "位置", "在哪", "在哪裡", "怎麼去", "怎麼找",
        "官網", "網站", "網址", "線上", "email", "信箱", "mail"
    ],
    "service": [
        "服務", "服務項目", "業務", "業務範圍", "提供什麼服務",
        "做什麼", "做什麼的", "你們是做什麼的", "主要業務",
        "提供", "能做", "可以做", "有哪些服務", "服務內容",
        "專長", "專業", "技術", "能力", "功能", "項目"
    ],
    "company": [
        "公司", "公司介紹", "你們公司", "你們是", "關於你們",
        "公司背景", "背景", "介紹", "關於", "公司資訊",
        "成立", "歷史", "多久", "什麼時候", "幾年", "經驗"
    ],
    "hours": [
        "營業時間", "上班時間", "服務時間", "幾點", "什麼時候",
        "時間", "週末", "假日", "休息", "營業", "開門", "關門"
    ],
    "promotion": [
        "優惠", "促銷", "活動", "折扣", "特價", "特惠",
        "優惠券", "折扣券", "優惠碼", "現在有什麼", "有什麼活動"
    ]
}

# 🎯 上下文產品詢問檢測 - 混合智慧快速版
CONTEXT_INQUIRY_HIGH_CONFIDENCE = [
    "你有賣", "你們有賣", "店裡有", "有這個商品嗎", "有這個產品嗎", 
    "可以買到嗎", "哪裡買", "怎麼購買", "能買到", "有在賣",
    "我要買", "我要購買", "想買", "想購買", "要訂購", "我需要",
    "購買這個", "買這個", "要這個", "訂購這個"
]

CONTEXT_INQUIRY_MEDIUM_CONFIDENCE = [
    "建議的", "推薦的", "剛才說的", "上面提到的", "這個產品", 
    "這個商品", "那個", "這種", "剛提到", "你說的"
]

# 核心產品關鍵詞庫（基於資料庫熱門產品）
CORE_PRODUCT_KEYWORDS = [
    "椰子油", "橄欖油", "堅果", "蜂蜜", "燕麥", "奇亞籽", "藜麥", 
    "維生素", "膠原蛋白", "益生菌", "蛋白粉", "魚油", "酵素",
    "綠茶", "咖啡", "巧克力", "餅乾", "麵條", "醬料"
]

# 房產關鍵詞（僅用於聊天提示詞切換，不改商品/訂單邏輯）
REAL_ESTATE_KEYWORDS = [
    "磐鈺建設",
    "磐鈺",
    "磐鈺草間漫漫",
    "磐鈺雲華",
    "磐鈺雲詠",
    "極致輕寓2房",
    "光合雅寓3房",
    "市景菁英3房",
    "景觀大戶4房",
    "樂樂璵里",
    "協奏輕盈3房",
]

CONFIRMATION_TERMS: Set[str] = {
    "要",
    "好",
    "好的",
    "好啊",
    "ok",
    "okay",
    "ok的",
    "好喔",
    "好呀",
    "需要",
    "需要的",
    "需要啊",
    "需要喔",
    "要的",
    "好呢",
    "ok喔",
    "好哦",
    "ok啦",
    "yes",
    "y",
    "sure",
    "show",
    "pls",
    "please",
    "go",
    "goahead",
    "給我看",
    "顯示",
    "幫我看",
    "幫我顯示",
    "幫我開",
    "麻煩",
    "麻煩你",
    "看一下",
    "看",
    "showme",
}

CSV_ONLY_SYSTEM_PROMPT = """
你是「智慧客服」。你只能使用提供的商品清單(名稱/ID/分類/價格/特價/圖片/連結/描述)回覆。
步驟：
1) 解析使用者需求，對齊最多8筆商品（務必附 GoodIden 與名稱）。
2) 若有候選：用簡短中文回覆「找到 N 款…」，尾句加：需要我顯示詳細介紹與圖片嗎？
3) 在回覆訊息最末端輸出隱藏 JSON（不要讓用戶看到）：
{"intent":"product_align","items":[{"id":"<GoodIden>","name":"<商品名稱>"}], "need_confirm_show_details": true}
4) 若找不到候選：請用禮貌語氣請客戶提供價位、款式或顏色。禁止臆測或捏造商品。
""".strip()

STATIC_CATEGORY_PROMPT = """
你是商品分類專家，請精確識別用戶查詢中的商品分類層級。

【識別原則】
1. 商品核心名詞優先：提取查詢中的核心商品名
2. 忽略修飾詞：「台灣」、「日曬」、「有機」等為修飾詞，不影響分類
3. 食品材料歸常溫食品；不確定時給出最相關層級，至少識別 L1

【輸出格式】
{
  "category_hierarchy": {"L1": "...", "L2": "...", "L3": "..."},
  "confidence": {"L1": 0.0-1.0, "L2": 0.0-1.0, "L3": 0.0-1.0},
  "matching_keywords": [...]
}
""".strip()


def _safe_int_from_any(val: Any) -> Optional[int]:
    try:
        return int(str(val).strip())
    except Exception:
        return None


def _build_category_tree(categories: List[Dict[str, Any]]) -> Dict[str, Any]:
    tree: Dict[str, Any] = {}
    if not categories:
        return tree
    for row in categories:
        l1 = str(row.get("L1") or "").strip()
        l2 = str(row.get("L2") or "").strip()
        l3 = str(row.get("L3") or "").strip()
        order = _safe_int_from_any(row.get("DisplayOrder"))
        if not l1:
            continue
        node1 = tree.setdefault(l1, {"order": order, "children": {}})
        if l2:
            node2 = node1["children"].setdefault(l2, {"order": order, "children": []})
            if l3:
                node2["children"].append({"name": l3, "order": order})
    return tree


def _guess_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for cand in candidates:
        if cand in df.columns:
            return cand
    return None


def _get_product_examples(df: Optional[pd.DataFrame], l3: str, limit: int = 3) -> List[str]:
    if df is None or df.empty or not l3:
        return []
    l3_col = _guess_column(df, ["CateName_L3", "小分類名稱", "L3", "分類名稱"])
    if not l3_col:
        return []
    subset = df[df[l3_col].astype(str).str.strip() == l3]
    if subset.empty:
        return []
    name_col = _guess_column(subset, ["商品名稱", "Name", "name", "品名"])
    if not name_col:
        return []
    names = []
    for raw in subset[name_col].astype(str).fillna(""):
        cleaned = raw.strip()
        if cleaned:
            names.append(cleaned[:30])
        if len(names) >= limit:
            break
    return names


# === 🆕 分類層級識別提示詞 ===
def _build_category_hierarchy_prompt() -> str:
    """
    動態從分類/商品資料構建提示詞；失敗時回退靜態版本。
    """
    try:
        categories = get_all_categories()
        if not categories:
            _logger.warning("category prompt: categories empty, fallback to static")
            return STATIC_CATEGORY_PROMPT
        tree = _build_category_tree(categories)
        products_df: Optional[pd.DataFrame] = None
        try:
            products_df = load_data(DEFAULT_DATA_PATH)
        except Exception as exc:
            _logger.warning("category prompt: load products failed: %s", exc)

        def _order_key(node):
            order = _safe_int_from_any(node.get("order"))
            return (order if order is not None else 10_000_000)

        l1_items = sorted(
            [{"name": name, **node} for name, node in tree.items()],
            key=lambda x: (_order_key(x), x["name"])
        )

        parts: List[str] = []
        parts.append("你是商品分類專家，以下是目前系統的分類與代表商品：")
        l1_cap = int(os.getenv("CATEGORY_PROMPT_L1_CAP", "50"))
        l2_cap = int(os.getenv("CATEGORY_PROMPT_L2_CAP", "100"))
        l3_cap_per_l2 = int(os.getenv("CATEGORY_PROMPT_L3_CAP", "50"))
        example_limit = int(os.getenv("CATEGORY_PROMPT_EXAMPLE_LIMIT", "3"))
        l1_count = 0
        l2_count_total = 0
        l3_count_total = 0
        for l1 in l1_items:
            if l1_count >= l1_cap:
                parts.append("  …(其他 L1 省略以控制長度)")
                break
            parts.append(f"\n📦 {l1['name']}:")
            l2_children = l1.get("children") or {}
            l2_items = sorted(
                [{"name": name, **node} for name, node in l2_children.items()],
                key=lambda x: (_order_key(x), x["name"])
            )
            l2_local = 0
            for l2 in l2_items:
                if l2_count_total >= l2_cap:
                    parts.append("  • …(其他 L2 省略)")
                    break
                l2_count_total += 1
                l2_local += 1
                parts.append(f"  • {l2['name']}:")
                l3_list = l2.get("children") or []
                l3_items = sorted(
                    l3_list,
                    key=lambda x: (_order_key(x), x.get("name", ""))
                )
                l3_local = 0
                for l3 in l3_items:
                    if l3_local >= l3_cap_per_l2:
                        parts.append("    - …(其他小分類省略)")
                        break
                    l3_local += 1
                    l3_count_total += 1
                    l3_name = l3.get("name") or ""
                    examples = _get_product_examples(products_df, l3_name, limit=example_limit)
                    if examples:
                        parts.append(f"    - {l3_name}: {', '.join(examples)}")
                    else:
                        parts.append(f"    - {l3_name}")
            l1_count += 1

        parts.extend([
            "",
            "【識別原則】",
            "1. 商品核心名詞優先：提取查詢中的核心商品名",
            "2. 忽略修飾詞：「台灣」「日曬」「有機」等為修飾詞",
            "3. 食品材料歸常溫食品；不確定時至少識別 L1 大分類",
            "",
            "【輸出格式】",
            '{ "category_hierarchy": {"L1": "...", "L2": "...", "L3": "..."},',
            '  "confidence": {"L1": 0.0-1.0, "L2": 0.0-1.0, "L3": 0.0-1.0},',
            '  "matching_keywords": [...] }',
        ])
        _logger.info(
            "category prompt built: L1=%d (cap=%d) L2=%d (cap=%d) L3=%d (per L2 cap=%d) examples=%d",
            l1_count, l1_cap, l2_count_total, l2_cap, l3_count_total, l3_cap_per_l2, example_limit,
        )
        return "\n".join(parts)
    except Exception as exc:
        _logger.warning("category prompt fallback static due to: %s", exc)
        return STATIC_CATEGORY_PROMPT


def clear_category_prompt_cache(force_rebuild: bool = False) -> None:
    """
    清除分類提示詞快取；選擇性立即重建。
    """
    global _CATEGORY_PROMPT_CACHE, _CATEGORY_PROMPT_TS
    with _CATEGORY_PROMPT_LOCK:
        _CATEGORY_PROMPT_CACHE = None
        _CATEGORY_PROMPT_TS = 0.0
        if force_rebuild:
            try:
                _CATEGORY_PROMPT_CACHE = _build_category_hierarchy_prompt()
                _CATEGORY_PROMPT_TS = time.time()
            except Exception as exc:
                _logger.warning("category prompt rebuild failed after clear: %s", exc)
                _CATEGORY_PROMPT_CACHE = None
                _CATEGORY_PROMPT_TS = 0.0


def _get_category_hierarchy_prompt(force: bool = False) -> str:
    """
    具快取的分類提示詞取得；失敗時回退靜態版且不污染快取。
    """
    global _CATEGORY_PROMPT_CACHE, _CATEGORY_PROMPT_TS
    now = time.time()
    with _CATEGORY_PROMPT_LOCK:
        if not force and _CATEGORY_PROMPT_CACHE and (now - _CATEGORY_PROMPT_TS) < CATEGORY_PROMPT_TTL:
            return _CATEGORY_PROMPT_CACHE
        try:
            prompt = _build_category_hierarchy_prompt()
            _CATEGORY_PROMPT_CACHE = prompt
            _CATEGORY_PROMPT_TS = now
            return prompt
        except Exception as exc:
            _logger.warning("category prompt build failed: %s", exc)
            # 保留舊快取，不污染
            return _CATEGORY_PROMPT_CACHE or STATIC_CATEGORY_PROMPT

SUGGEST_PROMPT_SUFFIX = "也可輸入 1=原建議、2=特價關聯、3=智慧搭配。"


def classify_recommendation_type(user_text: str) -> int:
    system_prompt = """
    你是一位智能行銷助理，負責分析顧客詢問的語氣與意圖。
    請根據以下規則，判斷應主推哪類商品：
    1️⃣ 若顧客只問某商品、品牌、型號 → 回傳 1。
    2️⃣ 若顧客提到優惠、折扣、便宜、特價、促銷 → 回傳 2。
    3️⃣ 若顧客提到送禮、搭配、配餐、組合、一起買、適合搭配 → 回傳 3。
    只輸出數字 1、2 或 3，不加文字。
    """.strip()
    reply = _call_chat(user_text, system=system_prompt, model=CHAT_OPENAI_MODEL, max_tokens=4)
    try:
        value = int((reply or "").strip())
        return value if value in (1, 2, 3) else 1
    except Exception:
        return 1


FREESTYLE_PLAN_PROMPT = """
你是「智慧採購顧問」。你可以自由規劃顧客的採購方案（例如：聚餐、送禮、預算控管）。
限制：
1. 你最終列出的每一項商品，必須是清單內存在的商品（系統會驗證）。
2. 回覆結尾一定要附上隱藏 JSON（不要讓顧客看到），格式：
{"intent":"bundle_plan","items":[{"name":"商品名稱","id":"(若知道)","quantity":2,"note":"理由"}], "budget":2000}
3. 若你無法滿足需求，JSON 的 items 請給空陣列。
""".strip()

BUNDLE_JSON_RE = re.compile(r"\{.*?\"intent\"\s*:\s*\"bundle_plan\".*?\}\s*$", re.S)


def llm_generate_plan(user_message: str, catalog_excerpt: str) -> Dict[str, Any]:
    system_prompt = f"{FREESTYLE_PLAN_PROMPT}\n\n以下是可用商品清單摘錄：\n{catalog_excerpt.strip()}"
    reply_text = _call_chat(user_message, system=system_prompt, model=CHAT_OPENAI_MODEL, max_tokens=500)
    if not reply_text:
        return {"reply_text": "目前沒有找到合適的商品方案，請提供更具體的需求。", "plan": {"items": []}}
    plan = {"items": []}
    text = reply_text.strip()
    match = BUNDLE_JSON_RE.search(text)
    if match:
        snippet = match.group(0)
        try:
            plan = json.loads(snippet)
        except Exception:
            plan = {"items": []}
        text = BUNDLE_JSON_RE.sub("", text).rstrip()
    return {"reply_text": text, "plan": plan}


def _get_chat_df() -> Optional[pd.DataFrame]:
    global _CHAT_DF_CACHE
    if _CHAT_DF_CACHE is None:
        try:
            _CHAT_DF_CACHE = load_data(str(DEFAULT_DATA_PATH))
        except Exception as exc:
            _logger.exception("failed to load chat dataframe: %s", exc)
            _CHAT_DF_CACHE = None
    return _CHAT_DF_CACHE


def _normalize_text_for_match(text: Any) -> str:
    return re.sub(r"[\s\-_/]+", "", str(text or "").lower())


def _strip_filler_phrases(text: str) -> str:
    cleaned = re.sub(r"[?？!！。，,.、\s]", "", (text or "").lower())
    cleaned = re.sub(r"^(請問|想找|想要|需要|可否|能否|可以|煩請)+", "", cleaned)
    cleaned = re.sub(r"^(有沒有|有賣)", "", cleaned)
    cleaned = re.sub(r"(嗎|呢|嘛|好嗎|嗎呢|嗎嘛)$", "", cleaned)
    return cleaned


def _extract_core_terms(keywords: List[str]) -> List[str]:
    return [
        kw.lower()
        for kw in keywords
        if kw and kw.lower() not in CHAT_STOP_WORDS and len(kw) >= 2
    ]


def _dedupe_products(items: List[Dict[str, Any]], limit: Optional[int] = None) -> List[Dict[str, Any]]:
    seen: Set[str] = set()
    result: List[Dict[str, Any]] = []
    for item in items:
        pid = (
            str(item.get("GoodIden") or item.get("商品編號") or item.get("id") or "")
            .strip()
        )
        key = pid or str(item.get("Name") or item.get("name") or "").strip()
        if not key:
            continue
        key_lower = key.lower()
        if key_lower in seen:
            continue
        seen.add(key_lower)
        result.append(item)
        if limit and len(result) >= limit:
            break
    return result


def _build_alignment_items(records: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    seen: Set[str] = set()
    for record in records:
        if record is None:
            continue
        # pandas Series support
        if hasattr(record, "to_dict"):
            record = record.to_dict()
        good_id = str(record.get("GoodIden") or record.get("商品編號") or "").strip()
        name = str(record.get("Name") or record.get("商品名稱") or "").strip()
        if not good_id:
            continue
        key = good_id.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append({"id": good_id, "name": name})
        if len(items) >= 8:
            break
    return items


def _is_confirmation_message(message: str) -> bool:
    if not message:
        return False
    lowered = message.lower()
    tokens = [tok for tok in re.findall(r"[a-zA-Z]+|[\u4e00-\u9fff]+", lowered) if tok]
    if tokens and all(tok in CONFIRMATION_TERMS for tok in tokens):
        return True
    normalized = re.sub(r"[\s\W_]+", "", lowered)
    return normalized in CONFIRMATION_TERMS


def _extract_alignment_from_history(history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not history:
        return None
    for item in reversed(history):
        if not isinstance(item, dict):
            continue
        if item.get("role") != "assistant":
            continue
        alignment = item.get("alignment")
        if not isinstance(alignment, dict):
            continue
        if alignment.get("intent") != "product_align":
            continue
        items = alignment.get("items")
        if not isinstance(items, list):
            continue
        filtered = []
        for entry in items:
            if not isinstance(entry, dict):
                continue
            good_id = str(entry.get("id") or "").strip()
            name = str(entry.get("name") or "").strip()
            if not good_id:
                continue
            filtered.append({"id": good_id, "name": name})
        if filtered:
            return {
                "items": filtered,
                "need_confirm": bool(alignment.get("need_confirm_show_details")),
                "reason": alignment.get("reason") or "",
            }
    return None

def _derive_structured_filters(query: str, keywords: List[str]) -> Dict[str, Any]:
    lowered_query = (query or "").lower()
    filters: Dict[str, Any] = {}
    
    # 處理類別和關鍵字過濾
    for rule in STRUCTURED_QUERY_RULES:
        rule_keywords = rule.get("keywords") or []
        if any(term.lower() in lowered_query for term in rule_keywords):
            filters["category_filter"] = rule.get("category")
            must: List[str] = []
            must.extend(rule.get("must") or [])
            filters["must_have_keywords"] = list(dict.fromkeys([kw for kw in must if kw]))
            excluded = rule.get("excluded") or []
            if excluded:
                filters["excluded_keywords"] = list(dict.fromkeys(excluded))
            break
    
    # 🆕 處理價格/預算過濾
    try:
        from utils.simple_extract import extract_budget_and_cats
        budget_info = extract_budget_and_cats(query)
        
        if budget_info.get("budget_info"):
            budget_data = budget_info["budget_info"]
            price_filter = {}
            
            if budget_data.get("min_price"):
                price_filter["min_price"] = budget_data["min_price"]
            if budget_data.get("max_price"):
                price_filter["max_price"] = budget_data["max_price"]
                
            if price_filter:
                filters["price_filter"] = price_filter
                _logger.debug("Price filter detected: %s", price_filter)
                
    except ImportError as e:
        _logger.warning("Could not import budget extraction: %s", e)
    except Exception as e:
        _logger.warning("Budget extraction failed: %s", e)
    
    return filters


# 食品分類清單 - 用於防止非食品查詢混入食品
FOOD_CATEGORIES = {
    "即食粥/麵", "咖啡", "沖調飲品", "燕麥/五穀/玉米", 
    "米類", "花果茶/草本飲品", "茶葉/茶包", "飲品", 
    "養身食品", "養身飲品",
}
FOOD_CATEGORIES_LOWER = {name.lower() for name in FOOD_CATEGORIES}

def _is_food_item(item: Dict[str, Any]) -> bool:
    """檢查商品是否為食品"""
    parts = [
        FieldAccessor.get_category_l1(item),
        FieldAccessor.get_category_l2(item),
        FieldAccessor.get_category_l3(item),
        FieldAccessor.get_category(item),
    ]
    haystack = " ".join([str(part).strip().lower() for part in parts if part]).strip()
    if not haystack:
        return False
    return any(food in haystack for food in FOOD_CATEGORIES_LOWER)

def _is_food_query(query: str, keywords: List[str]) -> bool:
    """判斷查詢是否明確要求食品"""
    query_lower = query.lower()
    keywords_lower = [kw.lower() for kw in keywords]
    
    food_keywords = {"食品", "飲品", "咖啡", "茶", "米", "粥", "燕麥", "五穀", "玉米", "沖調"}
    
    # 檢查查詢中是否包含食品關鍵詞
    for kw in food_keywords:
        if kw in query_lower:
            return True
    
    # 檢查提取的關鍵詞中是否包含食品相關詞彙
    for kw in keywords_lower:
        if any(f in kw for f in food_keywords):
            return True
    
    return False

def _apply_structured_filters(records: List[Dict[str, Any]], filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not records or not filters:
        return records
    category_filter = (filters.get("category_filter") or "").lower()
    must_keywords = [kw.lower() for kw in filters.get("must_have_keywords") or [] if kw]
    excluded_keywords = [kw.lower() for kw in filters.get("excluded_keywords") or [] if kw]
    price_filter = filters.get("price_filter") or {}
    min_price = price_filter.get("min_price")
    max_price = price_filter.get("max_price")
    filtered: List[Dict[str, Any]] = []
    for item in records:
        # 統一使用 FieldAccessor 提取欄位，確保一致的多別名支援
        name = FieldAccessor.get_name(item).lower()
        l1_cat = FieldAccessor.get_category_l1(item).lower()
        l2_cat = FieldAccessor.get_category_l2(item).lower()
        l3_cat = FieldAccessor.get_category_l3(item).lower()
        description = FieldAccessor.get_description(item).lower()
        haystack = " ".join([name, l1_cat, l2_cat, l3_cat, description]).lower()
        if category_filter and category_filter not in haystack:
            continue
        if must_keywords and not all(kw in haystack for kw in must_keywords):
            continue
        if excluded_keywords and any(kw in haystack for kw in excluded_keywords):
            continue
        if price_filter:
            special_price = FieldAccessor.get_special_price(item)
            regular_price = FieldAccessor.get_price(item)
            effective_price = special_price if special_price and special_price > 0 else regular_price
            if not effective_price or effective_price <= 0:
                continue
            if min_price is not None and effective_price < min_price:
                continue
            if max_price is not None and effective_price > max_price:
                continue
        filtered.append(item)
    return filtered


# === 🆕 分類層級搜尋函數 ===
def _search_by_category_hierarchy(
    df: pd.DataFrame,
    hierarchy: Dict[str, str],
    topn: int = 10,
) -> List[Dict[str, Any]]:
    """
    根據分類層級 (L1/L2/L3) 進行多層過濾搜尋。
    
    Args:
        df: 商品資料集
        hierarchy: {L1: "", L2: "", L3: ""} 分類層級
        topn: 返回的商品數量上限
    
    Returns:
        搜尋結果，包含 matched_levels 和 hierarchy_score 標記
    """
    if df is None or df.empty or not hierarchy:
        return []
    
    # 提取非空的分類層級
    l1 = str(hierarchy.get("L1", "")).strip()
    l2 = str(hierarchy.get("L2", "")).strip()
    l3 = str(hierarchy.get("L3", "")).strip()
    
    if not (l1 or l2 or l3):
        return []
    
    working = df.copy()
    matched_levels = []
    
    # 🔍 層級過濾：從大到小
    if l1:
        # 過濾 L1（支援中英文欄位名）
        for col in ["CateName_L1", "大分類名稱", "L1"]:
            if col in working.columns:
                mask = working[col].astype(str).str.contains(l1, na=False, regex=False)
                working = working[mask]
                if not working.empty:
                    matched_levels.append("L1")
                break
    
    if l2 and not working.empty:
        # 過濾 L2
        for col in ["CateName_L2", "中分類名稱", "L2"]:
            if col in working.columns:
                mask = working[col].astype(str).str.contains(l2, na=False, regex=False)
                working = working[mask]
                if not working.empty:
                    matched_levels.append("L2")
                break
    
    if l3 and not working.empty:
        # 過濾 L3
        for col in ["CateName_L3", "小分類名稱", "L3"]:
            if col in working.columns:
                mask = working[col].astype(str).str.contains(l3, na=False, regex=False)
                working = working[mask]
                if not working.empty:
                    matched_levels.append("L3")
                break
    
    if working.empty:
        return []
    
    # 轉換為字典格式並標記層級匹配信息
    result = working.head(topn).to_dict(orient="records")
    
    # 🆕 為每個結果添加層級匹配信息
    hierarchy_score = len(matched_levels) * 3  # 每個匹配層級得 3 分
    for item in result:
        item["matched_levels"] = matched_levels
        item["hierarchy_score"] = hierarchy_score
    
    _logger.info("Hierarchy search matched %d products with levels %s", len(result), matched_levels)
    return result


def _search_products_for_chat(
    query: str, keywords: List[str], topn: int = 5, filters: Optional[Dict[str, Any]] = None,
    hierarchy: Optional[Dict[str, str]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    result = {"exact": [], "fuzzy": []}
    if not query:
        return result
    try:
        df = _get_chat_df()
        if df is None or df.empty:
            return result

        # 🎯 優化: 使用分類索引加速搜尋 (Phase 1 優化)
        # 性能: 70ms → 2ms (35 倍改進) 對於分類過濾層
        if hierarchy and any(hierarchy.get(k) for k in ["L1", "L2", "L3"]):
            try:
                # 優先使用優化版搜尋 (利用分類索引 O(1) 查詢)
                hierarchy_results, _ = search_products_with_hierarchy(
                    df,
                    query=query,
                    hierarchy=hierarchy,
                    topn=topn * 2
                )
                if hierarchy_results:
                    result["exact"] = hierarchy_results[:topn]
                    # 若分類搜尋結果充足，直接返回
                    if len(result["exact"]) >= topn:
                        _logger.info("Optimized hierarchy search returned %d products", len(result["exact"]))
                        return result
                    # 否則繼續進行補充搜尋
            except Exception as e:
                _logger.debug("Category index search failed, fallback to baseline: %s", e)
                # 降級到原始分類搜尋
                hierarchy_results = _search_by_category_hierarchy(df, hierarchy, topn=topn * 2)
                if hierarchy_results:
                    result["exact"] = hierarchy_results[:topn]
                    if len(result["exact"]) >= topn:
                        return result

        fuzzy_records, _ = search_products(
            df,
            query,
            topn=topn,
            sort_price=False,
        )
        filtered_fuzzy = _apply_structured_filters(fuzzy_records or [], filters)

        # 若結果過少，額外使用強化搜尋補齊
        fallback_limit = max(topn * 2, 12)
        needs_fallback = len(filtered_fuzzy) < topn
        strict_candidates: List[Dict[str, Any]] = []
        if needs_fallback or (filters and not filtered_fuzzy):
            try:
                from search_ext_goods_1024001 import search_products_strict
                strict_candidates = search_products_strict(query=query, limit=fallback_limit, filters=filters) or []
            except Exception:
                strict_candidates = []

        if strict_candidates:
            merged_candidates = (filtered_fuzzy or []) + strict_candidates
            filtered_fuzzy = _dedupe_products(merged_candidates, fallback_limit)

        # 🔧 食品防護：確保非食品查詢不會混入食品
        # 如果查詢不是明確要求食品，則過濾掉所有食品
        if not _is_food_query(query, keywords):
            filtered_fuzzy = [item for item in filtered_fuzzy if not _is_food_item(item)]

        result["fuzzy"] = filtered_fuzzy

        core_phrase = _strip_filler_phrases(query)
        significant_keywords = _extract_core_terms(keywords)
        if not core_phrase and not significant_keywords:
            return result

        exact_matches: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            name = row.get("Name") or row.get("商品名稱") or ""
            brand = row.get("BRAND_Name") or row.get("品牌") or ""
            normalized_name = _normalize_text_for_match(name)
            normalized_brand = _normalize_text_for_match(brand)
            matched = False
            if core_phrase and core_phrase in normalized_name:
                matched = True
            elif core_phrase and core_phrase in normalized_brand:
                matched = True
            elif significant_keywords:
                if all(kw in normalized_name for kw in significant_keywords):
                    matched = True
                elif normalized_brand and any(kw in normalized_brand for kw in significant_keywords):
                    matched = True
            if matched:
                exact_matches.append(row.to_dict())
        if exact_matches:
            deduped_exact = _dedupe_products(exact_matches, topn)
            exact_filtered = _apply_structured_filters(deduped_exact, filters)
            if filters and not exact_filtered:
                exact_filtered = _apply_structured_filters(deduped_exact, None)
            
            # 🔧 食品防護：精確匹配也要過濾食品（如果非食品查詢）
            if not _is_food_query(query, keywords):
                exact_filtered = [item for item in exact_filtered if not _is_food_item(item)]
            
            result["exact"] = exact_filtered
        return result
    except Exception as exc:
        _logger.exception("chat product search failed: %s", exc)
        return result


def _filter_products_by_keywords(products: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
    if not products:
        return []
    significant = [kw for kw in keywords if kw and kw not in CHAT_STOP_WORDS and len(kw) >= 2]
    if not significant:
        return products
    filtered: List[Dict[str, Any]] = []
    for item in products:
        haystack = " ".join(
            str(item.get(field) or "").lower()
            for field in (
                "GoodIden",        # 🔧 添加商品編號欄位
                "商品編號",         # 🔧 添加中文商品編號欄位
                "Name",
                "商品名稱",
                "CateName",
                "分類名稱",
                "DESCRIPTION",
                "Description",
                "ShortDesc",
                "ShortDesc_20",
            )
        )
        if any(kw.lower() in haystack for kw in significant):
            filtered.append(item)
    return filtered or []


def _call_chat(prompt: str, system: Optional[str] = None, max_tokens: int = 64, model: Optional[str] = None) -> str:
    """Call OpenAI ChatCompletion (simple wrapper). Returns the assistant text or empty string on error."""
    client = _get_client()
    if not client:
        return ""
    if not model:
        model = OPENAI_MODEL  # 使用默認模型
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        res = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.0,
        )
        if res and res.choices:
            return (res.choices[0].message.content or "").strip()
    except Exception as e:
        _logger.exception("OpenAI call failed: %s", e)
    return ""


def _merge_prompt(custom: Optional[str], base: str) -> str:
    custom = (custom or "").strip()
    if not custom:
        return base
    return f"{custom}\n\n{base}"


DEFAULT_CHAT_CLARIFY_MESSAGE = "想確認一下，您是在找特定類型的商品嗎？像是日常外出、送禮或是工作使用？"


def llm_analyze_query(query: str, system_prompt: Optional[str] = None, use_search_config: bool = True) -> Dict[str, Any]:
    """分析查詢意圖，可指定使用搜索或聊天配置。
    
    新增功能：自動識別分類層級 (L1/L2/L3)
    """
    use_intent = SEARCH_USE_INTENT if use_search_config else CHAT_USE_INTENT
    model = SEARCH_OPENAI_MODEL if use_search_config else CHAT_OPENAI_MODEL
    
    _logger.info(f"    📋 llm_analyze_query() 被呼叫 (use_search_config={use_search_config})")
    _logger.info(f"      - 意圖分析啟用: {use_intent}, 模型: {model}")
    
    client = _get_client()
    if not use_intent or not client or not query:
        _logger.info(f"      - 略過 (use_intent={use_intent}, client={client is not None})")
        return {}
    
    _logger.info(f"      - 呼叫 OpenAI API 進行意圖分析")
    # 🆕 構建包含分類層級識別的提示詞
    category_prompt = _get_category_hierarchy_prompt()
    
    default_prompt = (
        "你是一個商品搜尋意圖解析器。輸入是使用者的自然語言需求，請輸出 JSON，包含：\n"
        "required_terms: 使用者必須條件（陣列，例如 ['無調味','核桃']）\n"
        "category_terms: 建議搜尋分類或種類（陣列，例如 ['堅果','零食']）\n"
        "excluded_terms: 應排除的詞（陣列）\n"
        # 🆕 新增分類層級欄位
        "category_hierarchy: {L1: '', L2: '', L3: ''} 商品分類層級（若有識別到）\n"
        "hierarchy_confidence: {L1: 0.0, L2: 0.0, L3: 0.0} 每個層級的識別信心度\n"
        "notes: 其他補充（字串）。若無明確資訊對應欄位請給空陣列或空字串。\n\n"
        # 🆕 加入分類識別指導
        f"{category_prompt}"
    )
    system_prompt = _merge_prompt(system_prompt, default_prompt)
    prompt = f"請解析以下需求並輸出 JSON（不需要多餘文字）：\n{query}"
    raw = _call_chat(prompt, system=system_prompt, model=model, max_tokens=300)
    if not raw:
        _logger.info(f"      - API 無回應")
        return {}
    try:
        result = json.loads(raw)
        # 🆕 確保分類層級欄位存在
        if "category_hierarchy" not in result:
            result["category_hierarchy"] = {"L1": "", "L2": "", "L3": ""}
        if "hierarchy_confidence" not in result:
            result["hierarchy_confidence"] = {"L1": 0.0, "L2": 0.0, "L3": 0.0}
        _logger.info(f"      ✅ 意圖分析完成: {result}")
        return result
    except Exception:
        try:
            content = raw[raw.find('{'):raw.rfind('}')+1]
            result = json.loads(content)
            # 🆕 確保分類層級欄位存在
            if "category_hierarchy" not in result:
                result["category_hierarchy"] = {"L1": "", "L2": "", "L3": ""}
            if "hierarchy_confidence" not in result:
                result["hierarchy_confidence"] = {"L1": 0.0, "L2": 0.0, "L3": 0.0}
            _logger.info(f"      ✅ 意圖分析完成 (JSON 修復): {result}")
            return result
        except Exception as e:
            _logger.warning(f"      ❌ 意圖分析失敗: {e}")
            return {}


def llm_clarify_or_confirm(intent: Optional[Dict[str, Any]], query: str = "") -> Dict[str, str]:
    """
    Decide whether we should ask a clarifying question before searching.
    """
    if not intent:
        return {"type": "ok"}

    need_clarification = intent.get("need_clarification")
    clarify_question = intent.get("clarify_question")
    if need_clarification:
        return {
            "type": "clarify",
            "message": clarify_question or "可以再幫我補充用途或預算，讓我更精準幫您推薦嗎？"
        }

    hierarchy_confidence = intent.get("hierarchy_confidence") or {}
    max_conf = 0.0
    try:
        confidences = [
            float(val) for val in hierarchy_confidence.values() if isinstance(val, (int, float, str))
        ]
        if confidences:
            max_conf = max(confidences)
    except Exception:
        max_conf = 0.0

    if max_conf < 0.55:
        return {"type": "clarify", "message": DEFAULT_CHAT_CLARIFY_MESSAGE}

    return {"type": "ok"}


def llm_expand_query(query: str, system_prompt: Optional[str] = None, use_search_config: bool = True) -> str:
    """擴展使用者查詢以包含同義詞/相關詞彙，可指定使用搜索或聊天配置
    
    Args:
        query: 使用者查詢
        system_prompt: 系統提示詞
        use_search_config: True 使用搜索配置，False 使用聊天配置
    
    Returns:
        擴展後的查詢字串，如果禁用或無 API key 則返回原查詢
    """
    use_expand = SEARCH_USE_EXPAND if use_search_config else CHAT_USE_EXPAND
    model = SEARCH_OPENAI_MODEL if use_search_config else CHAT_OPENAI_MODEL
    
    _logger.info(f"    📝 llm_expand_query() 被呼叫 (use_search_config={use_search_config})")
    _logger.info(f"      - 查詢擴展啟用: {use_expand}, 模型: {model}")
    
    client = _get_client()
    if not use_expand or not client or not query:
        _logger.info(f"      - 略過 (use_expand={use_expand}, client={client is not None})")
        return query
    
    _logger.info(f"      - 呼叫 OpenAI API")
    prompt = (
        f"請將使用者查詢盡量擴展成同義、相關或可能的搜尋詞組（以逗號分隔），輸出為一行，不要多餘說明。\n輸入：{query}\n輸出："
    )
    system = _merge_prompt(system_prompt, "你是一個搜尋查詢擴展工具（用繁體中文回應）")
    out = _call_chat(prompt, system=system, model=model, max_tokens=80)
    _logger.info(f"      ✅ 擴展結果: {out}")
    return out or query


def llm_shorten_20(text: str, use_search_config: bool = True) -> str:
    """產生簡短（<=20字）摘要，可指定使用搜索或聊天配置"""
    use_short = SEARCH_USE_SHORT if use_search_config else CHAT_USE_SHORT
    model = SEARCH_OPENAI_MODEL if use_search_config else CHAT_OPENAI_MODEL
    
    client = _get_client()
    if not use_short or not client or not text:
        return (text or "")[:60]
    prompt = (
        f"請將以下內容濃縮為不超過20個字的繁體中文重點描述，避免添加引號或多餘解說：\n\n{text}\n\n輸出："
    )
    out = _call_chat(prompt, system="你是一個簡短摘要生成器（繁體中文）", model=model, max_tokens=60)
    if not out:
        return (text or "")[:60]
    return out.strip()[:60]


def llm_generate_promo(name: str, raw_description: str, extra: Optional[str] = None, use_search_config: bool = True) -> str:
    """產生社群媒體風格的產品宣傳文案，可指定使用搜索或聊天配置"""
    use_promo = SEARCH_USE_PROMO if use_search_config else CHAT_USE_PROMO
    model = SEARCH_OPENAI_MODEL if use_search_config else CHAT_OPENAI_MODEL
    
    client = _get_client()
    if not use_promo or not client:
        base = raw_description or name
        return (base or "")[:180]
    system_prompt = (
        "你是一位品牌社群小編，請把商品資訊改寫成吸引人的繁體中文短文案。"
        "避免分析或列出包裝規格、重量、保存期限、保存方式、包裝數量等制式資訊。"
        "聚焦在使用情境、風格、特色或帶給消費者的感受，語氣自然、親切、有溫度。"
        "文案最多兩句，結尾可帶入情境或情感但不要使用#、Emoji 或制式口號（例如『立即購買』）。"
    )
    content_lines = [f"商品名稱：{name}"]
    if raw_description:
        content_lines.append(f"商品原始描述：{raw_description}")
    if extra:
        content_lines.append(f"補充資訊：{extra}")
    user_prompt = "\n".join(content_lines) + "\n請產出文案："
    out = _call_chat(user_prompt, system=system_prompt, model=model, max_tokens=160)
    return (out or raw_description or name)[:200]


def _truncate(text: str, limit: int) -> str:
    text = text or ""
    if len(text) > limit:
        return text[:limit - 1] + "…"
    return text


def llm_rerank_products(
    user_query: str,
    expanded_query: str,
    candidates: List[Dict[str, Any]],
    topn: int = 10,
    system_prompt: Optional[str] = None,
    use_search_config: bool = True,
) -> List[Dict[str, Any]]:
    """讓 LLM 基於語義相關性重新排序候選商品，可指定使用搜索或聊天配置
    
    Args:
        user_query: 使用者原始查詢
        expanded_query: 擴展後的查詢
        candidates: 候選商品列表
        topn: 返回的商品數量上限
        system_prompt: 系統提示詞
        use_search_config: True 使用搜索配置，False 使用聊天配置
    
    Returns:
        重新排序的商品列表（限制在 topn）或禁用時的原始列表
    """
    use_rerank = SEARCH_USE_RERANK if use_search_config else CHAT_USE_RERANK
    model = SEARCH_OPENAI_MODEL if use_search_config else CHAT_OPENAI_MODEL
    
    client = _get_client()
    if (
        not use_rerank
        or not client
        or not candidates
        or topn <= 0
    ):
        return candidates[:topn]

    # limit the number of candidates passed to the model to control prompt size
    max_candidates = min(len(candidates), max(topn * 3, 15))
    subset = candidates[:max_candidates]
    catalog = []
    for item in subset:
        catalog.append(
            {
                "id": item.get("GoodIden") or item.get("商品編號") or item.get("id") or "",
                "name": item.get("Name") or item.get("商品名稱") or "",
                "category": item.get("CateName") or item.get("分類名稱") or "",
                "brand": item.get("BRAND_Name") or item.get("品牌") or "",
                "price": item.get("Price") or item.get("商品價格") or "",
                "special_offer": item.get("SpecialOffer") or item.get("商品特價") or "",
                "description": _truncate(item.get("DESCRIPTION") or item.get("商品描述") or item.get("Description"), 200),
                "remark": _truncate(item.get("REMARK") or item.get("備註"), 120),
            }
    )

    payload = json.dumps(catalog, ensure_ascii=False)
    default_prompt = (
        "你是一個商品比對助手，請根據使用者的查詢從提供的商品列表中挑選最相關的項目。\n"
        "輸出必須是 JSON 物件，格式如下：\n"
        '{"matches": [{"id": "...", "score": 1-5, "reason": "簡短說明"}]}\n'
        f"僅保留與查詢高度相關的前幾項（最多 {topn} 項）。"
    )
    prompt = _merge_prompt(system_prompt, default_prompt)
    user_message = (
        f"使用者查詢：{user_query}\n"
        f"（可選擴展查詢：{expanded_query}）\n\n"
        f"候選商品列表（JSON 陣列）：\n{payload}"
    )

    try:
        res = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=400,
            temperature=0.0,
        )
        if not res or not res.choices:
            return subset[:topn]
        content = res.choices[0].message.content or ""
        parsed = json.loads(content)
        matches = parsed.get("matches")
        if not isinstance(matches, list):
            return subset[:topn]
        id_to_item = {
            (item.get("GoodIden") or item.get("商品編號") or item.get("id") or ""): item
            for item in subset
        }
        reranked: List[Dict[str, Any]] = []
        for entry in matches:
            if not isinstance(entry, dict):
                continue
            pid = entry.get("id")
            if not pid:
                continue
            chosen = id_to_item.get(pid)
            if chosen and chosen not in reranked:
                reranked.append(chosen)
            if len(reranked) >= topn:
                break
        # append any remaining candidates to fill up to requested topn
        for item in subset:
            if len(reranked) >= topn:
                break
            if item not in reranked:
                reranked.append(item)
        return reranked[:topn]
    except Exception as exc:
        _logger.exception("LLM rerank failed: %s", exc)
        return subset[:topn]


def _mock_or_real_llm(
    system_prompt: str,
    history: List[Dict[str, str]],
    user_message: str,
    catalog: List[Dict[str, Any]],
    context: Dict[str, Any],
) -> str:
    """
    強制透過 LLM 進行互動，理解使用者商品需求並搜尋 VIEW_GOODS_enhanced.csv 中的適合商品
    如果無可用商品則禮貌回覆。確保所有互動都經過 LLM 處理。
    """
    user_message = user_message or ""
    safe_history: List[Dict[str, str]] = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in ("system", "user", "assistant"):
            continue
        if content is None:
            continue
        safe_history.append({"role": role, "content": str(content)})

    mock_reply = _generate_mock_reply(user_message, catalog, context)
    _logger.debug("_mock_or_real_llm invoked")

    if context.get("overview"):
        _logger.debug("Using mock reply due to overview context")
        return mock_reply

    client = _get_client()
    if not client:
        _logger.debug("No OpenAI client available, using mock reply")
        return mock_reply
    
    _logger.debug("OpenAI client available, proceeding with real LLM call")

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(safe_history[-10:])  # avoid excessively long prompts
    messages.append({"role": "user", "content": user_message})

    try:
        _logger.debug("Calling OpenAI chat completion with model %s", CHAT_OPENAI_MODEL)
        res = client.chat.completions.create(
            model=CHAT_OPENAI_MODEL,  # 使用聊天專用模型
            messages=messages,
            max_tokens=320,
            temperature=0.4,
        )
        _logger.debug("OpenAI API call successful")
        if res and res.choices:
            reply_text = (res.choices[0].message.content or "").strip()
            _logger.debug("LLM reply received: %s", reply_text[:100])
            if reply_text:
                lowered = reply_text.lower()
                matches = context.get("matches") or []
                categories = context.get("categories") or []
                products = context.get("products") or []
                exact_products = context.get("exact_products") or []
                # when we already找出候選商品但 LLM 回「沒有」時，改用 mock。
                negative_markers = ("沒有", "無法", "找不到", "抱歉", "暫時沒有")
                candidate_names = [
                    str(item.get("name") or "").strip().lower()
                    for item in matches
                    if item.get("name")
                ]
                candidate_names.extend(
                    str(prod.get("Name") or prod.get("name") or "").strip().lower()
                    for prod in products
                )
                candidate_names.extend(
                    str(prod.get("Name") or prod.get("name") or "").strip().lower()
                    for prod in exact_products
                )
                candidate_names = [name for name in candidate_names if name]
                if candidate_names and any(name in lowered for name in candidate_names):
                    return reply_text

                if categories:
                    cat_lower = [cat.lower() for cat in categories if cat]
                    if any(cat in lowered for cat in cat_lower):
                        return reply_text

                if any(marker in lowered for marker in negative_markers):
                    _logger.debug("LLM reply contains negative markers, using mock reply")
                    return mock_reply
                return reply_text
    except Exception as exc:
        _logger.exception("Chat completion failed: %s", exc)
    
    _logger.debug("Fallback to mock reply")
    return mock_reply


def _get_natural_guidance(intent_subtype: str, response: str) -> str:
    """根據意圖子類型生成自然的引導語"""
    response_length = len(response)
    
    if intent_subtype == "health_info":
        if response_length < 180:
            return "\n\n想進一步了解相關的健康產品嗎？我可以為您推薦。"
        return ""
    
    elif intent_subtype == "usage_guide":
        if response_length < 160:
            return "\n\n如果您想實際體驗這些使用方法，我可以推薦適合的產品。"
        return ""
    
    elif intent_subtype == "knowledge":
        if response_length < 170:
            return "\n\n對這類產品感興趣嗎？我可以介紹一些優質的選擇。"
        return ""
    
    elif intent_subtype == "comparison":
        if response_length < 180:
            return "\n\n需要我推薦其中比較適合您的產品嗎？"
        return ""
    
    elif intent_subtype == "recommendation":
        # 推薦類問題不需要額外引導，因為本身就是在尋求推薦
        return ""
    
    else:
        if response_length < 150:
            return "\n\n如果您想了解相關產品，我也可以為您推薦。"
        return ""


def _detect_intent_subtype(query: str) -> str:
    """檢測資訊諮詢的具體子類型"""
    if not query:
        return "general"
    
    query_lower = query.lower()
    
    # 按照優先級檢測子類型
    for intent_type, patterns in INFORMATION_INTENT_PATTERNS.items():
        if any(pattern in query_lower for pattern in patterns):
            return intent_type
    
    # 檢查推薦諮詢
    if any(pattern in query_lower for pattern in RECOMMENDATION_PATTERNS):
        return "recommendation"
    
    return "general"


def _extract_full_product_context(content: str, matched_keywords: List[str]) -> str:
    """
    從內容中提取完整的產品描述，包含修飾詞
    例如：從 "冷壓純鮮椰子油對健康有什麼幫助" 提取 "冷壓純鮮椰子油"
    """
    if not matched_keywords:
        return ""
    
    # 為每個匹配的關鍵詞尋找完整描述
    best_match = ""
    longest_length = 0
    
    for keyword in matched_keywords:
        # 在內容中找到關鍵詞的位置
        keyword_pos = content.find(keyword)
        if keyword_pos == -1:
            continue
            
        # 向前尋找修飾詞的起始位置
        start_pos = keyword_pos
        chars_before = content[:keyword_pos]
        
        # 常見修飾詞模式
        modifiers = ['冷壓', '純鮮', '有機', '天然', '特級', '初榨', '原味', '無糖', '低脂', '高纖']
        
        # 向前搜索修飾詞
        words_before = chars_before.split()
        if words_before:
            # 檢查最後幾個詞是否為修飾詞
            for i in range(len(words_before) - 1, max(-1, len(words_before) - 4), -1):
                word = words_before[i]
                if any(mod in word for mod in modifiers):
                    start_pos = content.find(word, max(0, keyword_pos - 50))
                    break
        
        # 向後尋找產品描述的結束位置
        end_pos = keyword_pos + len(keyword)
        chars_after = content[end_pos:]
        
        # 檢查是否有後續的產品相關詞
        product_suffixes = ['油', '粉', '片', '粒', '膠囊', '錠', '液', '醬', '茶', '咖啡']
        for suffix in product_suffixes:
            if chars_after.startswith(suffix):
                end_pos += len(suffix)
                break
        
        # 提取完整產品名稱
        full_product = content[start_pos:end_pos].strip()
        
        # 選擇最長且合理的描述
        if len(full_product) > longest_length and len(full_product) <= 20:  # 避免過長描述
            best_match = full_product
            longest_length = len(full_product)
    
    return best_match or matched_keywords[-1]


def _detect_context_product_inquiry(user_message: str, history: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """
    🎯 混合智慧上下文產品詢問檢測器 - 增強版
    
    Returns:
        None: 非上下文產品詢問
        Dict: {
            "action": "direct_search" | "confirm_search",
            "query": str,  # 完整產品描述，如 "冷壓純鮮椰子油"
            "product": str, 
            "confidence": float,
            "confirmation_message": str (僅confirm_search時)
        }
    """
    if not user_message or not history:
        return None
    
    message_lower = user_message.lower()
    
    # 1. 檢測置信度
    confidence = 0.0
    inquiry_type = None
    
    if any(trigger in message_lower for trigger in CONTEXT_INQUIRY_HIGH_CONFIDENCE):
        confidence = 0.9
        inquiry_type = "direct"
    elif any(trigger in message_lower for trigger in CONTEXT_INQUIRY_MEDIUM_CONFIDENCE):
        confidence = 0.6  
        inquiry_type = "indirect"
    else:
        return None
    
    # 2. 提取上下文內容 (最近4輪對話)
    recent_messages = []
    for msg in history[-4:]:
        if isinstance(msg, dict) and msg.get("content"):
            recent_messages.append(msg["content"])
    
    all_context = " ".join(recent_messages)
    
    # 3. 匹配產品關鍵詞
    matched_keywords = []
    for keyword in CORE_PRODUCT_KEYWORDS:
        if keyword in all_context:
            matched_keywords.append(keyword)
    
    if not matched_keywords:
        return None
    
    # 4. 提取完整產品描述
    full_product_description = _extract_full_product_context(all_context, matched_keywords)
    target_keyword = matched_keywords[-1]  # 最後提到的核心關鍵詞
    
    _logger.debug("Context extraction: '%s' -> '%s'", target_keyword, full_product_description)
    
    # 5. 根據置信度決策
    if confidence >= 0.8:
        # 高置信度：直接轉換為產品搜索
        return {
            "action": "direct_search",
            "query": full_product_description,  # 使用完整描述
            "product": target_keyword,  # 核心關鍵詞用於顯示
            "confidence": confidence,
            "matched_products": matched_keywords,
            "inquiry_type": inquiry_type,
            "full_description": full_product_description
        }
    else:
        # 中置信度：確認後轉換
        return {
            "action": "confirm_search",
            "product": target_keyword,
            "query": full_product_description, 
            "confidence": confidence,
            "matched_products": matched_keywords,
            "inquiry_type": inquiry_type,
            "full_description": full_product_description,
            "confirmation_message": f"您是想了解{full_product_description}的商品資訊嗎？我可以為您搜尋相關產品。"
        }


def _detect_conversation_intent(query: str) -> str:
    """檢測對話意圖: 'company_info' | 'information' | 'product_search' | 'general'"""
    if not query:
        return "general"
    
    query_lower = query.lower()

    # 🆕 公司資料查詢 (最高優先級)
    # 檢查是否包含公司資料相關關鍵字
    for category, patterns in COMPANY_INFO_PATTERNS.items():
        if any(pattern in query_lower for pattern in patterns):
            return "company_info"
    
    # 概覽/詢問販售範圍 → 資訊對話
    overview_triggers = ("賣什麼", "有哪些", "商品有哪些", "有哪些商品", "商品分類", "商品類別", "分幾類", "類型")
    if any(t in query_lower for t in overview_triggers):
        return "information"
    
    # 檢查是否為資訊諮詢（優先級最高）
    for intent_type, patterns in INFORMATION_INTENT_PATTERNS.items():
        if any(pattern in query_lower for pattern in patterns):
            return "information"

    # 活動/情境導購
    if any(pattern in query_lower for pattern in EVENT_INTENT_PATTERNS):
        return "event_food_planning"
    
    # 檢查是否為推薦諮詢（用資訊模式處理，提供建議後再引導到商品）
    if any(pattern in query_lower for pattern in RECOMMENDATION_PATTERNS):
        return "information"
    
    # 檢查是否為明確購買意圖
    if any(pattern in query_lower for pattern in PURCHASE_INTENT_PATTERNS):
        return "product_search"
    
    # 特殊情況：包含產品名稱但沒有購買意圖的問題，歸類為資訊諮詢
    # 例如：「椰子油和橄欖油有什麼差別」
    if any(word in query_lower for word in ["差別", "不同", "vs", "和", "與"]) and not any(word in query_lower for word in ["推薦", "買", "購買"]):
        return "information"
    
    # 預設為一般對話
    return "general"


def _detect_real_estate_query(query: str) -> Dict[str, Any]:
    """識別房產意圖（僅聊天用），回傳是否命中與推測的層級。"""
    if not query:
        return {"hit": False, "hierarchy": {}}
    norm = query.strip()
    norm_lower = norm.lower()
    hit = any(kw.lower() in norm_lower for kw in REAL_ESTATE_KEYWORDS)
    hierarchy: Dict[str, str] = {}
    if not hit:
        return {"hit": False, "hierarchy": hierarchy}
    # 簡單層級推測（不改動搜尋邏輯，只給 LLM 提示）
    if "磐鈺" in norm:
        hierarchy["L1"] = "磐鈺建設"
    if "草間漫漫" in norm:
        hierarchy["L2"] = "磐鈺草間漫漫"
    elif "雲華" in norm:
        hierarchy["L2"] = "磐鈺雲華"
    elif "雲詠" in norm:
        hierarchy["L2"] = "磐鈺雲詠"
    if "極致輕寓2房" in norm:
        hierarchy["L3"] = "極致輕寓2房"
    elif "光合雅寓3房" in norm:
        hierarchy["L3"] = "光合雅寓3房"
    elif "市景菁英3房" in norm:
        hierarchy["L3"] = "市景菁英3房"
    elif "景觀大戶4房" in norm:
        hierarchy["L3"] = "景觀大戶4房"
    elif "協奏輕盈3房" in norm or "樂樂璵里" in norm:
        hierarchy["L3"] = "協奏輕盈3房"
    return {"hit": hit, "hierarchy": hierarchy}


def _filter_real_estate_items(catalog: List[Dict[str, Any]], hierarchy: Dict[str, str]) -> List[Dict[str, Any]]:
    """從 snapshot 中抓取房產商品，盡量依層級縮小。"""
    if not catalog:
        return []
    def _norm(s: Any) -> str:
        return str(s or "").strip()
    l1 = _norm(hierarchy.get("L1"))
    l2 = _norm(hierarchy.get("L2"))
    l3 = _norm(hierarchy.get("L3"))
    hits: List[Dict[str, Any]] = []
    for item in catalog:
        name = _norm(item.get("name"))
        cat = _norm(item.get("category"))
        if l3 and (l3 in name or cat == l3):
            hits.append(item)
            continue
        if l2 and (l2 in name):
            hits.append(item)
            continue
        if l1 and ("磐鈺" in name or cat == l1 or any(term in name for term in ["草間漫漫", "雲華", "雲詠"])):
            hits.append(item)
            continue
        if any(term in name for term in REAL_ESTATE_KEYWORDS):
            hits.append(item)
    # 去重保留順序
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for it in hits:
        gid = _norm(it.get("good_id"))
        if gid in seen:
            continue
        seen.add(gid)
        deduped.append(it)
    return deduped


def _build_real_estate_prompt(items: List[Dict[str, Any]], hierarchy: Dict[str, str]) -> str:
    """房產專員提示詞，控制語氣與結構。"""
    lines = [
        "你是房地產專員，主推磐鈺建設系列案，語氣精簡專業，不寒暄、不自介。",
        "回覆格式：",
        "1) 先一句定位，說明案名/戶型與適合族群。",
        "2) 接 2-4 個重點，以「•」列出（坪數/格局、採光通風、生活圈、陽台/綠化亮點）。",
        "3) 收尾 CTA：詢問是否要看其他坪型或預約賞屋。",
        "限制：60-80 字內（不含項目符號），不要詢問日常外出/送禮/工作用途，不要捏造價格。",
        "若沒有符合商品，回覆固定句：目前沒有找到該分類的房源，需不需要改看其他坪型或社區？",
        "",
        "可參考的房源：",
    ]
    if hierarchy:
        lines.append(f"- 層級提示：L1={hierarchy.get('L1') or ''} L2={hierarchy.get('L2') or ''} L3={hierarchy.get('L3') or ''}".strip())
    if items:
        for it in items[:6]:
            name = str(it.get("name") or "").strip()
            cat = str(it.get("category") or "").strip()
            tag = f"【{cat}】" if cat else ""
            lines.append(f"- {tag} {name}")
    else:
        lines.append("- 目前沒有候選房源可供參考。")
    return "\n".join(lines)


def _build_information_system_prompt(intent_type: str = "general") -> str:
    """建立資訊諮詢專用的系統提示詞，支援個性化語氣"""
    
    base_rules = """
回應原則：
1. 提供實用的資訊和建議，基於科學知識
2. 保持客觀中立，避免誇大效果或醫療宣稱  
3. 如涉及健康問題，建議諮詢專業醫師或營養師
4. 可以分享一般性的產品知識，但重點在資訊分享而非銷售
5. 適當時可自然地提及「如果您想了解相關產品，我也可以為您推薦」

請用繁體中文回應，控制在150-250字內。"""

    if "health" in intent_type.lower():
        return f"""你是一位專業的健康產品顧問與營養師。用專業但溫暖的語調回應健康相關問題。

語調特色：專業嚴謹、溫和關懷、基於科學證據
回應風格：先解釋健康機制，再提供實用建議，最後適度提醒注意事項

{base_rules}"""

    elif "usage" in intent_type.lower():
        return f"""你是一位經驗豐富的產品使用專家。用實用導向的親切語調回應使用方法問題。

語調特色：實用親切、步驟明確、貼心提醒
回應風格：提供具體用法、建議用量、使用時機和小技巧

{base_rules}"""

    elif "knowledge" in intent_type.lower():
        return f"""你是一位博學的產品知識專家。用教育性但易懂的語調分享產品知識。

語調特色：知識豐富、深入淺出、啟發思考
回應風格：解釋原理機制、分享有趣知識、提供深度理解

{base_rules}"""

    elif "comparison" in intent_type.lower():
        return f"""你是一位客觀的產品比較分析師。用中立專業的語調進行比較分析。

語調特色：客觀中立、邏輯清晰、平衡分析
回應風格：列出差異點、分析各自優勢、幫助用戶理性選擇

{base_rules}"""

    elif "recommendation" in intent_type.lower():
        return f"""你是一位貼心的產品推薦顧問。用親切諮詢的語調提供推薦建議。

語調特色：親切諮詢、考慮周全、個人化建議
回應風格：了解需求、分析選擇、給予具體推薦理由

{base_rules}"""
    
    else:
        return f"""你是一位全方位的產品顧問。用專業親切的語調回應各類產品問題。

語調特色：專業親切、樂於助人、知識豐富
回應風格：針對問題類型靈活調整回應方式

{base_rules}"""


def _call_chat_for_information(user_message: str, history: List[Dict[str, str]], system_prompt: str, intent_subtype: str = "general") -> str:
    """專門處理資訊諮詢的 LLM 調用"""
    client = _get_client()
    if not client:
        return "很抱歉，目前無法提供詳細的產品資訊。建議您諮詢專業營養師或查閱權威資料來源。"
    
    # 🧠 增強的對話記憶：分析歷史對話中的產品興趣和偏好
    context_prompt = user_message
    conversation_context = ""
    interested_products = set()
    
    if history:
        # 取最近3輪對話作為上下文，並分析產品興趣
        recent_history = []
        for msg in (history or [])[-6:]:
            if isinstance(msg, dict) and msg.get("role") and msg.get("content"):
                role = "用戶" if msg["role"] == "user" else "助理"
                content = msg["content"]
                recent_history.append(f"{role}: {content}")
                
                # 提取提到的產品類型
                content_lower = content.lower()
                product_keywords = ["椰子油", "橄欖油", "堅果", "蜂蜜", "燕麥", "藜麥", "奇亞籽", "維生素", "膠原蛋白", "益生菌"]
                for product in product_keywords:
                    if product in content_lower:
                        interested_products.add(product)
        
        if recent_history:
            conversation_context = "對話歷史：\n" + "\n".join(recent_history[-3:])
        
        # 如果檢測到持續關注的產品，加入上下文
        if interested_products:
            product_context = f"\n\n用戶關注的產品：{', '.join(interested_products)}"
            conversation_context += product_context
    
    # 構建完整的上下文提示詞
    if conversation_context:
        context_prompt = conversation_context + "\n\n當前問題：" + user_message
    
    # 🎯 基於對話記憶的個人化提示
    if interested_products and intent_subtype == "recommendation":
        context_prompt += f"\n\n注意：用戶之前提到過對 {', '.join(list(interested_products)[:2])} 等產品的興趣，可以考慮相關建議。"
    
    # 調用 LLM 獲取資訊回應
    try:
        response = _call_chat(
            prompt=context_prompt, 
            system=system_prompt, 
            model=CHAT_OPENAI_MODEL, 
            max_tokens=300
        )
        
        if not response:
            return "很抱歉，目前無法提供詳細回應。建議您查閱相關資料或諮詢專業人員。"
        
        # 🌟 根據意圖子類型優化引導語
        if not any(keyword in response for keyword in ["推薦", "產品", "商品", "了解更多"]):
            guidance = _get_natural_guidance(intent_subtype, response)
            if guidance:
                response += guidance
        
        return response
        
    except Exception as e:
        _logger.exception("資訊諮詢 LLM 調用失敗: %s", e)
        return "很抱歉，目前系統忙碌中。建議您稍後再試，或諮詢專業營養師獲得更詳細的資訊。"


def _extract_keywords(text: str) -> List[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+", text or "")
    keywords: List[str] = []
    for token in tokens:
        token = token.strip().lower()
        if not token or token in CHAT_STOP_WORDS:
            continue
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            if len(token) >= 2:
                keywords.append(token)
                # 加入連續雙字以利匹配（避免單字噪音）
                for idx in range(len(token) - 1):
                    bigram = token[idx : idx + 2]
                    if bigram not in CHAT_STOP_WORDS:
                        keywords.append(bigram)
        else:
            keywords.append(token)
    # 去重保持順序
    deduped: List[str] = []
    for kw in keywords:
        if kw and kw not in deduped:
            deduped.append(kw)
    return deduped


def _match_catalog_items(keywords: List[str], catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not catalog:
        return []
    if not keywords:
        return catalog[:3]
    lowered_keywords = [kw for kw in keywords if kw]
    if not lowered_keywords:
        return catalog[:3]
    matches: List[Dict[str, Any]] = []
    for item in catalog:
        name = str(item.get("name") or "").lower()
        category = str(item.get("category") or "").lower()
        if not name and not category:
            continue
        if any(kw in name or kw in category for kw in lowered_keywords):
            matches.append(item)
    if matches:
        return matches[:5]

    # 如果快照中找不到，從完整資料集再比對一次
    if lowered_keywords:
        try:
            from goods_search_service import load_goods_rows  # local import to avoid circular at module load
            rows = load_goods_rows()
            extended: List[Dict[str, Any]] = []
            for r in rows:
                name = str(r.get("Name") or r.get("商品名稱") or "").strip()
                category = str(r.get("CateName") or r.get("分類名稱") or "").strip()
                lower_name = name.lower()
                lower_cat = category.lower()
                if not name and not category:
                    continue
                if any(kw in lower_name or kw in lower_cat for kw in lowered_keywords):
                    extended.append({
                        "good_id": str(r.get("GoodIden") or r.get("商品編號") or ""),
                        "name": name,
                        "price": r.get("Price") or r.get("價格"),
                        "special": r.get("SpecialOffer") or r.get("特價"),
                        "category": category,
                    })
                if len(extended) >= 5:
                    break
            if extended:
                return extended
        except Exception:
            pass

    # fallback：按原始順序提供前三項
    return catalog[:3]


def _collect_categories(
    matches: List[Dict[str, Any]],
    catalog: List[Dict[str, Any]],
    products: List[Dict[str, Any]],
    limit: int = 4,
) -> List[str]:
    categories: List[str] = []
    seen: set[str] = set()

    def add(raw: Any):
        name = str(raw or "").strip()
        if not name:
            return
        if name in seen:
            return
        seen.add(name)
        categories.append(name)

    for product in products:
        add(product.get("CateName") or product.get("分類名稱"))
        if len(categories) >= limit:
            return categories[:limit]
    for item in matches:
        add(item.get("category"))
        if len(categories) >= limit:
            return categories[:limit]
    for item in catalog:
        add(item.get("category"))
        if len(categories) >= limit:
            break
    return categories[:limit]


def _prepare_chat_context(user_message: str, catalog: List[Dict[str, Any]]) -> Dict[str, Any]:
    query = (user_message or "").strip()
    keywords = _extract_keywords(query)
    matches = _match_catalog_items(keywords, catalog)
    category_question = any(word in query for word in ["分類", "類別", "類型", "幾大類", "分幾類"])
    normalized_query = _strip_filler_phrases(query)
    significant_keywords = _extract_core_terms(keywords)
    wants_overview = (
        not significant_keywords
        and any(trigger in normalized_query for trigger in GENERAL_OVERVIEW_TRIGGERS)
    )
    structured_filters = _derive_structured_filters(query, keywords)
    category_context_detected = False

    if wants_overview:
        product_search = {"exact": [], "fuzzy": []}
        exact_products = []
        fuzzy_products = []
        products = []
        categories = list(CHAT_CATEGORY_TOPICS.keys())
        matches = []
    else:
        # 🎯 LLM Step 5: 從 LLM 分析中提取分類層級
        category_hierarchy: Optional[Dict[str, str]] = None
        try:
            analysis = llm_analyze_query(query, use_search_config=False)
            category_hierarchy = analysis.get("category_hierarchy", {})
            if category_hierarchy and not any(category_hierarchy.get(k) for k in ["L1", "L2", "L3"]):
                category_hierarchy = None
            if category_hierarchy:
                _logger.info(
                    "Category hierarchy detected L1=%s L2=%s L3=%s",
                    category_hierarchy.get("L1"),
                    category_hierarchy.get("L2"),
                    category_hierarchy.get("L3"),
                )
                category_context_detected = True
                structured_filters = dict(structured_filters or {})
                structured_filters.setdefault("category_hierarchy", category_hierarchy)
        except Exception as e:
            _logger.warning("Failed to analyze query for hierarchy: %s", e)
            category_hierarchy = None
        
        product_search = _search_products_for_chat(query, keywords, topn=6, filters=structured_filters, hierarchy=category_hierarchy)
        exact_products = _dedupe_products(product_search.get("exact", []), 6)
        fuzzy_candidates = product_search.get("fuzzy", []) or []
        fuzzy_products = _dedupe_products(fuzzy_candidates, 12)
        filtered_products = _filter_products_by_keywords(fuzzy_products, keywords) if fuzzy_products else []
        if exact_products:
            products = exact_products if len(exact_products) >= 6 else _dedupe_products(
                exact_products + filtered_products + fuzzy_products,
                12,
            )
        else:
            products = filtered_products or fuzzy_products
        if len(products) < 6:
            merged_pool: List[Dict[str, Any]] = []
            if exact_products:
                merged_pool.extend(exact_products)
            if filtered_products:
                merged_pool.extend(filtered_products)
            if fuzzy_products:
                merged_pool.extend(fuzzy_products)
            products = _dedupe_products(merged_pool or products, 12)
        categories = _collect_categories(matches, catalog, products) if category_question else []
    return {
        "query": query,
        "keywords": keywords,
        "matches": matches,
        "exact_products": exact_products,
        "fuzzy_products": fuzzy_products,
        "products": products,
        "category_question": category_question,
        "categories": categories,
        "overview": CHAT_CATEGORY_TOPICS if wants_overview else {},
        "structured_filters": structured_filters,
        "oos_suspected": _should_flag_oos(
            query,
            keywords,
            products,
            has_category_context=(category_context_detected or bool(structured_filters.get("category_filter")))
        ),
    }


def build_oos_response(query: str, reason: str = "keyword_block") -> Dict[str, Any]:
    overview = CHAT_CATEGORY_TOPICS
    lines: List[str] = []
    for idx, (topic, children) in enumerate(overview.items(), 1):
        marker = f"{idx}\u20E3"
        child_text = "、".join(children) if children else "--"
        lines.append(f"{marker} {topic}：{child_text}")
    reply_text = (
        "目前我們暫不販售該品類，但以下是我們的主要販售範圍：\n\n"
        + "\n".join(lines)
        + "\n\n您可以告訴我想逛哪一類或提供預算、用途，我會為您推薦合適的商品。"
    )
    return {
        "reply": reply_text,
        "action": {"type": "none"},
        "intent": "information",
        "meta": {"oos_category": True, "oos_reason": reason, "query": query},
        "display_mode": "text_only",
    }


def _create_oos_meta(query: str, reason: str, keywords: List[str]) -> Dict[str, Any]:
    return {
        "oos_category": True,
        "oos_reason": reason,
        "query": query,
        "suspected_keywords": keywords,
    }


def _generate_mock_reply(user_message: str, catalog: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> str:
    context = context or _prepare_chat_context(user_message, catalog)
    query = context.get("query") or (user_message or "").strip()
    if not query:
        return "今天想找什麼好物呢？目前店內有多款人氣商品，部分正值特價。需要我顯示詳細介紹與圖片嗎？"

    matches = context.get("matches") or []
    exact_products = context.get("exact_products") or []
    fuzzy_products = context.get("fuzzy_products") or []
    products = context.get("products") or []
    category_question = bool(context.get("category_question"))
    categories = context.get("categories") or []
    significant_keywords = [kw for kw in context.get("keywords", []) if kw and kw not in CHAT_STOP_WORDS and len(kw) >= 2]
    overview = context.get("overview") or {}

    def _format_name(item: Dict[str, Any]) -> str:
        return str(item.get("name") or "神秘商品")

    def _format_price(item: Dict[str, Any]) -> str:
        special = item.get("special")
        price = item.get("price")
        if special not in (None, "", 0):
            return f"特價 {special}"
        if price not in (None, "", 0):
            return f"售價 {price}"
        return "價格依品項為準"

    if overview:
        lines = []
        for idx, (topic, children) in enumerate(overview.items(), 1):
            marker = f"{idx}\u20E3"
            child_text = "、".join(children) if children else "--"
            lines.append(f"{marker} {topic}：{child_text}")
        body = "\n".join(lines)
        return (
            "我們目前販售的主要商品分類如下：\n\n"
            f"{body}\n\n您可以告訴我想逛哪一類，我再為您列出該分類的商品與價格喔！"
        )

    if category_question:
        if not categories:
            categories = _collect_categories(matches, catalog, products)
        if categories:
            listed = "、".join(categories[:4])
            return f"廚房調味品大致可分為：{listed}。需要我顯示詳細介紹與圖片嗎？{SUGGEST_PROMPT_SUFFIX}"
        return f"目前調味品主要依風味與用途區分，歡迎告訴我偏好口味，我再為您推薦。需要我顯示詳細介紹與圖片嗎？{SUGGEST_PROMPT_SUFFIX}"

    if products:
        lines: List[str] = []
        source_items = products[:3]
        for idx, item in enumerate(source_items, 1):
            name = str(item.get("Name") or item.get("name") or "精選商品").strip()
            special = item.get("SpecialOffer") or item.get("商品特價") or item.get("special")
            price = item.get("Price") or item.get("商品價格") or item.get("price")
            if special not in (None, "", 0):
                price_text = f"原價{price}元，特價{special}元" if price not in (None, "", 0) else f"特價{special}元"
            elif price not in (None, "", 0):
                price_text = f"售價{price}元"
            else:
                price_text = "價格依現場為準"
            lines.append(f"{idx}. **{name}** – {price_text}。")
        body = "\n".join(lines)
        header = "以下是與您需求高度匹配的商品：" if exact_products else "我們找到幾款符合需求的商品，供您參考："
        return (
            f"{header}\n\n"
            f"{body}\n\n這些商品都很熱門，部分品項有特價。需要我顯示詳細介紹與圖片嗎？{SUGGEST_PROMPT_SUFFIX}"
        )

    if matches:
        relevant_matches = []
        for item in matches:
            name_field = str(item.get("name") or "").lower()
            if significant_keywords and not any(kw in name_field for kw in significant_keywords):
                continue
            relevant_matches.append(item)
        if significant_keywords and not relevant_matches:
            matches = []
        else:
            if relevant_matches:
                matches = relevant_matches
        if matches:
            top_items = matches[:3]
            names = [f"{_format_name(item)}（{_format_price(item)}）" for item in top_items]
            listed = "、".join(names)
            return f"我們有{listed}等商品可選，部分品項有特價。需要我顯示詳細介紹與圖片嗎？{SUGGEST_PROMPT_SUFFIX}"

    # 針對無符合商品的情況提供更詳細和禮貌的回覆
    if significant_keywords:
        keywords_text = "、".join(significant_keywords[:3])
        return (f"很抱歉，目前我們的商品庫存中暫時沒有完全符合「{keywords_text}」需求的商品。\n\n"
                f"不過我們會持續更新商品，也歡迎您描述更詳細的需求，或許我能為您推薦相關的替代商品。\n"
                f"如果您還有其他想了解的商品類別，我很樂意為您介紹！")
    else:
        return (f"很抱歉，根據您的查詢暫時沒有找到合適的商品。\n\n"
                f"不過我們店內有多款精選商品，包括健康食品、調味料、零食等多種類別。\n"
                f"歡迎告訴我您具體想要什麼類型的商品，我會為您詳細介紹適合的選項！")


def _build_system_prompt(catalog: List[Dict[str, Any]]) -> str:
    lines = [
        CSV_ONLY_SYSTEM_PROMPT,
        "",
        "你是「哈通友善生活館」的智能客服，專精於理解客戶商品需求並提供精準建議。",
        "核心使命：一律透過 LLM 與使用者互動，深度理解商品需求，從 VIEW_GOODS_enhanced.csv 搜尋適合商品。",
        "",
        "互動原則：",
        "1) 📝 **需求理解**：仔細聆聽並分析使用者的商品需求、預算、用途、偏好等。",
        "2) 🔍 **商品搜尋**：基於理解的需求，在 VIEW_GOODS_enhanced.csv 中搜尋最適合的商品。",
        "3) 💡 **智能推薦**：找到商品時，主動推薦並提供特價資訊、規格描述等詳細資訊。",
        "4) 🤝 **禮貌回應**：如果暫無符合商品，禮貌說明並主動了解更多需求或建議替代方案。",
        "5) 📋 **持續互動**：每次回覆都要詢問是否需要看詳細介紹與圖片，保持對話連續性。",
        "",
        "以下列出部分上架商品（名稱/價格/特價，非全部）：",
    ]
    for it in catalog:
        name = (it.get("name") or "").strip()
        if not name:
            continue
        price = it.get("price")
        special = it.get("special")
        tag = f"(特價 {special})" if special not in (None, "", 0) else ""
        price_text = price if price not in (None, "") else "—"
        lines.append(f"- {name} / {price_text}{' ' + tag if tag else ''}")
    return "\n".join(lines)


def _last_user_query(history: List[Dict[str, str]]) -> Optional[str]:
    if not history:
        return None
    for item in reversed(history):
        if not isinstance(item, dict):
            continue
        if item.get("role") != "user":
            continue
        content = str(item.get("content") or "").strip()
        if content:
            return content
    return None


def _should_switch_to_search(user_message: str, assistant_reply: str, history: List[Dict[str, str]]) -> Optional[str]:
    """Return trigger type when user wants to switch to search, otherwise None."""
    user_texts: List[str] = []
    if user_message:
        user_texts.append(str(user_message).lower())
    for item in history or []:
        if not isinstance(item, dict):
            continue
        if item.get("role") != "user":
            continue
        content = item.get("content")
        if content:
            user_texts.append(str(content).lower())

    keywords = [
        "看詳細",
        "看一下",
        "要看",
        "顯示商品",
        "看圖片",
        "帶我看看",
        "前往購買",
        "看更多",
        "詳細介紹",
        "看特價",
        "帶我去買",
        "我要看",
    ]
    if user_texts and any(kw in text for text in user_texts for kw in keywords):
        return "explicit"

    # fallback: short confirmations like "要" after客服詢問是否要看詳細
    recent_assistant_prompt = ""
    for item in reversed(history or []):
        if isinstance(item, dict) and item.get("role") == "assistant":
            recent_assistant_prompt = str(item.get("content") or "").lower()
            break
    if recent_assistant_prompt:
        follow_up_cues = [
            "需要我顯示詳細介紹",
            "要我顯示詳細介紹",
            "要不要看詳細介紹",
            "需要我帶你看",
            "要我幫你顯示圖片",
            "是否需要看詳細介紹",
            "是否需要看詳細介紹與圖片",
            "需要看詳細介紹與圖片",
            "需要看詳細介紹",
            "是否需要我顯示詳細介紹",
        ]
        if any(cue in recent_assistant_prompt for cue in follow_up_cues):
            normalized = (user_message or "").strip().lower()
            normalized = re.sub(r"[\s\W_]+", "", normalized, flags=re.UNICODE)
            if normalized in CONFIRMATION_TERMS:
                return "confirmation"
    return None


def chat_reply(
    user_message: str,
    history: List[Dict[str, str]],
    catalog: List[Dict[str, Any]],
    topn: int = 8,
) -> Dict[str, Any]:
    # Debug 資訊：檢查 USE_CHAT_MODE
    chat_mode = os.getenv("USE_CHAT_MODE", "True").lower()
    _logger.debug("USE_CHAT_MODE=%s", chat_mode)
    
    if chat_mode not in ("true", "1", "yes"):
        _logger.debug("Chat mode disabled, returning mock response")
        return {"reply": "聊天模式目前未啟用。", "action": {"type": "none"}}

    _logger.debug("chat_reply called with message: %s", user_message[:50])
    history = history or []
    catalog = catalog or []
    normalized_message = (user_message or "").strip()
    previous_alignment = _extract_alignment_from_history(history)

    # 🏠 房產意圖：切換房產專員提示詞（僅聊天，不改其他流程）
    real_estate_ctx = _detect_real_estate_query(normalized_message)
    if real_estate_ctx.get("hit"):
        estate_items = _filter_real_estate_items(catalog, real_estate_ctx.get("hierarchy") or {})
        system_prompt = _build_real_estate_prompt(estate_items, real_estate_ctx.get("hierarchy") or {})
        context = {"products": estate_items}
        reply_text = _mock_or_real_llm(system_prompt, history, normalized_message, catalog, context)
        structured_filters = {}
        if real_estate_ctx.get("hierarchy"):
            structured_filters["category_hierarchy"] = real_estate_ctx["hierarchy"]
        return {
            "reply": reply_text,
            "intent": "real_estate",
            "overview": True,
            "meta": {"real_estate": True, "category_hierarchy": real_estate_ctx.get("hierarchy"), "items_count": len(estate_items)},
            "structured_filters": structured_filters,
            "action": {"type": "none"},
        }

    # 🎯 優先檢測上下文產品詢問 - 混合智慧核心
    context_inquiry = _detect_context_product_inquiry(normalized_message, history)
    if context_inquiry:
        _logger.info("Context product inquiry detected: %s for %s", context_inquiry["action"], context_inquiry["product"])
        
        if context_inquiry["action"] == "direct_search":
            # 高置信度：直接執行產品搜索，不回應中間訊息
            search_query = context_inquiry["query"]
            
            # 直接執行產品搜尋
            context = _prepare_chat_context(search_query, catalog)
            structured_filters = context.get("structured_filters") or {}
            
            # 取得搜尋到的產品
            products = context.get("products", [])
            prompt_items = context.get("matches") or products[:max(topn, 1)]
            system_prompt = _build_system_prompt(prompt_items)
            reply_text = _mock_or_real_llm(system_prompt, history, search_query, catalog, context)

            # 建構 overview 資料
            overview = {
                "results": products,
                "total": len(products),
                "query": search_query
            }
            
            # 從搜尋結果建構對齊資訊
            alignment_items = _build_alignment_items(products)
            
            alignment = {
                "intent": "product_search",
                "items": alignment_items,
                "query": search_query
            } if alignment_items else None
            
            # 🆕 上下文搜索也進行商品格式化處理
            formatting_result = format_product_recommendations(reply_text)
            if formatting_result["product_count"] > 0:
                _logger.info("Product formatting applied to context search: %d products", formatting_result["product_count"])
                reply_text = formatting_result["formatted_text"]
                formatted_products = formatting_result["products"]
            else:
                formatted_products = []
            
            response = {
                "reply": reply_text,
                "action": {"type": "none"},
                "intent": "product_search",
                "overview": overview,
                "structured_filters": structured_filters,
                "context_info": context_inquiry,
                "alignment": alignment,
                "auto_suggest": None
            }
            if formatted_products:
                response["structured_products"] = formatted_products
            return response
        elif context_inquiry["action"] == "confirm_search":
            # 中置信度：確認後轉換
            return {
                "reply": context_inquiry["confirmation_message"],
                "action": {"type": "none"},
                "intent": "confirmation_needed",
                "context_info": context_inquiry,
                "alignment": {
                    "intent": "product_confirm",
                    "items": [{"id": "", "name": context_inquiry["product"]}],
                    "need_confirm_show_details": True,
                    "reason": "context_product_confirmation"
                },
                "auto_suggest": None
            }
    
    # 🚀 一般意圖檢測 - 進階優化的核心
    intent = _detect_conversation_intent(normalized_message)
    _logger.debug("Detected intent: %s", intent)

    # 🛡️ OOS（超出銷售範圍）守門：如 3C 類需求，先告知不販售並展示可售範圍
    # 無論意圖如何，都應該先檢查是否為 OOS 品類
    try:
        oos_keywords = ("3c", "耳機", "手機", "平板", "電腦", "相機", "家電", "自行車", "腳踏車", "單車")
        if any(kw in normalized_message.lower() for kw in oos_keywords) and intent != "product_search":
            _logger.debug("OOS keyword detected, flagging response")
            return {
                "reply": "",
                "action": {"type": "none"},
                "intent": intent,
                "meta": _create_oos_meta(normalized_message, "keyword_block", _extract_keywords(normalized_message)),
                "display_mode": "text_only",
            }
    except Exception as e:
        _logger.error("OOS check failed: %s", e)
        pass
    
    # 📚 資訊諮詢類問題優先用 LLM 對話，不進行商品搜索
    if intent == "information":
        _logger.info("Information intent detected, using conversational LLM")
        
        # 🎨 檢測具體的意圖子類型以個性化回應
        intent_subtype = _detect_intent_subtype(normalized_message)
        system_prompt = _build_information_system_prompt(intent_subtype)
        reply_text = _call_chat_for_information(normalized_message, history, system_prompt, intent_subtype)

        keywords = _extract_keywords(normalized_message)
        structured_filters = _derive_structured_filters(normalized_message, keywords)
        structured_payload = None
        fallback_items: List[Dict[str, Any]] = []
        if structured_filters:
            fallback_items = _search_products_with_filters(normalized_message, structured_filters, limit=6)
        if not fallback_items:
            fallback_items = _search_products_with_filters(normalized_message, None, limit=6)
        if fallback_items:
            structured_payload = _build_structured_payload(fallback_items)
            reply_text = f"{reply_text}\n{json.dumps(structured_payload, ensure_ascii=False)}"
        # 🆕 資訊諮詢也進行商品格式化處理
        formatting_result = format_product_recommendations(reply_text)
        if formatting_result["product_count"] > 0:
            _logger.info("Product formatting applied to information response: %d products", formatting_result["product_count"])
            reply_text = formatting_result["formatted_text"]
            formatted_products = formatting_result["products"]
        else:
            formatted_products = []
            
        response = {
            "reply": reply_text,
            "action": {"type": "none"},
            "intent": "information",
            "intent_subtype": intent_subtype,
            "alignment": None,
            "auto_suggest": None,
            "structured_filters": structured_filters,
            "query_terms": keywords,
        }
        if structured_payload:
            response["structured_payload"] = structured_payload
        if formatted_products:
            response["structured_products"] = formatted_products
        if "health" in intent_subtype:
            response["status"] = "🩺 專業健康諮詢中"
        elif "usage" in intent_subtype:
            response["status"] = "📋 使用指導分析中"
        return response

    if _is_confirmation_message(normalized_message) and previous_alignment and previous_alignment.get("items"):
        items = previous_alignment["items"]
        
        # 🎯 檢查是否為上下文產品確認
        if previous_alignment.get("intent") == "product_confirm":
            product_name = items[0].get("name") if items else "相關商品"
            reply_text = f"好的！我來為您搜尋{product_name}。"
            action = {
                "type": "switch_to_search", 
                "query": product_name,
                "reason": "context_product_confirmed",
            }
        else:
            reply_text = "收到，我為您顯示詳細介紹與圖片。"
            action = {
                "type": "switch_to_search",
                "items": items,
                "reason": "user confirmation",
            }
        return {"reply": reply_text, "action": action, "alignment": previous_alignment}

    context = _prepare_chat_context(user_message, catalog)
    structured_filters = context.get("structured_filters") or {}
    prompt_items = context.get("matches") or catalog[:max(topn, 1)]
    system_prompt = _build_system_prompt(prompt_items)
    reply_text = _mock_or_real_llm(system_prompt, history, user_message, catalog, context)
    intent_type = _detect_query_intent(user_message)

    if context.get("oos_suspected"):
        return {
            "reply": "",
            "action": {"type": "none"},
            "intent": intent_type,
            "meta": _create_oos_meta(user_message, "whitelist_miss", context.get("keywords", [])),
            "display_mode": "text_only",
        }

    overview = context.get("overview") or {}
    products = context.get("products") or []
    alignment_payload: Optional[Dict[str, Any]] = None
    action: Dict[str, Any] = {"type": "none"}
    structured_payload: Optional[Dict[str, Any]] = None

    if overview:
        lines = []
        for idx, (topic, children) in enumerate(overview.items(), 1):
            marker = f"{idx}\u20E3"
            child_text = "、".join(children) if children else "--"
            lines.append(f"{marker} {topic}：{child_text}")
        reply_text = (
            "我們目前販售的主要商品分類如下：\n\n"
            + "\n".join(lines)
            + "\n\n想看哪一類的詳細介紹？告訴我類別或條件，我再幫您列出商品。"
        )
        # 🆕 總覽回應也進行商品格式化處理（但不切到商品模式）
        formatting_result = format_product_recommendations(reply_text)
        if formatting_result["product_count"] > 0:
            _logger.info("Product formatting applied to overview response: %d products", formatting_result["product_count"])
            reply_text = formatting_result["formatted_text"]
            formatted_products = formatting_result["products"]
        else:
            formatted_products = []
            
        response = {
            "reply": reply_text,
            "action": {"type": "none"},
            "structured_filters": structured_filters,
            "intent": "information",
            "display_mode": "text_only",
        }
        if formatted_products:
            response["structured_products"] = formatted_products
        if intent_type == "health":
            response["status"] = "🩺 專業健康諮詢中"
        elif intent_type == "usage":
            response["status"] = "📋 使用指導分析中"
        return response

    alignment_items = _build_alignment_items(products)

    if alignment_items:
        preview_names = [item["name"] for item in alignment_items if item.get("name")]
        preview_text = "、".join(preview_names[:3]) if preview_names else ""
        count = len(alignment_items)
        summary = f"我找到了 {count} 款商品"
        if preview_text:
            summary += f"，例如 {preview_text}"
        question = f"需要我顯示詳細介紹與圖片嗎？{SUGGEST_PROMPT_SUFFIX}"
        reply_text = f"{summary}。{question}"
        alignment_payload = {
            "intent": "product_align",
            "items": alignment_items,
            "need_confirm_show_details": True,
            "reason": summary,
        }

        structured_payload = _build_structured_payload(products) if products else None
        if structured_payload:
            hidden_structured = json.dumps(structured_payload, ensure_ascii=False)
            # 保持與前端定義一致：結構化資料只放在 payload，不插入文字回覆

        trigger = _should_switch_to_search(user_message, reply_text, history)
        if trigger == "explicit":
            reply_text = "了解，我立刻為您顯示詳細介紹與圖片。"
            action = {
                "type": "switch_to_search",
                "items": alignment_items,
                "reason": "user requested details",
            }
    else:
        reply_text = (
            "目前在資料中找不到符合的商品 🙏\n"
            "您可以提供品牌、類型或預算範圍嗎？我再幫您縮小範圍。"
        )
        if intent_type in ("health", "usage"):
            fallback_items = _search_products_with_filters(user_message, structured_filters, limit=6)
            if not fallback_items and products:
                fallback_items = products
            if fallback_items:
                structured_payload = _build_structured_payload(fallback_items)
                reply_text = f"{reply_text}\n{json.dumps(structured_payload, ensure_ascii=False)}"

    if alignment_payload:
        hidden_json = json.dumps(alignment_payload, ensure_ascii=False)
        # 與 structured_payload 一樣，保持在結構化欄位中，不混入純文字回覆

    # 🆕 商品格式化處理 - 自動偵測並轉換商品連結為標準格式
    formatting_result = format_product_recommendations(reply_text)
    if formatting_result["product_count"] > 0:
        _logger.info("Product formatting applied: %d products detected", formatting_result["product_count"])
        reply_text = formatting_result["formatted_text"]
        formatted_products = formatting_result["products"]
        
        # 將格式化的商品資料添加到回應中
        if "structured_products" not in locals():
            structured_products = formatted_products
        else:
            # 合併現有的結構化商品資料
            structured_products.extend(formatted_products)
    else:
        structured_products = []
    
    response: Dict[str, Any] = {"reply": reply_text, "action": action}
    if alignment_payload:
        response["alignment"] = alignment_payload
    response["query_terms"] = context.get("keywords") or []
    response["structured_filters"] = structured_filters
    if structured_payload and "structured_payload" not in response:
        response["structured_payload"] = structured_payload
    
    # 🆕 添加結構化商品資料到回應
    if structured_products:
        response["structured_products"] = structured_products

    response["intent"] = intent
    if intent == "event_food_planning":
        response_meta = response.setdefault("meta", {})
        try:
            event_ctx = parse_event_context(normalized_message)
            response_meta["event_context"] = {
                "activity_type": event_ctx.activity_type,
                "people_count": event_ctx.people_count,
                "budget_total": event_ctx.budget_total,
                "audience": event_ctx.audience,
                "keywords": event_ctx.keywords or [],
            }
            response_meta["mode"] = "event_food_planning"
        except Exception as exc:
            _logger.warning("Failed to parse event context: %s", exc)

    if intent_type == "health":
        response["status"] = "🩺 專業健康諮詢中"
    elif intent_type == "usage":
        response["status"] = "📋 使用指導分析中"
    return response

def _detect_query_intent(text: str) -> str:
    lower = (text or "").lower()
    if any(keyword in lower for keyword in USAGE_KEYWORDS):
        return "usage"
    if any(keyword in lower for keyword in HEALTH_KEYWORDS):
        return "health"
    return "general"


def _search_products_with_filters(query: str, filters: Optional[Dict[str, Any]], limit: int = 6) -> List[Dict[str, Any]]:
    try:
        from search_ext_goods_1024001 import search_products_strict
        return search_products_strict(query=query, limit=limit, filters=filters)
    except Exception:
        return []


def _short_description(text: str, limit: int = 30) -> str:
    cleaned = re.sub(r"\s+", "", (text or "").strip())
    if not cleaned:
        return ""
    return cleaned[:limit]


def _build_structured_payload(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    payload_items: List[Dict[str, Any]] = []
    for idx, item in enumerate(items, 1):
        gid = str(item.get("GoodIden") or item.get("商品編號") or item.get("id") or "").strip()
        name = str(item.get("Name") or item.get("商品名稱") or item.get("name") or "").strip()
        desc = (
            item.get("ShortDesc_20")
            or item.get("ShortDesc")
            or item.get("DESCRIPTION")
            or item.get("Description")
            or item.get("商品描述")
            or ""
        )
        desc_short = _short_description(desc, 30)
        price = str(item.get("Price_fmt") or item.get("Price") or item.get("商品價格") or "").strip()
        special = str(item.get("SpecialOffer_fmt") or item.get("SpecialOffer") or item.get("商品特價") or "").strip()
        link = str(item.get("Goods_Link1") or item.get("商品購物網址") or item.get("購物連結") or "").strip()
        image = str(item.get("Goodspic_Link1") or item.get("商品圖片網址") or item.get("商品圖片") or "").strip()
        payload_items.append({
            "index": idx,
            "商品編號": gid,
            "商品名稱": name,
            "商品描述": desc_short,
            "商品價格": price,
            "商品特價": special,
            "商品購物網址": link,
            "購物連結": link,
            "商品圖片網址": image,
            "商品圖片": image,
        })
    return {
        "summary": f"我找到 {len(payload_items)} 款商品，詳細如下：",
        "items": payload_items,
    }


# === 商品描述生成 LLM 功能 ===

# 商品描述生成配置
USE_LLM_MARKETING = os.getenv("USE_LLM_MARKETING", "False").lower() in ("1", "true", "yes")
MARKETING_MAX_LENGTH = int(os.getenv("MARKETING_MAX_LENGTH", "25"))
MARKETING_FALLBACK_MODE = os.getenv("MARKETING_FALLBACK_MODE", "smart")

# 商品類別關鍵字庫
CATEGORY_KEYWORDS = {
    'food': [
        '麥片', '燕麥', '粥', '餅乾', '茶', '咖啡', '醬', '油', '調味', 
        '有機', '營養', '維生素', '保健', '飲品', '果汁', '奶', '豆漿',
        '米', '麵', '麵條', '湯', '罐頭', '零食', '糖', '蜂蜜', '醋'
    ],
    'bag': [
        '包', '袋', '背包', '手提', '錢包', '皮夾', '收納', '斜背', 
        '後背', '托特', '多夾層', '防水', '皮革', '帆布', '尼龍',
        '拉鍊', '磁扣', '釦式', '肩背', '手拿'
    ],
    'clothing': [
        '衣', '服', '褲', '裙', '外套', '上衣', '下身', '內衣', 
        '襪子', '帽子', '圍巾', '材質', '尺寸', '棉', '絲', '毛',
        '透氣', '彈性', '防曬', '保暖', '時尚', '休閒'
    ],
    'electronics': [
        '電池', '充電', '螢幕', '音響', '耳機', '手機', '平板', 
        '電腦', '配件', '數位', '智能', 'USB', '藍牙', '無線',
        '3C', '電子', '科技', '數碼'
    ],
    'beauty': [
        '化妝', '保養', '面膜', '精華', '乳液', '洗面', '防曬',
        '香水', '指甲', '彩妝', '美容', '護膚', '清潔', '滋潤'
    ],
    'health': [
        '保健', '維他命', '膠囊', '錠', '營養', '補充', '鈣', 
        '蛋白', '益生菌', '魚油', '葡萄糖胺', '膠原蛋白'
    ]
}

# 類別化文案風格指南
CATEGORY_STYLE_GUIDES = {
    'food': {
        'tone': '健康美味',
        'keywords': ['營養', '美味', '健康', '新鮮', '天然', '香醇', '濃郁'],
        'suffix_templates': ['，{feature}好滋味', '，{benefit}好選擇', '，{quality}享美味']
    },
    'bag': {
        'tone': '實用時尚', 
        'keywords': ['實用', '便利', '時尚', '質感', '耐用', '收納', '多功能'],
        'suffix_templates': ['，{feature}好搭配', '，{benefit}好夥伴', '，{quality}展風格']
    },
    'clothing': {
        'tone': '舒適時尚',
        'keywords': ['舒適', '透氣', '時尚', '百搭', '質感', '柔軟', '彈性'],
        'suffix_templates': ['，{feature}好穿搭', '，{benefit}好選擇', '，{quality}顯魅力']
    },
    'electronics': {
        'tone': '科技便利',
        'keywords': ['智能', '便利', '高效', '精準', '耐用', '創新', '先進'],
        'suffix_templates': ['，{feature}好幫手', '，{benefit}好選擇', '，{quality}展科技']
    },
    'beauty': {
        'tone': '美麗自信',
        'keywords': ['美麗', '滋潤', '亮麗', '自然', '溫和', '持久', '清爽'],
        'suffix_templates': ['，{feature}好美麗', '，{benefit}好選擇', '，{quality}展光采']
    },
    'health': {
        'tone': '健康活力',
        'keywords': ['健康', '活力', '營養', '純淨', '天然', '溫和', '有效'],
        'suffix_templates': ['，{feature}好健康', '，{benefit}好選擇', '，{quality}享活力']
    }
}

# 預設結尾文案
DEFAULT_CATEGORY_TAILS = {
    'food': '，香濃美味好選擇',
    'bag': '，實用時尚好搭配', 
    'clothing': '，舒適百搭好穿搭',
    'electronics': '，智能便利好幫手',
    'beauty': '，美麗自信好選擇',
    'health': '，健康活力好選擇',
    'general': '，品質優選好推薦'
}

def detect_product_category(name: str, description: str) -> str:
    """
    智能檢測商品類別
    
    Args:
        name: 商品名稱
        description: 商品描述
        
    Returns:
        str: 商品類別 ('food', 'bag', 'clothing', 'electronics', 'beauty', 'health', 'general')
    """
    if not name and not description:
        return 'general'
    
    combined = (name or "").lower() + " " + (description or "").lower()
    
    # 計算各類別的匹配分數
    category_scores = {}
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in combined)
        if score > 0:
            category_scores[category] = score
    
    if not category_scores:
        return 'general'
    
    # 返回得分最高的類別
    return max(category_scores, key=category_scores.get)


def llm_generate_marketing_description(
    product_name: str, 
    original_description: str, 
    category: str = None,
    max_length: int = None
) -> str:
    """
    使用 LLM 根據原始商品資訊生成吸引人的行銷描述
    
    Args:
        product_name: 商品名稱
        original_description: 原始商品描述 (DESCRIPTION 欄位)
        category: 商品類別 (可選，會自動檢測)
        max_length: 最大長度 (預設25字)
    
    Returns:
        str: 生成的行銷描述
    """
    if not USE_LLM_MARKETING:
        return ""
    
    client = _get_client()
    if not client:
        _logger.debug("LLM client not available for marketing description generation")
        return ""
    
    if not product_name and not original_description:
        return ""
    
    # 自動檢測類別
    if not category:
        category = detect_product_category(product_name, original_description)
    
    # 取得類別風格指南
    style_guide = CATEGORY_STYLE_GUIDES.get(category, CATEGORY_STYLE_GUIDES['food'])
    
    max_len = max_length or MARKETING_MAX_LENGTH
    
    # 建構 LLM 提示詞
    prompt = f"""你是專業的商品文案寫手，請根據以下商品資訊生成吸引消費者的行銷描述。

商品名稱：{product_name or '未提供'}
商品描述：{original_description or '未提供'}
商品類別：{category}
文案風格：{style_guide['tone']}

要求：
1. 描述控制在{max_len}字以內
2. 突出商品核心特色和優勢
3. 使用吸引人的形容詞，參考關鍵詞：{', '.join(style_guide['keywords'][:5])}
4. 根據{category}類商品調整語調風格
5. 避免誇大不實的宣傳
6. 如果是{category}類商品，可參考結尾格式：{style_guide['suffix_templates'][0]}

範例格式：
- 食品類：「有機燕麥片營養滿滿，健康美味好選擇」
- 包包類：「真皮多夾層設計便利，時尚實用好搭配」  
- 服飾類：「純棉透氣材質舒適，百搭時尚好穿搭」
- 3C類：「智能藍牙高效連接，科技便利好幫手」
- 美妝類：「天然溫和滋潤配方，美麗自信好選擇」
- 保健類：「純淨營養活力補充，健康養生好選擇」

請直接回傳行銷描述，不需要其他說明。"""

    try:
        _logger.debug("Generating marketing description for %s product: %s", category, product_name[:20] if product_name else "")
        
        response = client.chat.completions.create(
            model=CHAT_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "你是專業的商品文案寫手，擅長為各類商品撰寫吸引人的行銷描述。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100,
            timeout=10
        )
        
        generated_desc = response.choices[0].message.content.strip()
        
        # 長度檢查與截斷
        if len(generated_desc) > max_len:
            generated_desc = generated_desc[:max_len-1] + "…"
        
        _logger.debug("LLM generated marketing description: %s", generated_desc)
        return generated_desc
        
    except Exception as e:
        _logger.error("LLM marketing description generation failed: %s", e)
        return ""


def generate_smart_template_description(item: Dict[str, Any]) -> str:
    """
    智能模板生成商品描述（LLM 失敗時的後備方案）
    
    Args:
        item: 商品資訊字典
        
    Returns:
        str: 生成的行銷描述
    """
    name = item.get("Name") or item.get("商品名稱") or item.get("name") or ""
    description = item.get("DESCRIPTION") or item.get("Description") or item.get("商品描述") or ""
    
    # 檢測商品類別
    category = detect_product_category(name, description)
    
    # 清理商品名稱，提取核心部分
    name_core = name
    if name_core:
        # 移除括號內容和規格
        name_core = re.sub(r"[（(].*?[)）]", "", name_core)
        name_core = re.split(r"[／/\-]", name_core)[0]
        name_core = re.sub(r"\d+(?:g|ml|包|袋|入|瓶|顆|公分|cm)", "", name_core, flags=re.IGNORECASE)
        name_core = name_core.strip()
    
    if len(name_core) > 8:
        name_core = name_core[:8]
    
    # 智能截斷，避免在詞彙中間截斷
    if len(name_core) > 8:
        truncated = name_core[:8]
        # 如果最後一個字是常見詞彙的開頭，退一個字
        if truncated.endswith(('實', '多', '前', '後', '上', '下')):
            truncated = truncated[:-1]
        name_core = truncated
    
    if not name_core:
        name_core = "精選好物"
    
    # 取得類別風格指南
    style_guide = CATEGORY_STYLE_GUIDES.get(category, CATEGORY_STYLE_GUIDES['food'])
    
    # 在商品名稱和描述中尋找特色關鍵字
    combined = (name + " " + description).lower()
    matched_features = []
    
    for keyword in style_guide['keywords']:
        if keyword in combined and keyword not in matched_features and len(matched_features) < 2:
            matched_features.append(keyword)
    
    # 如果沒有匹配到特色，使用預設特色
    if not matched_features:
        if category == 'food':
            matched_features = ['營養']
        elif category == 'bag':
            matched_features = ['實用']
        elif category == 'clothing':
            matched_features = ['舒適']
        elif category == 'electronics':
            matched_features = ['智能']
        elif category == 'beauty':
            matched_features = ['滋潤']
        elif category == 'health':
            matched_features = ['健康']
        else:
            matched_features = ['品質']
    
    # 組合描述，避免名稱核心與特色重複
    features_text = ""
    for feature in matched_features[:2]:
        # 檢查是否與名稱核心有字元重疊
        overlap = any(char in name_core for char in feature)
        if not overlap:
            features_text += feature
    
    # 如果所有特色都與名稱重複，使用預設特色
    if not features_text:
        default_features = {
            'food': '健康',
            'bag': '便利', 
            'clothing': '時尚',
            'electronics': '科技',
            'beauty': '美麗',
            'health': '安心',
            'general': '優質'
        }
        default_feature = default_features.get(category, '優質')
        # 檢查預設特色是否也重疊
        if not any(char in name_core for char in default_feature):
            features_text = default_feature
        else:
            # 使用備用特色
            backup_features = ['品質', '優選', '精選', '好物']
            for backup in backup_features:
                if not any(char in name_core for char in backup):
                    features_text = backup
                    break
            else:
                features_text = ''  # 都重疊就不加特色
    
    tail = DEFAULT_CATEGORY_TAILS.get(category, DEFAULT_CATEGORY_TAILS['general'])
    
    marketing_desc = f"{name_core}{features_text}{tail}"
    
    # 長度控制
    if len(marketing_desc) > MARKETING_MAX_LENGTH:
        marketing_desc = marketing_desc[:MARKETING_MAX_LENGTH-1] + "…"
    
    return marketing_desc


def generate_enhanced_marketing_description(item: Dict[str, Any]) -> str:
    """
    增強版商品描述生成 - 整合 LLM 與智能模板的階段式降級策略
    
    Priority:
    1. LLM 生成 (如果有 OPENAI_API_KEY 且啟用 USE_LLM_MARKETING)
    2. 智能模板生成 (根據類別和關鍵字)
    3. 基礎模板生成 (保持向後相容)
    
    Args:
        item: 商品資訊字典
        
    Returns:
        str: 生成的行銷描述
    """
    name = item.get("Name") or item.get("商品名稱") or item.get("name") or ""
    description = item.get("DESCRIPTION") or item.get("Description") or item.get("商品描述") or ""
    
    _logger.debug("Enhanced marketing description for: %s", name[:30])
    
    # 第一優先級：LLM 生成
    if USE_LLM_MARKETING and _get_client() and (name or description):
        try:
            category = detect_product_category(name, description)
            llm_result = llm_generate_marketing_description(name, description, category)
            
            if llm_result and len(llm_result.strip()) > 0:
                _logger.info("LLM marketing description generated successfully")
                return llm_result.strip()
        except Exception as e:
            _logger.warning("LLM marketing description generation failed: %s", e)
    
    # 第二優先級：智能模板生成
    if MARKETING_FALLBACK_MODE == "smart":
        try:
            smart_result = generate_smart_template_description(item)
            if smart_result:
                _logger.info("Smart template marketing description generated")
                return smart_result
        except Exception as e:
            _logger.warning("Smart template generation failed: %s", e)
    
    # 第三優先級：基礎模板（現有邏輯的改良版）
    _logger.info("Using basic template for marketing description")
    return _build_basic_marketing_description(item)


def _build_basic_marketing_description(item: Dict[str, Any]) -> str:
    """
    基礎模板商品描述生成（改良版的現有邏輯）
    """
    name = item.get("Name") or item.get("商品名稱") or item.get("name") or ""
    
    # 簡單的類別判斷，避免食品文案用在非食品商品
    category = detect_product_category(name, "")
    
    name_core = name
    if name_core:
        name_core = re.sub(r"[（(].*?[)）]", "", name_core)
        name_core = re.split(r"[／/]", name_core)[0]
        name_core = re.sub(r"\d+(?:g|ml|包|袋|入|瓶|顆)", "", name_core, flags=re.IGNORECASE)
        name_core = name_core.strip()
    
    if not name_core:
        name_core = "精選商品"
    if len(name_core) > 8:
        name_core = name_core[:8]
    
    # 根據類別選擇適當的後綴
    tail = DEFAULT_CATEGORY_TAILS.get(category, DEFAULT_CATEGORY_TAILS['general'])
    
    marketing = f"{name_core}{tail}"
    
    if len(marketing) > MARKETING_MAX_LENGTH:
        marketing = marketing[:MARKETING_MAX_LENGTH-1] + "…"
    
    return marketing


# === 商品格式化功能 ===

def format_product_recommendations(text: str) -> Dict[str, Any]:
    """
    自動偵測文字內容中的商品連結並轉換為標準格式
    
    Args:
        text: 待格式化的文字內容，可能包含商品推薦或連結
        
    Returns:
        Dict: {
            "formatted_text": str,     # 格式化後的文字
            "products": List[Dict],    # 結構化商品資料
            "product_count": int       # 商品數量
        }
    """
    if not text:
        return {"formatted_text": text, "products": [], "product_count": 0}
    
    # 1. 搜尋文字中的商品編號模式
    product_id_pattern = r"(?:商品編號|產品編號|ID)[：:\s]*([A-Za-z0-9]+)"
    product_ids = re.findall(product_id_pattern, text, re.IGNORECASE)
    
    # 2. 搜尋購物連結模式
    url_pattern = r"(?:https?://[^\s]+)|(?:www\.[^\s]+\.(?:com|tw|net|org)[^\s]*)"
    urls = re.findall(url_pattern, text)
    
    # 3. 搜尋商品名稱模式（以**包圍或明確商品關鍵字）
    product_name_pattern = r"\*\*([^*]+)\*\*|([^\s]*(?:油|醋|醬|茶|咖啡|餅乾|麥片|堅果|蜂蜜|維生素|膠囊|錠|片|粉|包|袋|瓶)[^\s]*)"
    product_names = []
    for match in re.finditer(product_name_pattern, text):
        name = match.group(1) if match.group(1) else match.group(2)
        if name and len(name) > 2:  # 過濾太短的匹配
            product_names.append(name.strip())
    
    # 4. 從資料庫搜尋相關商品
    products = []
    df = _get_chat_df()
    
    if df is not None and not df.empty:
        # 優先以商品編號搜尋
        for pid in product_ids:
            matching_rows = df[
                (df.get("GoodIden") == pid) | 
                (df.get("商品編號") == pid)
            ]
            if not matching_rows.empty:
                product = _format_single_product(matching_rows.iloc[0])
                if product:
                    products.append(product)
        
        # 再以商品名稱搜尋
        for name in product_names:
            if len(products) >= 8:  # 限制最多8個商品
                break
            
            # 檢查是否已經有相同商品
            if any(name.lower() in p.get("name", "").lower() for p in products):
                continue
                
            # 在資料庫中搜尋 - 使用 literal 參數避免正則表達式錯誤
            try:
                matching_rows = df[
                    df["Name"].str.contains(re.escape(name), case=False, na=False, regex=True) |
                    df.get("商品名稱", pd.Series()).str.contains(re.escape(name), case=False, na=False, regex=True)
                ]
            except Exception as e:
                _logger.warning("Search error for '%s': %s", name, e)
                continue
            
            if not matching_rows.empty:
                # 取最相關的一個商品
                best_match = matching_rows.iloc[0]
                product = _format_single_product(best_match)
                if product:
                    products.append(product)
    
    # 5. 生成格式化文字
    formatted_text = _generate_formatted_text(text, products)
    
    return {
        "formatted_text": formatted_text,
        "products": products,
        "product_count": len(products)
    }


def _format_single_product(row: pd.Series) -> Optional[Dict[str, Any]]:
    """
    將單一商品記錄轉換為標準格式
    
    Args:
        row: pandas Series，代表一個商品記錄
        
    Returns:
        Dict: 標準化商品資料，如果資料不完整則返回None
    """
    try:
        product_id = str(row.get("GoodIden") or row.get("商品編號") or "").strip()
        name = str(row.get("Name") or row.get("商品名稱") or "").strip()
        
        if not product_id or not name:
            return None
        
        # 使用 FieldAccessor 來確保價格格式正確
        from field_utils import FieldAccessor
        
        price = FieldAccessor.get_price(row)
        special_price = FieldAccessor.get_special_price(row)
        
        # 商品描述：優先使用短描述，否則使用完整描述
        description = (
            row.get("ShortDesc_20") or 
            row.get("ShortDesc") or 
            row.get("DESCRIPTION") or 
            row.get("Description") or 
            row.get("商品描述") or 
            "優質商品推薦"
        )
        
        # 限制描述長度
        if isinstance(description, str) and len(description) > 50:
            description = description[:47] + "..."
        
        # 購物網址
        url = (
            row.get("Goods_Link1") or 
            row.get("商品購物網址") or 
            row.get("購物連結") or 
            ""
        )
        
        # 商品圖片
        image_url = (
            row.get("Goodspic_Link1") or 
            row.get("商品圖片網址") or 
            row.get("商品圖片") or 
            ""
        )
        
        return {
            "product_id": product_id,
            "name": name,
            "description": str(description).strip(),
            "price": price if price and price > 0 else None,
            "special_price": special_price if special_price and special_price > 0 else None,
            "url": str(url).strip() if url else "",
            "image_url": str(image_url).strip() if image_url else ""
        }
        
    except Exception as e:
        _logger.exception(f"Error formatting product: {e}")
        return None


def _generate_formatted_text(original_text: str, products: List[Dict[str, Any]]) -> str:
    """
    將原始文字與商品資料結合，生成格式化的文字內容
    
    Args:
        original_text: 原始文字
        products: 商品資料列表
        
    Returns:
        str: 格式化後的文字
    """
    if not products:
        return original_text
    
    # 如果原文已經有商品格式，保持原樣
    if "【商品推薦】" in original_text or "**商品名稱**" in original_text:
        return original_text
    
    # 在原文末尾添加商品推薦區塊
    formatted_text = original_text.rstrip()
    
    if len(products) == 1:
        formatted_text += "\n\n【推薦商品】\n"
    else:
        formatted_text += "\n\n【相關商品推薦】\n"
    
    for i, product in enumerate(products, 1):
        name = product.get("name", "商品")
        description = product.get("description", "")
        price = product.get("price")
        special_price = product.get("special_price")
        url = product.get("url", "")
        
        # 價格顯示
        price_text = ""
        if special_price:
            if price:
                price_text = f"原價 ${price}，特價 ${special_price}"
            else:
                price_text = f"特價 ${special_price}"
        elif price:
            price_text = f"${price}"
        else:
            price_text = "洽詢價格"
        
        # 生成商品區塊
        product_block = f"{i}. **{name}**\n"
        if description:
            product_block += f"   {description}\n"
        product_block += f"   {price_text}"
        
        if url:
            product_block += f"\n   [立即購買]({url})"
        
        formatted_text += product_block + "\n\n"
    
    return formatted_text.rstrip()
