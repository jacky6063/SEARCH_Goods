"""LLM service using OpenAI SDK.

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
import pandas as pd
from openai import OpenAI
import logging
from goods_search_service import (
    load_data,
    search_products,
    DEFAULT_DATA_PATH,
)

_logger = logging.getLogger(__name__)

# === 搜索功能 LLM 配置 ===
SEARCH_USE_EXPAND = os.getenv("SEARCH_USE_LLM_EXPAND", os.getenv("USE_LLM_EXPAND", "False")).lower() in ("1", "true", "yes")
SEARCH_USE_SHORT = os.getenv("SEARCH_USE_LLM_SHORTDESC", os.getenv("USE_LLM_SHORTDESC", "False")).lower() in ("1", "true", "yes")
SEARCH_USE_RERANK = os.getenv("SEARCH_USE_LLM_RERANK", os.getenv("USE_LLM_RERANK", "False")).lower() in ("1", "true", "yes")
SEARCH_USE_INTENT = os.getenv("SEARCH_USE_LLM_INTENT", os.getenv("USE_LLM_INTENT", "False")).lower() in ("1", "true", "yes")
SEARCH_USE_PROMO = os.getenv("SEARCH_USE_LLM_PROMO", os.getenv("USE_LLM_PROMO", "False")).lower() in ("1", "true", "yes")
SEARCH_OPENAI_MODEL = os.getenv("SEARCH_OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

# === 聊天功能 LLM 配置 ===
CHAT_USE_EXPAND = os.getenv("CHAT_USE_LLM_EXPAND", os.getenv("USE_LLM_EXPAND", "False")).lower() in ("1", "true", "yes")
CHAT_USE_SHORT = os.getenv("CHAT_USE_LLM_SHORTDESC", os.getenv("USE_LLM_SHORTDESC", "False")).lower() in ("1", "true", "yes")
CHAT_USE_RERANK = os.getenv("CHAT_USE_LLM_RERANK", os.getenv("USE_LLM_RERANK", "False")).lower() in ("1", "true", "yes")
CHAT_USE_INTENT = os.getenv("CHAT_USE_LLM_INTENT", os.getenv("USE_LLM_INTENT", "False")).lower() in ("1", "true", "yes")
CHAT_USE_PROMO = os.getenv("CHAT_USE_LLM_PROMO", os.getenv("USE_LLM_PROMO", "False")).lower() in ("1", "true", "yes")
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

def _get_client() -> Optional[OpenAI]:
    """動態獲取 OpenAI 客戶端，支援執行時期的 API key 更新"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Debug 資訊：記錄 API key 狀態
    if not api_key:
        print(f"[DEBUG] OPENAI_API_KEY not found in environment")
        return None
    elif api_key == "your-openai-api-key":
        print(f"[DEBUG] OPENAI_API_KEY is placeholder value")
        return None
    else:
        # 只顯示前幾個字符以保護敏感資訊
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        print(f"[DEBUG] OPENAI_API_KEY found: {masked_key}")
    
    try:
        client = OpenAI(api_key=api_key)
        print(f"[DEBUG] OpenAI client created successfully")
        return client
    except Exception as e:
        print(f"[DEBUG] Failed to create OpenAI client: {e}")
        _logger.error(f"Failed to create OpenAI client: {e}")
        return None

# 保持向後相容性
_client: Optional[OpenAI] = None  # 將在首次使用時初始化
_CHAT_DF_CACHE: Optional[pd.DataFrame] = None
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

# 明確購買意圖關鍵詞
PURCHASE_INTENT_PATTERNS = [
    "我要買", "想買", "購買", "下單", "訂購", "有賣", 
    "價格", "多少錢", "便宜", "特價", "優惠", "商品"
]

# 商品推薦諮詢（介於資訊和購買之間）
RECOMMENDATION_PATTERNS = [
    "推薦", "推薦商品", "推薦好用", "哪個好", "建議", "適合"
]

# 🎯 上下文產品詢問檢測 - 混合智慧快速版
CONTEXT_INQUIRY_HIGH_CONFIDENCE = [
    "你有賣", "你們有賣", "店裡有", "有這個商品嗎", "有這個產品嗎", 
    "可以買到嗎", "哪裡買", "怎麼購買", "能買到", "有在賣"
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
    for rule in STRUCTURED_QUERY_RULES:
        rule_keywords = rule.get("keywords") or []
        if any(term.lower() in lowered_query for term in rule_keywords):
            filters["category_filter"] = rule.get("category")
            must: List[str] = []
            must.extend(rule.get("must") or [])
            female_terms = rule.get("female_terms") or []
            if female_terms and any(marker in lowered_query for marker in female_terms):
                must.extend(rule.get("female_must") or [])
            filters["must_have_keywords"] = list(dict.fromkeys([kw for kw in must if kw]))
            excluded = rule.get("excluded") or []
            if excluded:
                filters["excluded_keywords"] = list(dict.fromkeys(excluded))
            break
    return filters


def _apply_structured_filters(records: List[Dict[str, Any]], filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not records or not filters:
        return records
    category_filter = (filters.get("category_filter") or "").lower()
    must_keywords = [kw.lower() for kw in filters.get("must_have_keywords") or [] if kw]
    excluded_keywords = [kw.lower() for kw in filters.get("excluded_keywords") or [] if kw]
    filtered: List[Dict[str, Any]] = []
    for item in records:
        name = str(item.get("Name") or item.get("商品名稱") or item.get("name") or "").lower()
        category = str(item.get("CateName") or item.get("分類名稱") or item.get("category") or "").lower()
        haystack = " ".join([
            name,
            category,
            str(item.get("DESCRIPTION") or item.get("Description") or item.get("ShortDesc") or ""),
        ]).lower()
        if category_filter and category_filter not in category:
            continue
        if must_keywords and not all(kw in haystack for kw in must_keywords):
            continue
        if excluded_keywords and any(kw in haystack for kw in excluded_keywords):
            continue
        filtered.append(item)
    return filtered


def _search_products_for_chat(
    query: str, keywords: List[str], topn: int = 5, filters: Optional[Dict[str, Any]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    result = {"exact": [], "fuzzy": []}
    if not query:
        return result
    try:
        df = _get_chat_df()
        if df is None or df.empty:
            return result

        fuzzy_records, _ = search_products(
            df,
            query,
            topn=topn,
            sort_price=True,
        )
        filtered_fuzzy = _apply_structured_filters(fuzzy_records or [], filters)
        if filters and not filtered_fuzzy:
            try:
                from search_ext_goods_1024001 import search_products_strict
                filtered_fuzzy = search_products_strict(query=query, limit=topn, filters=filters) or []
            except Exception:
                filtered_fuzzy = []
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


def llm_analyze_query(query: str, system_prompt: Optional[str] = None, use_search_config: bool = True) -> Dict[str, Any]:
    """分析查詢意圖，可指定使用搜索或聊天配置"""
    use_intent = SEARCH_USE_INTENT if use_search_config else CHAT_USE_INTENT
    model = SEARCH_OPENAI_MODEL if use_search_config else CHAT_OPENAI_MODEL
    
    client = _get_client()
    if not use_intent or not client or not query:
        return {}
    default_prompt = (
        "你是一個商品搜尋意圖解析器。輸入是使用者的自然語言需求，請輸出 JSON，包含：\n"
        "required_terms: 使用者必須條件（陣列，例如 ['無調味','核桃']）\n"
        "category_terms: 建議搜尋分類或種類（陣列，例如 ['堅果','零食']）\n"
        "excluded_terms: 應排除的詞（陣列）\n"
        "notes: 其他補充（字串）。若無明確資訊對應欄位請給空陣列或空字串。"
    )
    system_prompt = _merge_prompt(system_prompt, default_prompt)
    prompt = f"請解析以下需求並輸出 JSON（不需要多餘文字）：\n{query}"
    raw = _call_chat(prompt, system=system_prompt, model=model, max_tokens=200)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        try:
            content = raw[raw.find('{'):raw.rfind('}')+1]
            return json.loads(content)
        except Exception:
            _logger.warning("failed to parse llm intent json: %s", raw)
            return {}


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
    
    client = _get_client()
    if not use_expand or not client or not query:
        return query
    prompt = (
        f"請將使用者查詢盡量擴展成同義、相關或可能的搜尋詞組（以逗號分隔），輸出為一行，不要多餘說明。\n輸入：{query}\n輸出："
    )
    system = _merge_prompt(system_prompt, "你是一個搜尋查詢擴展工具（用繁體中文回應）")
    out = _call_chat(prompt, system=system, model=model, max_tokens=80)
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
    Minimal wrapper that falls back to a demo response when OpenAI credentials are not configured.
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
    print(f"[DEBUG] _mock_or_real_llm called, checking client...")

    if context.get("overview"):
        print(f"[DEBUG] Using mock reply due to overview context")
        return mock_reply

    client = _get_client()
    if not client:
        print(f"[DEBUG] No OpenAI client available, using mock reply")
        return mock_reply
    
    print(f"[DEBUG] OpenAI client available, proceeding with real LLM call...")

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(safe_history[-10:])  # avoid excessively long prompts
    messages.append({"role": "user", "content": user_message})

    try:
        print(f"[DEBUG] Making OpenAI API call with model: {CHAT_OPENAI_MODEL}")
        res = client.chat.completions.create(
            model=CHAT_OPENAI_MODEL,  # 使用聊天專用模型
            messages=messages,
            max_tokens=320,
            temperature=0.4,
        )
        print(f"[DEBUG] OpenAI API call successful")
        if res and res.choices:
            reply_text = (res.choices[0].message.content or "").strip()
            print(f"[DEBUG] LLM reply received: {reply_text[:100]}...")
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
                    print(f"[DEBUG] LLM reply contains negative markers, using mock reply")
                    return mock_reply
                return reply_text
    except Exception as exc:
        print(f"[DEBUG] OpenAI API call failed: {exc}")
        _logger.exception("Chat completion failed: %s", exc)
    
    print(f"[DEBUG] Fallback to mock reply")
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


def _detect_context_product_inquiry(user_message: str, history: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """
    🎯 混合智慧上下文產品詢問檢測器 - 快速版
    
    Returns:
        None: 非上下文產品詢問
        Dict: {
            "action": "direct_search" | "confirm_search",
            "query": str,
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
    
    # 2. 提取上下文產品 (最近4輪對話)
    recent_content = " ".join([
        msg.get("content", "") for msg in history[-4:] if isinstance(msg, dict)
    ])
    all_context = recent_content + " " + user_message
    
    # 3. 匹配產品關鍵詞
    matched_products = []
    for keyword in CORE_PRODUCT_KEYWORDS:
        if keyword in all_context:
            matched_products.append(keyword)
    
    if not matched_products:
        return None
    
    # 4. 選擇目標產品（最後提到的）
    target_product = matched_products[-1]
    
    # 5. 根據置信度決策
    if confidence >= 0.8:
        # 高置信度：直接轉換為產品搜索
        return {
            "action": "direct_search",
            "query": target_product,
            "product": target_product,
            "confidence": confidence,
            "matched_products": matched_products,
            "inquiry_type": inquiry_type
        }
    else:
        # 中置信度：確認後轉換
        return {
            "action": "confirm_search",
            "product": target_product, 
            "confidence": confidence,
            "matched_products": matched_products,
            "inquiry_type": inquiry_type,
            "confirmation_message": f"您是想了解{target_product}的商品資訊嗎？我可以為您搜尋相關產品。"
        }


def _detect_conversation_intent(query: str) -> str:
    """檢測對話意圖: 'information' | 'product_search' | 'general'"""
    if not query:
        return "general"
    
    query_lower = query.lower()
    
    # 檢查是否為資訊諮詢（優先級最高）
    for intent_type, patterns in INFORMATION_INTENT_PATTERNS.items():
        if any(pattern in query_lower for pattern in patterns):
            return "information"
    
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
    if wants_overview:
        product_search = {"exact": [], "fuzzy": []}
        exact_products = []
        fuzzy_products = []
        products = []
        categories = list(CHAT_CATEGORY_TOPICS.keys())
        matches = []
    else:
        product_search = _search_products_for_chat(query, keywords, topn=6, filters=structured_filters)
        exact_products = _dedupe_products(product_search.get("exact", []), 4)
        fuzzy_products = _dedupe_products(product_search.get("fuzzy", []), 6)
        products = exact_products or _filter_products_by_keywords(fuzzy_products, keywords)
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

    return f"目前尚未找到符合的商品，不過我們持續補貨中，也可告訴我其他需求。需要我顯示詳細介紹與圖片嗎？{SUGGEST_PROMPT_SUFFIX}"


def _build_system_prompt(catalog: List[Dict[str, Any]]) -> str:
    lines = [
        CSV_ONLY_SYSTEM_PROMPT,
        "",
        "你是「哈通友善生活館」的客服銷售員，熟悉上架商品。",
        "原則：",
        "1) 架上有顧客要的商品：主動推薦並清楚告知特價資訊（若有）。",
        "2) 請把商品描述優化為簡短行銷文案（≤25字，自然不浮誇）。",
        "3) 回覆末段一定要詢問：是否需要看詳細介紹與圖片？",
        "4) 查無符合商品：禮貌婉謝，歡迎下次再來。",
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
    print(f"[DEBUG] USE_CHAT_MODE = {chat_mode}")
    
    if chat_mode not in ("true", "1", "yes"):
        print(f"[DEBUG] Chat mode disabled, returning mock response")
        return {"reply": "聊天模式目前未啟用。", "action": {"type": "none"}}

    print(f"[DEBUG] chat_reply called with message: {user_message[:50]}...")
    history = history or []
    catalog = catalog or []
    normalized_message = (user_message or "").strip()
    previous_alignment = _extract_alignment_from_history(history)

    # 🎯 優先檢測上下文產品詢問 - 混合智慧核心
    context_inquiry = _detect_context_product_inquiry(normalized_message, history)
    if context_inquiry:
        print(f"[INFO] Context product inquiry detected: {context_inquiry['action']} for {context_inquiry['product']}")
        
        if context_inquiry["action"] == "direct_search":
            # 高置信度：直接轉換為產品搜索
            return {
                "reply": f"好的！我來為您搜尋{context_inquiry['product']}的相關商品。",
                "action": {
                    "type": "switch_to_search",
                    "query": context_inquiry["query"],
                    "reason": "context_product_search"
                },
                "intent": "context_product_search",
                "context_info": context_inquiry,
                "alignment": None,
                "auto_suggest": None
            }
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
    print(f"[DEBUG] Detected intent: {intent}")
    
    # 📚 資訊諮詢類問題優先用 LLM 對話，不進行商品搜索
    if intent == "information":
        print(f"[INFO] Information intent detected, using conversational LLM")
        
        # 🎨 檢測具體的意圖子類型以個性化回應
        intent_subtype = _detect_intent_subtype(normalized_message)
        system_prompt = _build_information_system_prompt(intent_subtype)
        reply_text = _call_chat_for_information(normalized_message, history, system_prompt, intent_subtype)
        
        return {
            "reply": reply_text,
            "action": {"type": "none"},  # 不觸發商品搜索模式
            "intent": "information",
            "intent_subtype": intent_subtype,  # 新增子類型資訊
            "alignment": None,
            "auto_suggest": None
        }

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

    overview = context.get("overview") or {}
    products = context.get("products") or []
    alignment_payload: Optional[Dict[str, Any]] = None
    action: Dict[str, Any] = {"type": "none"}

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
        return {
            "reply": reply_text,
            "action": action,
            "structured_filters": structured_filters,
        }

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

    if alignment_payload:
        hidden_json = json.dumps(alignment_payload, ensure_ascii=False)
        reply_text = f"{reply_text}\n{hidden_json}"

    response: Dict[str, Any] = {"reply": reply_text, "action": action}
    if alignment_payload:
        response["alignment"] = alignment_payload
    response["query_terms"] = context.get("keywords") or []
    response["structured_filters"] = structured_filters
    return response
