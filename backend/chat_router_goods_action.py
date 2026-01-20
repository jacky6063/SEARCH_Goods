from fallback.multi_category_party import run_fallback
from typing import Any, Dict, List, Optional, Sequence, Tuple
from fastapi import APIRouter
from pydantic import BaseModel
from utils.llm_guard import safe_call_async
from utils.simple_extract import extract_budget_and_cats
from planner import (
    DetectedIntent,
    detect_intent as planner_detect_intent,
    build_plan as planner_build_plan,
    compose_plan_payload as planner_compose_payload,
)
__LLM_GUARD_INSTALLED__ = True
from search_ext_goods_1024001 import search_products_strict, infer_filters_from_query
from goods_search_service import search_products_with_hierarchy
from field_utils import FieldAccessor
from modes.shopping_recommender import prepare_shopping_response
from modes.marketing_consultant import prepare_information_response
import uuid
import time
import re
import json
import html
import difflib
from conversation_core import (
    ConversationInput,
    ConversationContext,
    IntentDecision,
    HandlerResult,
    ConversationHandler,
    IntentRouter,
    ConversationOrchestrator,
)
from services import bundle_service, catalog_service, categories_service
from services.search_service import (
    is_negative_query,
    NEGATIVE_QUERY_MESSAGE,
)
from chat_logging import (
    ChatLoggingError,
    log_recommendations as supabase_log_recommendations,
)
from chat_logging_bridge import ChatLoggingBridge
from supabase_client import SupabaseConfigError
from utils.logging_utils import get_logger

# 🆕 匯入公司簡介服務
LOGGER = get_logger(__name__)
try:
    from company_profile_service import get_company_profile_service
    from company_response_formatter import get_company_response_formatter
    COMPANY_PROFILE_AVAILABLE = True
except ImportError:
    COMPANY_PROFILE_AVAILABLE = False
    LOGGER.warning("Company profile service not available")


CHAT_LOGGING_BRIDGE = ChatLoggingBridge(
    module_type="goods",
    channel="chat_api",
    logger=LOGGER,
)


def _clean_text(value: Optional[str]) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"[，,。．\.；;！!／/、\\|（）()【】［］\[\]]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _looks_like_product_id_query(text: Optional[str]) -> bool:
    """輕量封裝，避免在聊天流程中重複商品編號判斷邏輯。"""
    if not text:
        return False
    try:
        from goods_search_service import is_product_id_query as _public_id_check
    except ImportError:
        try:
            from goods_search_service import _is_product_id_query as _public_id_check  # type: ignore
        except ImportError:
            return False
    try:
        return bool(_public_id_check(text))
    except Exception:
        return False


def _select_marketing_tail(name: str, description: str) -> str:
    combined = (name or "") + " " + (description or "")
    for keyword, tail in MARKETING_TAILS:
        if keyword and keyword in combined:
            return tail
    return "，香濃暖胃好活力"


def _build_marketing_description(item: Dict[str, Any]) -> str:
    """
    建構商品行銷描述
    
    優先順序：
    1. 使用 LLM 增強版描述生成（如果啟用）
    2. 降級到原有邏輯
    """
    try:
        # 嘗試使用 LLM 增強版描述生成
        from llm_service import generate_enhanced_marketing_description
        enhanced_desc = generate_enhanced_marketing_description(item)
        if enhanced_desc and enhanced_desc.strip():
            return enhanced_desc
    except ImportError:
        LOGGER.warning("LLM service not available, using basic marketing description")
    except Exception as e:
        LOGGER.warning("Enhanced marketing description generation failed: %s", e)
    
    # 降級到原有邏輯（略作改良以避免食品文案用在非食品商品）
    return _build_basic_marketing_description_fallback(item)


def _build_basic_marketing_description_fallback(item: Dict[str, Any]) -> str:
    """
    基礎商品描述生成（原有邏輯的改良版）
    """
    name = _clean_text(FieldAccessor.get_name(item))
    desc_candidates = [
        item.get("ShortDesc_20"),
        item.get("ShortDesc"),
        item.get("商品描述"),
        item.get("DESCRIPTION"),
        item.get("Description"),
        item.get("備註"),
    ]
    raw_desc = ""
    for candidate in desc_candidates:
        cleaned = _clean_text(candidate)
        if cleaned:
            raw_desc = cleaned
            break
    combined = (raw_desc or "") + (name or "")

    # 簡單商品類別判斷
    is_food = any(kw in combined.lower() for kw in [
        "麥片", "燕麥", "粥", "餅乾", "茶", "咖啡", "醬", "油", "調味", 
        "有機", "營養", "維生素", "保健", "飲品"
    ])
    is_bag = any(kw in combined.lower() for kw in [
        "包", "袋", "背包", "手提", "錢包", "皮夾", "收納", "斜背", "多夾層"
    ])
    is_clothing = any(kw in combined.lower() for kw in [
        "衣", "服", "褲", "裙", "外套", "上衣", "材質", "尺寸"
    ])

    name_core = name or ""
    if name_core:
        name_core = re.sub(r"[（(].*?[)）]", "", name_core)
        name_core = re.split(r"[／/]", name_core)[0]
        name_core = re.sub(r"\d+(?:g|ml|包|袋|入|瓶|顆)", "", name_core, flags=re.IGNORECASE)
        name_core = name_core.strip()
    if not name_core:
        name_core = "人氣好物"
    if len(name_core) > 8:
        name_core = name_core[:8]

    feature_map = [
        ("有機", "有機安心"),
        ("全穀", "全穀纖維"),
        ("多穀", "多穀營養"),
        ("高纖", "高纖滿滿"),
        ("低糖", "低糖無負擔"),
        ("無糖", "無糖輕盈"),
        ("即食", "即沖即享"),
        ("即沖", "即沖即享"),
        ("濃郁", "濃郁香醇"),
        ("滑順", "滑順順口"),
        ("酥脆", "酥脆好口感"),
        ("香脆", "香脆好口感"),
        ("植物", "植物好選"),
        ("多夾層", "收納便利"),
        ("真皮", "質感升級"),
        ("防水", "安心防護"),
        ("舒適", "穿著舒適"),
        ("透氣", "透氣清爽"),
    ]
    
    features: List[str] = []
    for keyword, phrase in feature_map:
        if keyword in combined and phrase not in features:
            features.append(phrase)
        if len(features) >= 2:
            break

    if not features:
        if is_food:
            if any(kw in combined for kw in ["麥片", "燕麥"]):
                features.append("高纖滿滿")
            elif "粥" in combined:
                features.append("暖胃即享")
            else:
                features.append("營養美味")
        elif is_bag:
            features.append("實用便利")
        elif is_clothing:
            features.append("舒適時尚")
        else:
            features.append("品質優選")

    body = name_core + "".join(features[:2])
    
    # 根據商品類型選擇合適的結尾
    if is_food:
        tail = _select_marketing_tail(name, raw_desc)  # 原有的食品專用邏輯
    elif is_bag:
        tail = "，時尚實用好搭配"
    elif is_clothing:
        tail = "，舒適百搭好穿搭"
    else:
        tail = "，品質優選好推薦"
    
    marketing = (body + tail).strip()
    if not marketing:
        if is_food:
            marketing = f"{name_core}香濃暖胃好活力"
        elif is_bag:
            marketing = f"{name_core}實用時尚好搭配"
        elif is_clothing:
            marketing = f"{name_core}舒適百搭好穿搭"
        else:
            marketing = f"{name_core}品質優選好推薦"
    
    if len(marketing) > 30:
        marketing = marketing[:30]
    return marketing


def _extract_budget_from_query(user_query: str) -> Optional[Dict[str, Optional[int]]]:
    """從用戶查詢中提取預算區間，回傳 {min, max}"""
    import re
    if not user_query:
        return None

    text = str(user_query)
    range_patterns = [
        r'(\d+)\s*[~\-–—]\s*(\d+)\s*元?',  # 3000~4000 / 3000-4000
    ]
    max_only_patterns = [
        r'(\d+)\s*元.*?(以下|內)',
        r'上限\s*(\d+)\s*元',
        r'不超過\s*(\d+)\s*元',
    ]
    exact_patterns = [
        r'預算\s*(\d+)\s*元',
        r'(\d+)\s*元',
    ]

    for pattern in range_patterns:
        match = re.search(pattern, text)
        if match:
            lo = int(match.group(1))
            hi = int(match.group(2))
            if lo > hi:
                lo, hi = hi, lo
            return {"min": lo, "max": hi}

    for pattern in max_only_patterns:
        match = re.search(pattern, text)
        if match:
            value = int(next(g for g in match.groups() if g and g.isdigit()))
            return {"min": None, "max": value}

    for pattern in exact_patterns:
        match = re.search(pattern, text)
        if match:
            value = int(match.group(1))
            return {"min": value, "max": value}

    return None

def _build_user_friendly_reply(items: List[Dict[str, Any]], user_query: str, structured: Dict[str, Any]) -> str:
    """建立用戶友好的回覆格式"""
    if not items:
        return "很抱歉，沒有找到符合您需求的商品。"
    
    # 提取預算資訊
    budget = _extract_budget_from_query(user_query)
    safe_query = _sanitize_text(user_query)
    
    # 建立開場白
    if user_query:
        opening = f"根據您的需求「{safe_query}」，我為您找到了 {len(items)} 款相關商品。\n\n推薦商品包括：\n"
    else:
        opening = f"我為您找到了 {len(items)} 款商品。\n\n推薦商品包括：\n"
    
    # 顯示所有商品的完整資訊
    product_details: List[str] = []
    for idx, item in enumerate(items, 1):
        gid = _sanitize_text(FieldAccessor.get_product_id(item))
        name = _sanitize_text(FieldAccessor.get_name(item))
        price = _sanitize_text(FieldAccessor.get_price(item) or "")
        special = _sanitize_text(FieldAccessor.get_special_price(item) or "")
        link = FieldAccessor.get_shop_url(item) or ""
        marketing = _sanitize_text(_build_marketing_description(item))
        lines = [
            f"{idx}. 商品編號：{gid}",
            f"   商品名稱：{name}",
            f"   商品描述：{marketing}",
            f"   商品價格：{price}",
        ]
        if special:
            lines.append(f"   商品特價：{special}")
        if link:
            escaped = html.escape(link, quote=True)
            lines.append(f"   購物連結：<a href=\"{escaped}\" target=\"_blank\" rel=\"noopener noreferrer\">🛒 前往購買</a>")
        else:
            lines.append("   購物連結：—")
        product_details.append("\n".join(lines))
    
    # 組合商品詳細資訊
    products_section = "\n".join(product_details)
    
    # 建立預算確認和引導語句
    budget_section = ""
    if budget:
        min_val = budget.get("min")
        max_val = budget.get("max")
        if min_val is not None and max_val is not None:
            if min_val == max_val:
                budget_section = f"\n考量到您 {min_val} 元的預算，我已為您篩選適合的選項。\n"
            else:
                budget_section = f"\n考量到您 {min_val}~{max_val} 元的預算，我已為您篩選適合的選項。\n"
        elif max_val is not None:
            budget_section = f"\n考量到您 {max_val} 元以下的預算，我已為您篩選適合的選項。\n"
        elif min_val is not None:
            budget_section = f"\n考量到您 {min_val} 元以上的預算，我已為您篩選適合的選項。\n"
    
    guidance = "\n需要我顯示詳細商品資訊與圖片嗎？也歡迎告訴我更具體的需求！"
    
    return opening + products_section + budget_section + guidance

def _build_structured_items(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = f"{len(items)} 款商品"
    payload_items: List[Dict[str, Any]] = []
    lines: List[str] = []
    for idx, item in enumerate(items, 1):
        gid = _sanitize_text(FieldAccessor.get_product_id(item))
        name = _sanitize_text(FieldAccessor.get_name(item))
        price = _sanitize_text(FieldAccessor.get_price(item) or "")
        special = _sanitize_text(FieldAccessor.get_special_price(item) or "")
        link = FieldAccessor.get_shop_url(item) or ""
        image = FieldAccessor.get_image_url(item) or ""
        marketing = _sanitize_text(_build_marketing_description(item))

        entry_lines = [
            f"{idx}. 商品編號：{gid}",
            f"   商品名稱：{name}",
            f"   商品描述：{marketing}",
            f"   商品價格：{price}",
        ]
        if special:
            entry_lines.append(f"   商品特價：{special}")
        if link:
            escaped = html.escape(link, quote=True)
            entry_lines.append(f"   購物連結：<a href=\"{escaped}\" target=\"_blank\" rel=\"noopener noreferrer\">🛒 前往購買</a>")
        else:
            entry_lines.append("   購物連結：—")
        lines.append("\n".join(entry_lines))

        payload_items.append({
            "index": idx,
            "商品編號": gid,
            "商品名稱": name,
            "商品描述": marketing,
            "商品價格": price,
            "商品特價": special,
            "商品購物網址": link,
            "購物連結": link,
            "商品圖片網址": image,
            "商品圖片": image,
        })
    return {
        "summary": summary,
        "items": payload_items,
        "text_lines": lines,
    }


def _compose_structured_reply(items: List[Dict[str, Any]], include_suffix: bool = True, user_query: str = "") -> Tuple[str, Dict[str, Any]]:
    if not items:
        return "", {"summary": "", "items": []}

    normalized_query = (user_query or "").lower()
    expected_aliases: List[str] = []
    for aliases in QUERY_CATEGORY_HINTS.values():
        for alias in aliases:
            alias_lc = alias.lower()
            if alias_lc and alias_lc in normalized_query:
                expected_aliases.append(alias)

    warning = ""
    if expected_aliases:
        alias_lc_set = {alias.lower() for alias in expected_aliases}
        match_found = False

        # 🔧 改進：同時檢查 REMARK 欄位中的商品分類標籤
        for item in items:
            text = " ".join(
                [
                    FieldAccessor.get_category(item),
                    FieldAccessor.get_name(item),
                    FieldAccessor.get_description(item),
                    str(item.get("REMARK") or item.get("備註") or ""),  # 新增 REMARK 檢查
                ]
            ).lower()
            if any(alias in text for alias in alias_lc_set):
                match_found = True
                break
        if not match_found:
            keyword_text = _sanitize_text("、".join(dict.fromkeys(expected_aliases)))
            warning = (
                f"提醒：目前資料中未明確標示「{keyword_text}」分類，"
                "若結果不符合可再提供品牌、款式或其他描述，我再幫你重新查詢。"
            )

    structured = _build_structured_items(items)
    
    # 🔧 建立用戶友好的回覆格式
    user_friendly_reply = _build_user_friendly_reply(items, user_query, structured)
    
    # structured_payload 另由呼叫端帶回，不需要在聊天文字中出現 JSON
    suffix = f"\n\n{SUGGEST_PROMPT_SUFFIX}" if include_suffix and SUGGEST_PROMPT_SUFFIX else ""
    if warning:
        reply_text = f"{warning}\n\n{user_friendly_reply}{suffix}"
    else:
        reply_text = f"{user_friendly_reply}{suffix}"
    return reply_text, structured


def _fetch_items_for_reply(prefetched: Optional[List[Dict[str, Any]]], suggestion_ids: List[str]) -> List[Dict[str, Any]]:
    """取得完整欄位的商品列表，若沒有預取資料則回到資料服務查詢。"""
    items = prefetched or []
    if items:
        return items
    if not suggestion_ids:
        return []
    try:
        return catalog_service.get_items_by_ids(suggestion_ids)
    except Exception as exc:
        LOGGER.warning("Failed to fetch full product data: %s", exc)
        return []


def _invoke_category_planner(intent: Optional[DetectedIntent]) -> Optional[Dict[str, Any]]:
    """
    呼叫通用規劃器以補齊建議。
    以防止任何例外影響主要流程，所有錯誤都捕捉並記錄。
    """
    if not intent:
        return None
    if not intent.categories and not intent.budget:
        return None
    try:
        df = catalog_service.get_dataframe()
        plan_result = planner_build_plan(intent, df)
        return planner_compose_payload(plan_result)
    except Exception as exc:
        LOGGER.warning("Category planner failed: %s", exc)
        return None


def _merge_planner_reply(base_reply: str, planner_payload: Dict[str, Any], planner_suggestions: List[str]) -> str:
    """
    將 planner 產出的資訊附加到原始回覆中。
    """
    reply_lines: List[str] = []
    if base_reply:
        reply_lines.append(base_reply.strip())

    structured = planner_payload.get("structured_payload") or {}
    categories = structured.get("categories") or {}

    if categories:
        reply_lines.append("")
        reply_lines.append("以下是依據您的需求補充的品類建議：")
        for category, info in categories.items():
            allocated = info.get("allocated_budget")
            subtotal = info.get("subtotal")
            items = info.get("items", []) or []
            header = f"- {category}"
            if allocated:
                header += f"（預算 {allocated} 元"
                if subtotal:
                    header += f"，目前約 {subtotal} 元"
                header += "）"
            reply_lines.append(header)
            for item in items[:3]:
                name = FieldAccessor.get_name(item)
                price = FieldAccessor.get_price(item)
                reply_lines.append(f"   • {name} - {price or '—'} 元")

    if planner_suggestions:
        reply_lines.append("")
        reply_lines.append("提醒：")
        for tip in planner_suggestions:
            reply_lines.append(f"• {tip}")

    return "\n".join(line for line in reply_lines if line).strip()


router = APIRouter()

# 聊天會話結果快取
CHAT_SESSION_CACHE = {}
CACHE_TTL = 300  # 5 分鐘 TTL


def _clear_chat_session_cache(session_id: Optional[str] = None) -> None:
    if session_id is None:
        CHAT_SESSION_CACHE.clear()
        return
    CHAT_SESSION_CACHE.pop(session_id, None)

AGREE_WORDS = {"要","ok","OK","Ok","好","可以","行","確定","沒問題","那就這些","都可以","ＯＫ","Ｏk","ｏｋ"}
SUGGEST_PROMPT_SUFFIX = "也可輸入 1=原建議、2=特價關聯、3=智慧搭配。"

QUERY_CATEGORY_HINTS: Dict[str, List[str]] = {
    "包": ["包", "包包", "晚宴包", "手提包", "背包", "肩背包", "斜背包", "側背包", "手拿包", "小包", "中包", "隨身單品"],
    "鞋": ["鞋", "鞋子", "運動鞋", "球鞋", "休閒鞋", "皮鞋"],
    "衣": ["外套", "上衣", "襯衫", "洋裝", "褲", "襪", "衣服"],
}

L2_HINTS_BY_L1: Dict[str, Dict[str, List[str]]] = {
    "時尚女性": {
        "女用皮包": QUERY_CATEGORY_HINTS["包"] + ["皮包", "手提包", "肩背包", "背包"],
    },
    "常溫食品": {
        "五穀/豆類/米麵/乾貨": ["米", "米類", "豆包", "豆腐", "米麵", "米飯", "穀物", "佐醬", "湯料", "乾貨"],
        "零食/餅乾/點心": ["零食", "點心", "餅乾", "零食點心", "小食", "糖果"],
    },
}
L3_FALLBACKS_BY_L1_L2: Dict[str, Dict[str, List[str]]] = {
    "常溫食品": {
        "五穀/豆類/米麵/乾貨": ["米類", "豆包", "豆腐", "佐醬湯料", "乾貨", "米麵"],
    },
    "時尚女性": {
        "女用皮包": ["女用背包", "背包", "手提包", "肩背包", "斜背包", "側背包", "手拿包", "小包", "中包"],
    },
}
MARKETING_TAILS = [
    ("麥片", "，晨起元氣好選擇"),
    ("燕麥", "，守護輕盈好體態"),
    ("粥", "，暖胃即食好滋味"),
    ("餅乾", "，酥脆共享好時光"),
    ("飲料", "，清爽補水好滿足"),
    ("茶", "，溫潤放鬆好時刻"),
    ("咖啡", "，香醇醒神好夥伴"),
]

FALLBACK_STATUS_MESSAGE = "已提供方向建議，請補充更明確需求。"


def _sanitize_text(value: Any) -> str:
    """防止輸出 HTML 時被插入惡意內容"""
    if value is None:
        return ""
    return html.escape(str(value).strip())

def has_budget_intent(text: str) -> bool:
    import re
    t = (text or "").strip()
    kw = re.compile(r"(預算|多少錢|多少元|價位|上限|便宜|貴不貴|價格)")
    money = re.compile(r"(\d[\d,\.]*)(\s*)(元|塊|\$)")
    return bool(kw.search(t) or money.search(t))

class ChatReq(BaseModel):
    message: str  # 改為與前端一致的欄位名稱
    text: Optional[str] = None  # 向後相容
    history: Optional[List[Dict]] = None
    topn: Optional[int] = 8
    session_id: Optional[str] = None
    voice_mode: Optional[bool] = False  # 🎙️ 語音模式標記
    action: Optional[Dict[str, Any]] = None  # 🔥 前端動作描述 (ex: 熱門分類點擊)
    flags: Optional[Dict[str, Any]] = None   # 🔖 輕量旗標 (ex: from_hot_category)
    
    @property
    def user_message(self):
        """統一的訊息存取方式"""
        return self.message or self.text or ""
    
    @property
    def safe_history(self) -> List[Dict]:
        """避免共用同一個預設 list"""
        return list(self.history) if self.history else []


CHAT_CHANNEL = "chat_api"
_DEFAULT_MODULE = "goods"


def _extract_recommendations(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    sources: List[Sequence[Dict[str, Any]]] = []
    for key in ("items", "structured_products"):
        items = payload.get(key)
        if isinstance(items, list) and items:
            sources.append(items)
    structured_payload = payload.get("structured_payload")
    if isinstance(structured_payload, dict):
        items = structured_payload.get("items")
        if isinstance(items, list) and items:
            sources.append(items)

    results: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for collection in sources:
        for item in collection:
            if not isinstance(item, dict):
                continue
            product_id = (
                item.get("product_id")
                or FieldAccessor.get_product_id(item)
                or item.get("id")
            )
            name = (
                item.get("product_name")
                or FieldAccessor.get_name(item)
                or item.get("name")
            )
            if not product_id or not name or product_id in seen:
                continue
            seen.add(product_id)
            results.append(
                {
                    "product_id": product_id,
                    "product_name": name,
                    "source_rank": len(results) + 1,
                }
            )
    return results


def _log_recommendations_for_payload(
    assistant_record: Optional[Dict[str, Any]],
    payload: Dict[str, Any],
) -> None:
    if not assistant_record:
        return
    message_id = assistant_record.get("message_id")
    session_id = assistant_record.get("session_id")
    if not message_id or not session_id:
        return
    recs = _extract_recommendations(payload)
    if not recs:
        return
    try:
        supabase_log_recommendations(
            session_id=session_id,
            message_id=message_id,
            recommendations=recs,
        )
    except (SupabaseConfigError, ChatLoggingError) as exc:
        LOGGER.debug("Skip recommendation log: %s", exc)

def _cleanup_session_cache() -> None:
    """清理過期的聊天會話快取"""
    current_time = time.time()
    expired_sessions = [
        session_id for session_id, (timestamp, _) in CHAT_SESSION_CACHE.items()
        if current_time - timestamp > CACHE_TTL
    ]
    for session_id in expired_sessions:
        del CHAT_SESSION_CACHE[session_id]

def get_chat_result_by_session(session_id: str) -> Optional[Dict[str, Any]]:
    """根據會話 ID 獲取聊天結果"""
    _cleanup_session_cache()
    if session_id in CHAT_SESSION_CACHE:
        timestamp, result = CHAT_SESSION_CACHE[session_id]
        return result
    return None

def _store_chat_result(result: Dict[str, Any]) -> str:
    """儲存聊天結果並回傳會話 ID"""
    if not result.get("category_suggestions") and not result.get("suggestion_ids"):
        return None
        
    session_id = str(uuid.uuid4())
    CHAT_SESSION_CACHE[session_id] = (time.time(), {
        "category_suggestions": result.get("category_suggestions"),
        "suggestion_ids": result.get("suggestion_ids", []),
        "action": result.get("action"),
        "meta": result.get("meta", {}),
    })
    return session_id


def _finalize_text_only_fallback(
    base: Dict[str, Any],
    *,
    reply: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """強制將回退結果轉成純文字狀態並寫入會話快取"""

    combined_meta: Dict[str, Any] = {}
    combined_meta.update(base.get("meta") or {})
    if meta:
        combined_meta.update(meta)
    combined_meta["search_fallback"] = True

    status_msg = status or base.get("status") or FALLBACK_STATUS_MESSAGE

    session_id = str(uuid.uuid4())[:8]
    sanitized: Dict[str, Any] = {
        "ok": base.get("ok", True),
        "reply": reply or base.get("reply") or status_msg,
        "suggestion_ids": [],
        "category_suggestions": None,
        "action": {"type": "none"},
        "meta": combined_meta,
        "chat_session_id": session_id,
        "display_mode": "text_only",
        "structured_payload": None,
        "structured_products": [],
        "status": status_msg,
    }

    if extra:
        for key, value in extra.items():
            if value is not None:
                sanitized[key] = value

    CHAT_SESSION_CACHE[session_id] = (time.time(), sanitized)
    return sanitized

from pydantic import BaseModel
from typing import Dict

class ChatResponse(BaseModel):
    ok: Optional[bool] = None
    reply: str
    suggestion_ids: Optional[List[str]] = None
    category_suggestions: Optional[Dict] = None
    action: Optional[Dict] = None
    meta: Optional[Dict] = None
    chat_session_id: Optional[str] = None
    display_mode: Optional[str] = None
    structured_payload: Optional[Dict] = None
    structured_filters: Optional[Dict] = None
    structured_products: Optional[List[Dict]] = None
    items: Optional[List[Dict]] = None
    status: Optional[str] = None
    rich_content: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return self.reply or ""

    def __repr__(self) -> str:
        return self.__str__()


def _finalize_directional_products(
    items: List[Dict[str, Any]],
    user_query: str,
    *,
    meta: Optional[Dict[str, Any]] = None,
    structured_filters: Optional[Dict[str, Any]] = None,
) -> ChatResponse:
    """輸出含商品卡結構的方向建議回覆"""

    direction_meta = dict(meta or {})
    direction_meta.setdefault("directional_products", True)
    direction_meta.setdefault("fallback_reason", "SEARCH_DIRECTIONAL_RESULTS")
    direction_meta.setdefault("has_budget_intent", has_budget_intent(user_query))

    reply, structured_payload = _compose_structured_reply(items, True, user_query)
    structured_products = structured_payload.get("items", []) if structured_payload else []

    suggestion_ids = [
        FieldAccessor.get_product_id(item)
        for item in items
        if FieldAccessor.get_product_id(item)
    ]

    session_id = str(uuid.uuid4())[:8]
    status_msg = FALLBACK_STATUS_MESSAGE

    resp_dict: Dict[str, Any] = {
        "ok": True,
        "reply": reply,
        "suggestion_ids": suggestion_ids,
        "meta": direction_meta,
        "action": {"type": "none"},
        "structured_payload": structured_payload,
        "structured_products": structured_products,
        "items": structured_products,
        "chat_session_id": session_id,
        "display_mode": "flat",
        "status": status_msg,
    }

    if structured_filters:
        resp_dict["structured_filters"] = structured_filters

    response_model = ChatResponse(**resp_dict)

    CHAT_SESSION_CACHE[session_id] = (time.time(), response_model.model_dump())

    if suggestion_ids:
        try:
            rows = catalog_service.get_items_by_ids(suggestion_ids)
            cache_entry = {
                "align_ids": suggestion_ids,
                "align_rows": rows,
                "query_terms": [user_query],
                "structured_items": structured_products,
                "structured_summary": structured_payload.get("summary", "") if structured_payload else "",
            }
            if structured_filters:
                cache_entry["structured_filters"] = structured_filters
            bundle_service.save_bundle(session_id, cache_entry)
        except Exception as cache_error:
            LOGGER.warning("Failed to sync directional fallback bundle: %s", cache_error)

    return response_model


class ShoppingSupportHandler(ConversationHandler):
    name = "shopping_support"

    def can_handle(self, intent: IntentDecision, ctx: ConversationContext) -> bool:
        intent_type = (intent.intent_type or "").lower()
        if not intent_type:
            return True
        return intent_type in ("shopping_support", "shopping_recommendation", "general")

    def handle(self, ctx: ConversationContext, intent: IntentDecision) -> HandlerResult:
        raw_req = ctx.input.metadata.get("raw_request") if ctx.input.metadata else None
        if isinstance(raw_req, ChatReq):
            response = _legacy_chat_flow(raw_req)
        else:
            reconstructed = ChatReq(
                message=ctx.input.user_text,
                history=ctx.input.history,
                session_id=ctx.input.session_id,
            )
            response = _legacy_chat_flow(reconstructed)

        if hasattr(response, "dict"):
            payload = response.dict()
        elif isinstance(response, dict):
            payload = dict(response)
        else:
            raise TypeError("Unsupported response type from legacy chat flow")
        return HandlerResult(
            ok=payload.get("ok", True),
            reply=payload.get("reply", ""),
            payload=payload,
            session_id=payload.get("chat_session_id"),
            trace={
                "handler": self.name,
                "intent": intent.intent_type,
                "intent_metadata": intent.metadata,
            },
        )


# 🆕 公司資料查詢處理器
class CompanyInfoHandler(ConversationHandler):
    """處理公司資料查詢的對話處理器"""
    name = "company_info"

    def can_handle(self, intent: IntentDecision, ctx: ConversationContext) -> bool:
        """判斷是否能處理此意圖"""
        intent_type = (intent.intent_type or "").lower()
        return intent_type == "company_info"

    def handle(self, ctx: ConversationContext, intent: IntentDecision) -> HandlerResult:
        """處理公司資料查詢"""
        supabase_session_id = CHAT_LOGGING_BRIDGE.ensure_session(
            ctx.input.session_id,
            metadata={"intent": "company_info"},
        )
        CHAT_LOGGING_BRIDGE.log_user_message(
            ctx.input.session_id,
            ctx.input.user_text,
            {"handler": self.name},
            supabase_session_id=supabase_session_id,
        )

        if not COMPANY_PROFILE_AVAILABLE:
            reply_text = "抱歉，公司資料查詢功能暫時無法使用。"
            payload = {"error": "company_profile_service_unavailable"}
            CHAT_LOGGING_BRIDGE.bind_ui_session(ctx.input.session_id, supabase_session_id)
            CHAT_LOGGING_BRIDGE.log_assistant_message(
                ctx.input.session_id,
                reply_text,
                {"reply": reply_text, "meta": payload},
                supabase_session_id=supabase_session_id,
            )
            return HandlerResult(
                ok=False,
                reply=reply_text,
                payload=payload,
                session_id=ctx.input.session_id,
            )
        
        try:
            # 取得服務實例
            service = get_company_profile_service()
            formatter = get_company_response_formatter()
            
            if not service.is_loaded():
                reply_text = "抱歉，公司資料尚未載入。"
                payload = {"error": "company_profile_not_loaded"}
                CHAT_LOGGING_BRIDGE.bind_ui_session(ctx.input.session_id, supabase_session_id)
                CHAT_LOGGING_BRIDGE.log_assistant_message(
                    ctx.input.session_id,
                    reply_text,
                    {"reply": reply_text, "meta": payload},
                    supabase_session_id=supabase_session_id,
                )
                return HandlerResult(
                    ok=False,
                    reply=reply_text,
                    payload=payload,
                    session_id=ctx.input.session_id,
                )
            
            # 取得完整公司資料
            profile = service.get_profile()
            
            # 判斷查詢主題
            user_query = ctx.input.user_text
            topic = service.match_topic_by_keywords(user_query)
            
            # 格式化回應（返回結構化資料）
            formatted_response = formatter.format_by_topic(topic, profile, query=user_query)
            
            # 提取文字和豐富內容
            reply_text = formatted_response.get("text", "")
            rich_content = formatted_response.get("rich_content")
            
            # 建立回應 payload
            payload = {
                "reply": reply_text,
                "ok": True,
                "suggestion_ids": [],  # 公司資料查詢不需要商品推薦
                "chat_session_id": ctx.input.session_id,
                "meta": {
                    "intent": "company_info",
                    "topic": topic,
                    "company_id": profile.get("company_id"),
                },
                "action": None,
                "items": [],
            }
            
            # 如果有豐富內容，加入 payload
            if rich_content:
                payload["rich_content"] = rich_content

            CHAT_LOGGING_BRIDGE.bind_ui_session(ctx.input.session_id, supabase_session_id)
            CHAT_LOGGING_BRIDGE.log_assistant_message(
                ctx.input.session_id,
                reply_text,
                payload,
                supabase_session_id=supabase_session_id,
            )
            
            return HandlerResult(
                ok=True,
                reply=reply_text,
                payload=payload,
                session_id=ctx.input.session_id,
                trace={
                    "handler": self.name,
                    "intent": intent.intent_type,
                    "topic": topic,
                    "company_id": profile.get("company_id"),
                    "has_rich_content": rich_content is not None,
                },
            )
            
        except Exception as e:
            LOGGER.exception("Company info handler failed: %s", e, session_id=ctx.input.session_id)

            reply_text = "抱歉，查詢公司資料時發生錯誤，請稍後再試。"
            payload = {
                "error": str(e),
                "reply": reply_text,
            }
            CHAT_LOGGING_BRIDGE.bind_ui_session(ctx.input.session_id, supabase_session_id)
            CHAT_LOGGING_BRIDGE.log_assistant_message(
                ctx.input.session_id,
                reply_text,
                {"reply": reply_text, "meta": payload},
                supabase_session_id=supabase_session_id,
            )
            
            return HandlerResult(
                ok=False,
                reply=reply_text,
                payload=payload,
                session_id=ctx.input.session_id,
            )


def _create_enhanced_fallback_response(user_text: str, catalog: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    創建增強的回退響應，即使 LLM 不可用也能理解使用者需求並搜尋商品
    """
    from goods_search_service import search_products
    from llm_service import _prepare_chat_context
    
    # 使用上下文分析理解使用者需求
    context = _prepare_chat_context(user_text, catalog)
    products = context.get("products", [])
    
    # 從使用者訊息中提取關鍵需求
    keywords = []
    budget_match = None
    
    # 基本關鍵字提取
    import re
    chinese_words = re.findall(r'[\u4e00-\u9fff]+', user_text)
    keywords.extend([word for word in chinese_words if len(word) >= 2])
    
    # 預算提取
    budget_pattern = r'(\d+)元?|預算.*?(\d+)|總.*?(\d+)'
    budget_matches = re.findall(budget_pattern, user_text)
    if budget_matches:
        for match in budget_matches:
            for group in match:
                if group and group.isdigit():
                    budget_match = int(group)
                    break
    
    suggestion_ids = []
    safe_user_text = _sanitize_text(user_text)
    
    if products:
        # 有找到商品的情況
        suggestion_ids = [
            str(p.get("商品編號") or p.get("GoodIden", ""))
            for p in products[:8]
            if p.get("商品編號") or p.get("GoodIden")
        ]
        
        product_names = [
            _sanitize_text(FieldAccessor.get_name(p))
            for p in products[:3]
            if FieldAccessor.get_name(p)
        ]
        
        product_summary = " 、 ".join(product_names[:3]) if product_names else "多款精選商品"
        reply = (
            f"根據您的需求「{safe_user_text}」，我為您找到了 {len(products)} 款相關商品。\n\n"
            f"推薦商品包括：{_sanitize_text(product_summary)}。\n\n"
        )
        
        if budget_match:
            reply += f"考量到您 {budget_match} 元的預算，我已為您篩選適合的選項。\n\n"
        
        reply += "需要我顯示詳細商品資訊與圖片嗎？也歡迎告訴我更具體的需求！"
        
        action = {
            "type": "switch_to_search",
            "items": [{"id": sid} for sid in suggestion_ids if sid]
        }
    else:
        # 沒有找到商品的情況
        if keywords:
            keywords_text = _sanitize_text("、".join(keywords[:3]))
            reply = (f"很抱歉，目前我們暫時沒有完全符合「{keywords_text}」的商品。\n\n"
                    f"不過我們有多款相關類別的精選商品，或許能滿足您的需求。\n"
                    f"請告訴我更詳細的使用情境或偏好，我會為您推薦最適合的替代商品！\n\n"
                    f"也歡迎瀏覽我們的熱門分類：健康食品、調味料、零食點心等。")
        else:
            reply = (f"歡迎來到哈通友善生活館！我是您的專屬購物助手。\n\n"
                    f"請告訴我您想要什麼類型的商品，比如：\n"
                    f"• 健康食品（燕麥、五穀雜糧等）\n"
                    f"• 調味料（醬油、香料、沾醬等）\n"
                    f"• 零食點心（餅乾、堅果等）\n"
                    f"• 飲品（茶包、沖泡飲品等）\n\n"
                    f"我會根據您的需求為您精心推薦最適合的商品！")
        
        action = {"type": "none"}
    
    return {
        "reply": reply,
        "suggestion_ids": suggestion_ids,
        "action": action
    }

def simple_chat_handler(req: ChatReq):
    """簡化版聊天處理器，避免複雜依賴問題"""
    user_text = req.user_message.strip()
    
    # 清理過期快取
    _cleanup_session_cache()
    
    # 基本關鍵字匹配
    party_keywords = ["生日", "聚會", "派對", "party", "慶祝", "活動"]
    food_keywords = ["餅乾", "飲料", "點心", "零食", "茶", "汁", "cookie", "drink"]
    
    has_party = any(kw in user_text for kw in party_keywords)
    has_food = any(kw in user_text for kw in food_keywords)
    
    suggestion_ids = []
    structured_payload: Optional[Dict[str, Any]] = None
    
    # 嘗試使用搜索服務來找到相關商品，而不是硬編碼
    try:
        from goods_search_service import search_products
        search_results = search_products(user_text, limit=8)
        
        if search_results:
            suggestion_ids = [
                str(item.get("商品編號") or item.get("GoodIden", ""))
                for item in search_results[:8]
                if item.get("商品編號") or item.get("GoodIden")
            ]
            
            if suggestion_ids:
                fetched = _fetch_items_for_reply(None, suggestion_ids)
                if fetched:
                    reply, structured_payload = _compose_structured_reply(fetched, True, user_text)
                else:
                    reply = f"我為您找到了 {len(suggestion_ids)} 款相關商品。需要我顯示詳細介紹嗎？"
            else:
                reply = "很抱歉，暫時沒有找到符合您需求的商品。請嘗試描述更具體的需求，我會為您重新搜尋。"
        else:
            reply = "很抱歉，暫時沒有找到符合您需求的商品。請嘗試描述更具體的需求，我會為您重新搜尋。"
    except Exception as e:
        LOGGER.error("Search failed in simple_chat_handler: %s", e, session_id=req.session_id)
        # 通用回應，不包含任何硬編碼商品
        reply = "您好！我是智能客服，可以為您推薦商品。請告訴我您需要什麼類型的商品，我會為您搜尋最適合的選項。"
    
    resp = {
        "ok": True,
        "reply": reply,
        "suggestion_ids": suggestion_ids,
        "meta": {"has_budget_intent": has_budget_intent(user_text)},
        "action": {
            "type": "switch_to_search",
            "items": [{"id": sid} for sid in suggestion_ids]
        } if suggestion_ids else None
    }
    simple_filters = infer_filters_from_query(user_text)
    if simple_filters:
        resp["structured_filters"] = simple_filters
    if structured_payload:
        resp["structured_payload"] = structured_payload
    
    # 儲存聊天結果並加入會話 ID
    if suggestion_ids:
        session_id = str(uuid.uuid4())[:8]
        CHAT_SESSION_CACHE[session_id] = (time.time(), resp)
        
        try:
            rows = catalog_service.get_items_by_ids(suggestion_ids)
            cache_entry = {
                "align_ids": suggestion_ids,
                "align_rows": rows,
                "query_terms": [user_text],
            }
            if structured_payload:
                cache_entry["structured_items"] = structured_payload.get("items", [])
                cache_entry["structured_summary"] = structured_payload.get("summary", "")
            if simple_filters:
                cache_entry["structured_filters"] = simple_filters
            bundle_service.save_bundle(session_id, cache_entry)
        except Exception as e:
            LOGGER.warning("Failed to sync recommendation bundle: %s", e, session_id=req.session_id)
        
        resp["chat_session_id"] = session_id
        resp["display_mode"] = "flat"
    
    # 構建 ChatResponse 對象
    return ChatResponse(
        ok=resp.get("ok", True),
        reply=resp.get("reply", ""),
        suggestion_ids=resp.get("suggestion_ids", []),
        meta=resp.get("meta", {}),
        action=resp.get("action", {"type": "none"}),
        structured_filters=resp.get("structured_filters"),
        structured_payload=resp.get("structured_payload"),
        structured_products=resp.get("structured_products", []),
        chat_session_id=resp.get("chat_session_id"),
        status=resp.get("status")
    )


# ---- 概覽/販售範圍 Top-K L1 幫手 ----
import os

def _is_overview_query(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    # 若已能抽出 L1/L2/L3，則不是概覽問句（避免覆蓋導覽回覆）
    try:
        sel = _extract_selected_levels_from_text(t)
        if sel.get("L1") or sel.get("L2") or sel.get("L3"):
            return False
    except Exception:
        pass
    patterns = [
        r"賣什麼",
        r"有什麼類",
        r"販售範圍",
        r"有哪些東西",
        r"有哪些分類",
        r"你們賣",
        r"商品類別",
        r"分類",
        r"能買到什麼",
        r"有賣什麼",
        r"有賣甚麼",
    ]
    return any(re.search(p, t) for p in patterns)


def _detect_l1_column(df) -> Optional[str]:
    if df is None or df.empty:
        return None
    for col in ["CateName_L1", "大分類名稱", "CateName", "分類名稱"]:
        if col in df.columns:
            return col
    return None


def _get_top_l1_list(df, topk: int) -> Dict[str, Any]:
    """優先嘗試走 /api/catalog/scope 的統一計數邏輯；失敗時回退本地 DataFrame 計數。"""
    try:
        # 直接調用內部函式，避免 HTTP call 開銷
        from app import get_catalog_scope  # type: ignore
        scope_resp = get_catalog_scope(level="L1", top_k=topk)
        if hasattr(scope_resp, "body"):
            import json as _json
            data = _json.loads(scope_resp.body)
        else:
            data = scope_resp
        items = (data.get("items") or []) if isinstance(data, dict) else []
        # 🔧 修正：scope/items 是分類對象，用 "name" 字段取分類名稱（不是商品！）
        names = [it.get("name") or it.get("大分類名稱") for it in items if it.get("name")]
        return {"l1": names, "more_count": int(data.get("more_count") or 0), "total": int(data.get("total") or len(names))}
    except Exception:
        # 回退：本地 DataFrame 計數
        l1_col = _detect_l1_column(df)
        if not l1_col:
            return {"l1": [], "more_count": 0, "total": 0}
        series = df[l1_col].astype(str).str.strip()
        series = series.replace({"": "未分類", "None": "未分類", "nan": "未分類"})
        counts = series.value_counts()
        names = [str(x).strip() or "未分類" for x in counts.index.tolist()]
        top_names = names[:topk]
        total_unique = len(names)
        more_count = max(0, total_unique - len(top_names))
        return {"l1": top_names, "more_count": more_count, "total": total_unique}


def _compose_scope_text(l1_list: List[str], more_count: int) -> str:
    if not l1_list:
        return "目前分類載入中，請稍後再試或從左側分類樹查看。"
    text = f"我們目前可銷售的大分類包含：{'、'.join(l1_list)}。"
    if more_count > 0:
        text += f"…還有 {more_count} 類可在左側分類樹查看。"
    text += "想先看看哪一類？"
    return text


def _try_overview_scope_reply(user_text: str) -> Optional[Dict[str, Any]]:
    if not _is_overview_query(user_text):
        return None
    try:
        df = catalog_service.get_dataframe()
    except Exception:
        df = None
    topk = int(os.getenv("SCOPE_TOPK_L1", "8"))
    info = _get_top_l1_list(df, topk)
    reply_text = _compose_scope_text(info.get("l1", []), int(info.get("more_count") or 0))
    meta = {
        "oos_category": False,
        "available_scope": {
            "level": "L1",
            "l1": info.get("l1", []),
            "more_count": int(info.get("more_count") or 0),
        },
        "category_context": {
            "selected": {},
            "next_level": "L1"
        },
        "guide": {"hints": ["可點選上方熱門分類或告訴我您的預算/用途/品牌"]}
    }
    return {
        "ok": True,
        "reply": reply_text,
        "suggestion_ids": [],
        "meta": meta,
        "action": {"type": "none"},
        "structured_payload": None,
        "structured_products": [],
        "items": [],
        "display_mode": "text_only",
        "chat_session_id": str(uuid.uuid4())[:8],
        "status": None,
    }

# ---- 類目導覽（L1 -> L2 -> L3）回覆 ----

def _json_from_response(resp: Any) -> Dict[str, Any]:
    try:
        if hasattr(resp, "body"):
            import json as _json
            return _json.loads(resp.body)
        if isinstance(resp, dict):
            return resp
    except Exception:
        pass
    return {}


def _get_scope_names(level: str, top_k: Optional[int] = None, parent_l1: Optional[str] = None, parent_l2: Optional[str] = None) -> Dict[str, Any]:
    try:
        from app import get_catalog_scope  # type: ignore
        resp = get_catalog_scope(level=level, top_k=top_k, parent_l1=parent_l1, parent_l2=parent_l2)
        data = _json_from_response(resp)
        items = data.get("items") or []
        # 🔧 修正：scope/items 是分類對象，用 "name" 字段取分類名稱（不是商品！）
        names = [it.get("name") or it.get("大分類名稱") for it in items if it.get("name")]
        if not names:
            if level == "L2" and parent_l1:
                names = list((L2_HINTS_BY_L1.get(parent_l1) or {}).keys())
            elif level == "L3" and parent_l1 and parent_l2:
                names = (L3_FALLBACKS_BY_L1_L2.get(parent_l1) or {}).get(parent_l2, [])
        return {
            "names": names,
            "more_count": int(data.get("more_count") or 0),
            "total": int(data.get("total") or len(names)),
            "level": data.get("level") or level,
        }
    except Exception:
        names: List[str] = []
        if level == "L2" and parent_l1:
            names = list((L2_HINTS_BY_L1.get(parent_l1) or {}).keys())
        elif level == "L3" and parent_l1 and parent_l2:
            names = (L3_FALLBACKS_BY_L1_L2.get(parent_l1) or {}).get(parent_l2, [])
        return {"names": names, "more_count": 0, "total": len(names), "level": level}


def _pick_first_in_text(text: str, candidates: List[str]) -> Optional[str]:
    t = str(text or "").strip()
    for name in candidates:
        n = str(name or "").strip()
        if n and (n in t):
            return n
    return None


def _normalize_text_for_match(t: str) -> str:
    t = (t or "").strip()
    # 保留斜線（/、／）以支援名稱中含斜線的分類（例如：五穀/豆類/米麵/乾貨）
    t = re.sub(r"[，,。．\.；;！!？?、\\|（）()【】［］\[\]》〈<>]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


def _best_match(candidates: List[str], text: str, threshold: float = 0.6) -> Optional[str]:
    """
    從候選名單中挑選與文字最相似的名稱。
    - 優先採用子字串精確匹配（最長優先）
    - 若無子字串命中，使用相似度（SequenceMatcher）並套用閾值
    """
    from difflib import SequenceMatcher

    t = _normalize_text_for_match(text)
    best = None
    best_len = 0
    for name in candidates or []:
        n = str(name or "").strip()
        if not n:
            continue
        if n in t:
            if len(n) > best_len:
                best = n
                best_len = len(n)
    if best:
        return best

    scored: List[Tuple[float, str]] = []
    folded = _fold_for_score(t)
    for name in candidates or []:
        n = str(name or "").strip()
        if not n:
            continue
        score = SequenceMatcher(None, _fold_for_score(n), folded).ratio()
        scored.append((score, n))
    scored.sort(key=lambda x: x[0], reverse=True)
    if scored and scored[0][0] >= threshold:
        top3 = scored[:3]
        LOGGER.debug("best_match fallback: top=%s", top3)
        return scored[0][1]
    return None


def _fold_for_score(text: str) -> str:
    base = _normalize_text_for_match(text)
    base = re.sub(r"\s+", "", base).lower()
    return base


def _clean_focus_term(term: str) -> str:
    if not term:
        return ""
    term = term.strip()
    for prefix in ["想看", "想找", "要看", "要找", "想要", "我要"]:
        if term.startswith(prefix):
            term = term[len(prefix):]
    for suffix in ["有哪些", "有什麼", "類別", "分類", "品類", "種類"]:
        if term.endswith(suffix):
            term = term[: -len(suffix)]
    return term.strip()


def _extract_focus_terms(text: str) -> List[str]:
    raw = _normalize_text_for_match(text)
    terms: List[str] = []
    if raw:
        terms.append(raw)
        cleaned = _clean_focus_term(raw)
        if cleaned and cleaned != raw:
            terms.append(cleaned)
    patterns = [
        r"(?:想看|想找|要看|要找|看看|找找)\s*([A-Za-z0-9\u4e00-\u9fff /-]{2,24})",
        r"([A-Za-z0-9\u4e00-\u9fff /-]{2,24})(?:有哪些|分類|品類|種類)",
        r"在\s*([A-Za-z0-9\u4e00-\u9fff /-]{2,24})\s*下",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, raw):
            term = (match.group(1) or "").strip()
            term = _clean_focus_term(term)
            if term:
                terms.append(term)
    # 拆成較短片語，方便比對（例如：女用 背包）
    fragments = re.split(r"[，,。；;？?！!、]", raw)
    for frag in fragments:
        frag = _clean_focus_term(frag)
        if 2 <= len(frag) <= 16:
            terms.append(frag)
        # 針對 slash/頓號等分隔符再細分，捕捉「米類/佐醬湯料」這類片段
        sub_parts = re.split(r"[／/\\|｜、]", frag)
        for part in sub_parts:
            part = _clean_focus_term(part)
            if 2 <= len(part) <= 16:
                terms.append(part)
    deduped = []
    seen = set()
    for term in terms:
        folded = _fold_for_score(term)
        if not folded or folded in seen:
            continue
        seen.add(folded)
        deduped.append(term)
    return deduped


def _compute_match_score(term: str, candidate: str) -> float:
    t = _fold_for_score(term)
    c = _fold_for_score(candidate)
    if not t or not c:
        return 0.0
    if c in t:
        return min(1.2, len(c) / max(len(t), 1) + 0.4)
    if t in c:
        return min(1.2, len(t) / max(len(c), 1) + 0.2)
    ratio = difflib.SequenceMatcher(None, t, c).ratio()
    tokens = [tok for tok in re.split(r"[/-]", c) if tok]
    overlap = sum(1 for tok in tokens if tok in t)
    return min(1.2, ratio + overlap * 0.05)


def _pick_taxonomy_entry(entries: List[Dict[str, Any]], key: str, terms: List[str], min_score: float = 0.68) -> Optional[Dict[str, Any]]:
    best_entry = None
    best_score = 0.0
    for entry in entries or []:
        name = entry.get(key)
        if not name:
            continue
        for term in terms:
            score = _compute_match_score(term, name)
            if score > best_score:
                best_score = score
                best_entry = entry
    if best_score >= min_score:
        return best_entry
    return None


def _match_taxonomy_path(text: str) -> Dict[str, Optional[str]]:
    try:
        taxonomy = categories_service.get_taxonomy_index()
        if not any(taxonomy.get(level) for level in ("l1", "l2", "l3")):
            taxonomy = categories_service.get_taxonomy_index(force=True)
    except Exception:
        taxonomy = {}
    terms = _extract_focus_terms(text)
    if not terms:
        return {}
    l3_entry = _pick_taxonomy_entry(taxonomy.get("l3", []), "l3", terms)
    if l3_entry:
        return {"L1": l3_entry.get("l1"), "L2": l3_entry.get("l2"), "L3": l3_entry.get("l3")}
    l2_entry = _pick_taxonomy_entry(taxonomy.get("l2", []), "l2", terms)
    if l2_entry:
        return {"L1": l2_entry.get("l1"), "L2": l2_entry.get("l2"), "L3": None}
    l1_entry = _pick_taxonomy_entry(taxonomy.get("l1", []), "name", terms, min_score=0.6)
    if l1_entry:
        return {"L1": l1_entry.get("name"), "L2": None, "L3": None}
    return {}


def _extract_selected_levels_from_text(text: str) -> Dict[str, Optional[str]]:
    """從文字中抽取 L1/L2/L3 選擇（以現有 taxonomy 名稱為基準做 substring/語序匹配）。"""
    selected = {"L1": None, "L2": None, "L3": None}
    raw = _normalize_text_for_match(text)
    fallback_l1 = ["常溫食品", "時尚女性"]
    fallback_l1_synonyms = {
        "常溫食品": ["常溫食品"],
        "時尚女性": ["時尚女性"],
    }
    bag_keywords = {"包", "包包", "背包", "女用背包", "皮包", "手提包", "肩背包"}
    fallback_l2_keywords = {
        "常溫食品": {
            "五穀/豆類/米麵/乾貨": ["豆包", "豆腐", "米類", "佐醬", "湯料", "乾貨", "米麵", "穀物"],
        },
        "時尚女性": {
            "女用皮包": ["包", "包包", "背包", "女用背包", "皮包", "手提包", "肩背包"],
        },
    }
    try:
        # 確保分類快取已載入（若前序流程清空了快取，這裡會強制重載）
        categories_service.get_scope(level="L1", top_k=None, force=True)
    except Exception:
        pass
    taxonomy_index = categories_service.get_taxonomy_index(force=True)
    
    # 先嘗試語序模式：在 X 下 Y、小分類/品類等
    l1_names = (_get_scope_names("L1", top_k=None).get("names") or [])
    if not l1_names:
        l1_names = [entry.get("name") for entry in taxonomy_index.get("l1", []) if entry.get("name")]
    if not l1_names:
        l1_names = fallback_l1  # 測試/空資料時提供保底 L1
    LOGGER.debug("[Extract] L1 names=%d query=%s", len(l1_names), raw)
    l1_guess = None
    # 常見語序：在X下、X 下面
    m = re.search(r"在\s*([\u4e00-\u9fffA-Za-z0-9 /&-]{1,20})\s*下", raw)
    if m:
        l1_guess = _best_match(l1_names, m.group(1))
    if not l1_guess:
        # 也支援：有什麼X的品類/分類
        m2 = re.search(r"有什麼\s*([\u4e00-\u9fffA-Za-z0-9 /&-]{1,20})\s*的(品類|分類|小分類|類別|種類)", raw)
        if m2:
            l1_guess = _best_match(l1_names, m2.group(1))
    if not l1_guess:
        # 直接在全文掃描 L1 子字串
        l1_guess = _best_match(l1_names, raw)
    if not l1_guess:
        # fallback: 手工同義詞表（避免測試資料缺分類時無法匹配）
        for canon, syns in fallback_l1_synonyms.items():
            if any(s in raw for s in syns):
                l1_guess = canon
                break
    if not l1_guess and any(bk in raw for bk in bag_keywords):
        l1_guess = "時尚女性"
    if l1_guess:
        selected["L1"] = l1_guess

    def _maybe_fill_l2() -> None:
        if not selected.get("L1") or selected.get("L2"):
            return
        
        # 🔧 修正：先嘗試從各種來源取得 L2 分類名稱清單
        l2_names = (_get_scope_names("L2", top_k=None, parent_l1=selected["L1"]).get("names") or [])
        if not l2_names:
            l2_names = [
                entry.get("l2")
                for entry in taxonomy_index.get("l2", [])
                if entry.get("l1") == selected["L1"] and entry.get("l2")
            ]
        if not l2_names:
            l2_names = list((fallback_l2_keywords.get(selected["L1"]) or {}).keys())
        
        LOGGER.debug("[Extract] L2 names=%d parent=%s", len(l2_names), selected["L1"])
        
        l2_guess = None
        
        # 🔧 優先嘗試關鍵字匹配（即使 l2_names 為空也執行）
        # 這樣可以確保在測試環境中也能正確識別
        hint_table = L2_HINTS_BY_L1.get(selected["L1"], {})
        for l2_name, keywords in hint_table.items():
            if any(keyword in raw for keyword in keywords):
                l2_guess = l2_name
                break
        
        if not l2_guess:
            extra_hints = fallback_l2_keywords.get(selected["L1"], {})
            for l2_name, keywords in extra_hints.items():
                if any(keyword in raw for keyword in keywords):
                    l2_guess = l2_name
                    break
        
        # 如果關鍵字匹配失敗，且有 l2_names，則嘗試語序模式匹配
        if not l2_guess and l2_names:
            m3 = re.search(
                rf"(?:對|於|在)?\s*(?:{re.escape(selected['L1'])})?\s*(?:下)?[\s，,。]*我?對?\s*([\u4e00-\u9fffA-Za-z0-9 /&-]{{1,40}})\s*(?:有興趣|感興趣|喜歡|偏好|想看|想找)",
                raw,
            )
            l2_guess = _best_match(l2_names, m3.group(1)) if m3 else None
            if not l2_guess:
                m4 = re.search(rf"(?:{re.escape(selected['L1'])})\s*(?:的)?\s*([\u4e00-\u9fffA-Za-z0-9 /&-]{{1,40}})", raw)
                if m4:
                    l2_guess = _best_match(l2_names, m4.group(1))
            if not l2_guess:
                l2_guess = _best_match(l2_names, raw)
        
        if l2_guess:
            selected["L2"] = l2_guess

    def _maybe_fill_l3() -> None:
        if not selected.get("L1") or not selected.get("L2") or selected.get("L3"):
            return
        l3_names = (
            _get_scope_names("L3", top_k=None, parent_l1=selected["L1"], parent_l2=selected["L2"]).get("names") or []
        )
        if not l3_names:
            l3_names = [
                entry.get("l3")
                for entry in taxonomy_index.get("l3", [])
                if entry.get("l1") == selected["L1"] and entry.get("l2") == selected["L2"] and entry.get("l3")
            ]
        if not l3_names:
            return
        LOGGER.debug("[Extract] L3 names=%d parent=%s/%s", len(l3_names), selected["L1"], selected["L2"])
        
        # 🔧 優先使用斜線分隔的關鍵字精確匹配（支援：豆包/豆腐/米類/佐醬湯料）
        slash_terms = [t.strip() for t in re.split(r'[/、,，]', raw) if t.strip()]
        if slash_terms:
            best_guess = None
            best_score = 0.0
            for term in slash_terms:
                for candidate in l3_names:
                    score = _compute_match_score(term, candidate)
                    if score > best_score:
                        best_score = score
                        best_guess = candidate
            if best_guess and best_score >= 0.6:
                selected["L3"] = best_guess
                return
        
        # 再嘗試語序模式：小分類X
        m5 = re.search(r"小分類\s*([\u4e00-\u9fffA-Za-z0-9 /&-]{1,40})", raw)
        l3_guess = _best_match(l3_names, m5.group(1)) if m5 else None
        if not l3_guess:
            l3_guess = _best_match(l3_names, raw)
        if l3_guess:
            selected["L3"] = l3_guess

    _maybe_fill_l2()
    _maybe_fill_l3()

    # 若仍無法決定層級，參考 taxonomy 映射做模糊比對
    taxonomy_guess = _match_taxonomy_path(raw)
    for level in ("L1", "L2", "L3"):
        if not selected.get(level) and taxonomy_guess.get(level):
            selected[level] = taxonomy_guess.get(level)

    # 再次補齊可能缺少的 L2/L3
    _maybe_fill_l2()
    _maybe_fill_l3()

    # 若已有 L3/L2 但缺 L1，從 taxonomy 反查路徑補齊
    if taxonomy_index:
        if selected.get("L3") and not selected.get("L1"):
            for entry in taxonomy_index.get("l3", []):
                if entry.get("l3") == selected["L3"]:
                    selected["L1"] = entry.get("l1") or selected.get("L1")
                    selected["L2"] = entry.get("l2") or selected.get("L2")
                    break
        if selected.get("L2") and not selected.get("L1"):
            for entry in taxonomy_index.get("l2", []):
                if entry.get("l2") == selected["L2"]:
                    selected["L1"] = entry.get("l1") or selected.get("L1")
                    break

    LOGGER.debug("[Extract] selected=%s", selected)

    return selected


def _compose_nav_text(selected: Dict[str, Optional[str]], next_level: str, names: List[str], more_count: int) -> str:
    l1 = selected.get("L1") or ""
    l2 = selected.get("L2") or ""
    if next_level == "L2":
        base = f"熱門中分類（{l1}）：{ '、'.join(names) }"
    elif next_level == "L3":
        base = f"熱門小分類（{l1} > {l2}）：{ '、'.join(names) }"
    else:
        base = f"我們目前可銷售的分類包含：{ '、'.join(names) }。"
    if more_count > 0:
        base += f"…還有 {more_count} 類可展開。"
    return base


def _build_category_navigation_response(user_text: str, selected: Dict[str, Optional[str]]) -> Optional[Dict[str, Any]]:
    """
    根據已識別的分類層級構建導覽回應。
    - 若無 L1，回傳 None（表示不處理）
    - 若只有 L1：返回 L2 列表，available_scope.level = L2
    - 若有 L1+L2：返回 L3 列表，available_scope.level = L3
    - 若有 L1+L2+L3：已在最深層，仍回傳 L3 列表（保持可瀏覽）
    """
    if not selected.get("L1"):
        return None

    selected_display = dict(selected)
    if not selected_display.get("L2"):
        selected_display["L2"] = "全部"

    if selected.get("L3"):
        level = "L3"
        next_level = None
        scope = _get_scope_names(
            "L3",
            top_k=int(os.getenv("SCOPE_TOPK_L3", "8")),
            parent_l1=selected["L1"],
            parent_l2=selected["L2"],
        )
    elif selected.get("L2"):
        level = "L3"
        next_level = "L3"
        scope = _get_scope_names(
            "L3",
            top_k=int(os.getenv("SCOPE_TOPK_L3", "8")),
            parent_l1=selected["L1"],
            parent_l2=selected["L2"],
        )
    else:
        level = "L3"
        next_level = "L3"
        scope = _get_scope_names(
            "L3",
            top_k=int(os.getenv("SCOPE_TOPK_L3", "8")),
            parent_l1=selected["L1"],
            parent_l2=None,
        )

    names = scope.get("names") or []
    more_count = int(scope.get("more_count") or 0)
    reply = _compose_nav_text(selected_display, level if level in ("L2", "L3") else "L1", names, more_count)
    meta = {
        "oos_category": False,
        "available_scope": {
            "level": level,
            level.lower(): names,
            "more_count": more_count,
            "parents": {
                "L1": selected_display.get("L1"),
                "l1": selected_display.get("L1"),
                "L2": selected_display.get("L2"),
                "l2": selected_display.get("L2"),
            },
        },
        "category_context": {"selected": selected_display, "next_level": next_level},
        "guide": {"hints": ["可提供預算、用途或品牌，我會更精準推薦"]},
        "decision": {"from": "_build_category_navigation_response", "user_text": user_text},
    }

    return {
        "ok": True,
        "reply": reply,
        "suggestion_ids": [],
        "meta": meta,
        "action": {"type": "none"},
        "structured_payload": None,
        "structured_products": [],
        "items": [],
        "display_mode": "text_only",
        "chat_session_id": str(uuid.uuid4())[:8],
        "status": None,
    }


def _try_category_navigation_reply(user_text: str) -> Optional[Dict[str, Any]]:
    selected = _extract_selected_levels_from_text(user_text)
    resp = _build_category_navigation_response(user_text, selected)
    if resp:
        LOGGER.debug("[NavReply] selected=%s level=%s", selected, resp.get("meta", {}).get("available_scope", {}).get("level"))
    return resp


def _sanitize_category_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_hot_category_hierarchy(raw: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not isinstance(raw, dict):
        return {"L1": "", "L2": "", "L3": ""}
    normalized = {"L1": "", "L2": "", "L3": ""}
    candidates = [raw]
    for key in ("category_hierarchy", "hierarchy", "selected", "selection", "path", "scope"):
        nested = raw.get(key)
        if isinstance(nested, dict):
            candidates.append(nested)
    for payload in candidates:
        for level in ("L1", "L2", "L3"):
            if normalized[level]:
                continue
            value = payload.get(level)
            if value is None and level.lower() in payload:
                value = payload[level.lower()]
            if value is None and level.upper() in payload:
                value = payload[level.upper()]
            if value is None:
                alt_key = f"level_{level[-1]}"
                if alt_key in payload:
                    value = payload.get(alt_key)
            normalized[level] = _sanitize_category_value(value)
    return normalized


def _safe_int(value: Any, default: int, upper: int = 48) -> int:
    try:
        number = int(value)
        if number <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return default
    return min(number, upper)


def _extract_hot_category_click(req: ChatReq) -> Optional[Dict[str, Any]]:
    action = req.action if isinstance(req.action, dict) else {}
    flags = req.flags if isinstance(req.flags, dict) else {}
    action_type = str(action.get("type") or "").lower()
    hot_action_types = {
        "hot_category_click",
        "hot_category_select",
        "select_hot_category",
        "hot_scope_click",
    }
    flag_hot = any(bool(flags.get(key)) for key in ("from_hot_category", "hot_category", "hot_category_click"))
    if action_type not in hot_action_types and not flag_hot:
        return None

    payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
    hierarchy_source = (
        payload.get("category_hierarchy")
        or payload.get("hierarchy")
        or payload.get("selected_path")
        or action.get("category_hierarchy")
        or flags.get("category_hierarchy")
    )
    if not isinstance(hierarchy_source, dict):
        alt = payload.get("parents")
        hierarchy_source = alt if isinstance(alt, dict) else payload

    hierarchy = _normalize_hot_category_hierarchy(hierarchy_source)
    if not (hierarchy.get("L1") and hierarchy.get("L2") and hierarchy.get("L3")):
        return None

    query = (
        payload.get("query")
        or payload.get("text")
        or payload.get("display_text")
        or req.user_message.strip()
    )
    if not query:
        query = " ".join(filter(None, (hierarchy.get("L1"), hierarchy.get("L2"), hierarchy.get("L3"))))

    limit = _safe_int(payload.get("limit") or payload.get("page_size") or payload.get("topn") or req.topn, 24)

    return {
        "hierarchy": hierarchy,
        "level": str(payload.get("level") or action.get("level") or "L3").upper(),
        "query": query,
        "limit": limit,
        "from_hot_category": True,
        "action_type": action_type or ("flag" if flag_hot else ""),
        "source": action.get("source"),
    }


def _normalize_match_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return re.sub(r"\s+", "", text).lower()


def _filter_snapshot_by_hierarchy(
    snapshot: Sequence[Dict[str, Any]],
    hierarchy: Dict[str, str],
    limit: int,
) -> List[Dict[str, Any]]:
    l1 = _normalize_match_text(hierarchy.get("L1"))
    l2 = _normalize_match_text(hierarchy.get("L2"))
    l3 = _normalize_match_text(hierarchy.get("L3"))
    matches: List[Dict[str, Any]] = []
    for row in snapshot or []:
        l3_value = _normalize_match_text(FieldAccessor.get_category_l3(row))
        if l3 and l3_value != l3:
            continue
        l2_value = _normalize_match_text(FieldAccessor.get_category_l2(row))
        if l2 and l2_value != l2:
            continue
        l1_value = _normalize_match_text(FieldAccessor.get_category_l1(row))
        if l1 and l1_value != l1:
            continue
        matches.append(row)
        if len(matches) >= limit:
            break
    return matches


def handle_hot_category_click(req: ChatReq, hot_ctx: Dict[str, Any]) -> Optional[ChatResponse]:
    hierarchy = hot_ctx.get("hierarchy") or {}
    if not (hierarchy.get("L1") and hierarchy.get("L2") and hierarchy.get("L3")):
        return None

    query_text = hot_ctx.get("query") or " ".join(filter(None, hierarchy.values()))
    limit = _safe_int(hot_ctx.get("limit"), 24)

    LOGGER.info(
        "Hot category click → L1=%s, L2=%s, L3=%s, limit=%s",
        hierarchy.get("L1"),
        hierarchy.get("L2"),
        hierarchy.get("L3"),
        limit,
        session_id=req.session_id,
    )

    items: List[Dict[str, Any]] = []
    try:
        df = catalog_service.get_dataframe()
        if df is not None and not df.empty:
            items, _ = search_products_with_hierarchy(
                df,
                query=query_text,
                hierarchy=hierarchy,
                topn=limit,
            )
    except Exception as exc:
        LOGGER.warning("Hot category handler failed to use indexed search: %s", exc, session_id=req.session_id)

    if not items:
        try:
            snapshot = catalog_service.snapshot(limit=max(limit * 3, 120))
            items = _filter_snapshot_by_hierarchy(snapshot, hierarchy, limit)
        except Exception as exc:
            LOGGER.warning("Hot category snapshot fallback failed: %s", exc, session_id=req.session_id)

    if not items:
        return None

    reply, structured_payload = _compose_structured_reply(items, True, query_text)
    structured_products = structured_payload.get("items", []) if structured_payload else []
    suggestion_ids = [
        FieldAccessor.get_product_id(item)
        for item in items
        if FieldAccessor.get_product_id(item)
    ]

    session_id = str(uuid.uuid4())[:8]
    meta = {
        "hot_category": True,
        "from_hot_category": hot_ctx.get("from_hot_category", True),
        "category_hierarchy": hierarchy,
        "trigger_level": hot_ctx.get("level"),
        "search_directional": True,
    }
    if hot_ctx.get("action_type"):
        meta["action_type"] = hot_ctx["action_type"]
    if hot_ctx.get("source"):
        meta["source"] = hot_ctx["source"]

    structured_filters = {"category_hierarchy": hierarchy, "from_hot_category": True}

    resp = ChatResponse(
        ok=True,
        reply=reply,
        suggestion_ids=suggestion_ids,
        meta=meta,
        action={"type": "none"},
        structured_filters=structured_filters,
        structured_payload=structured_payload,
        structured_products=structured_products,
        items=structured_products,
        chat_session_id=session_id,
        display_mode="flat",
        status="已根據熱門分類為您列出推薦",
    )

    try:
        CHAT_SESSION_CACHE[session_id] = (time.time(), resp.model_dump())
    except Exception:
        CHAT_SESSION_CACHE[session_id] = (time.time(), resp.dict())

    if suggestion_ids:
        try:
            rows = catalog_service.get_items_by_ids(suggestion_ids)
            cache_entry = {
                "align_ids": suggestion_ids,
                "align_rows": rows,
                "query_terms": [query_text],
                "structured_items": structured_products,
                "structured_summary": structured_payload.get("summary", "") if structured_payload else "",
            }
            bundle_service.save_bundle(session_id, cache_entry)
        except Exception as cache_error:
            LOGGER.warning("Failed to cache hot category bundle: %s", cache_error, session_id=req.session_id)

    return resp

def _legacy_chat_flow(req: ChatReq) -> ChatResponse:
    """Legacy chat flow kept for gradual refactor."""
    user_text = req.user_message.strip()
    history = req.safe_history
    structured_filters: Dict[str, Any] = {}
    hot_ctx = _extract_hot_category_click(req)
    if hot_ctx:
        hot_resp = handle_hot_category_click(req, hot_ctx)
        if hot_resp:
            return hot_resp
    product_id_query = _looks_like_product_id_query(user_text)

    if user_text and is_negative_query(user_text):
        return ChatResponse(
            ok=True,
            reply=NEGATIVE_QUERY_MESSAGE,
            suggestion_ids=[],
            meta={"clarify": True, "reason": "negative_query"},
            action={"type": "none"},
            structured_filters=None,
            structured_payload=None,
            structured_products=[],
            chat_session_id=str(uuid.uuid4())[:8],
            status=None,
        )

    if product_id_query:
        try:
            items = search_products_strict(query=user_text, limit=10, filters=None)
            if items:
                meta_info = {"product_id_query": True}
                return _finalize_directional_products(
                    items,
                    user_text,
                    meta=meta_info,
                    structured_filters=None,
                )
        except Exception as exc:
            LOGGER.warning("Direct product-id search failed: %s", exc, session_id=req.session_id)

    # 🆕 若文字中已能完整識別 L1/L2/L3，直接走分類搜尋（避免進入聊天話術）
    selected_full = _extract_selected_levels_from_text(user_text)
    if selected_full.get("L1") and selected_full.get("L2") and selected_full.get("L3"):
        try:
            df = catalog_service.get_dataframe()
            results, _ = search_products_with_hierarchy(
                df=df,
                query=user_text,
                hierarchy=selected_full,
                topn=24,
                min_score=0.0,
            )
            if results:
                meta = {"from_category_autodetect": True, "category_hierarchy": selected_full}
                filters = {"category_hierarchy": selected_full}
                return _finalize_directional_products(results, user_text, meta=meta, structured_filters=filters)
        except Exception as exc:
            LOGGER.warning("category autodetect search failed: %s", exc, session_id=req.session_id)

    # 類目導覽 / 範圍總覽優先回覆，避免純分類詢問被拉進 LLM 話術
    nav_early = _try_category_navigation_reply(user_text)
    if nav_early:
        return ChatResponse(**nav_early)
    overview_early = _try_overview_scope_reply(user_text)
    if overview_early:
        return ChatResponse(**overview_early)

    if user_text and not product_id_query:
        try:
            from llm_service import llm_analyze_query, llm_clarify_or_confirm

            analysis = llm_analyze_query(user_text, use_search_config=False)
            clarification = llm_clarify_or_confirm(analysis, user_text)
            if clarification.get("type") == "clarify":
                return ChatResponse(
                    ok=True,
                    reply=clarification["message"],
                    suggestion_ids=[],
                    meta={"clarify": True, "reason": "needs_more_context"},
                    action={"type": "none"},
                    structured_filters=None,
                    structured_payload=None,
                    structured_products=[],
                    chat_session_id=str(uuid.uuid4())[:8],
                    status=None,
                )
        except Exception as exc:
            LOGGER.warning("Clarification pre-check failed: %s", exc, session_id=req.session_id)
    
    # 清理過期快取
    _cleanup_session_cache()

    planner_intent: Optional[DetectedIntent] = None
    try:
        planner_intent = planner_detect_intent(user_text)
    except Exception as exc:
        LOGGER.warning("Planner intent detection failed: %s", exc, session_id=req.session_id)
        planner_intent = None

    party_context = False
    try:
        from fallback.multi_category_party import need_fallback

        party_context = need_fallback(user_text)
    except Exception as exc:
        LOGGER.warning("Fallback detector failed: %s", exc, session_id=req.session_id)

    # 1. 強制使用 LLM 聊天模式（一律透過 LLM 互動）
    try:
        from llm_service import chat_reply, _get_client, build_oos_response
        
        # 檢查 LLM 是否可用，如果不可用則提供回退
        client = _get_client()
        if not client:
            LOGGER.warning("OpenAI client not available, using mock LLM mode", session_id=req.session_id)
        
        # 獲取完整商品目錄用於 LLM 聊天和商品搜尋
        catalog = catalog_service.snapshot(limit=200)  # 增加商品數量以提供更全面的搜尋
        
        # 強制使用 LLM 聊天功能進行所有互動
        llm_result = chat_reply(
            user_message=user_text,
            history=history,
            catalog=catalog,
            topn=10  # 增加搜尋結果數量
        )
        llm_result = llm_result or {}
        if not llm_result.get("display_mode"):
            llm_result["display_mode"] = "text_only"
        llm_result.setdefault("meta", {})
        structured_filters = llm_result.get("structured_filters") or {}
        llm_meta = llm_result.get("meta") or {}

        if llm_meta.get("oos_category"):
            _clear_chat_session_cache(req.session_id)
            oos_resp = build_oos_response(user_text, llm_meta.get("oos_reason", "keyword_block"))
            merged_meta = oos_resp.get("meta", {})
            merged_meta.update(llm_meta)
            oos_reply = ChatResponse(
                ok=True,
                reply=oos_resp.get("reply", ""),
                suggestion_ids=[],
                meta=merged_meta,
                action=oos_resp.get("action", {"type": "none"}),
                structured_filters=None,
                structured_payload=None,
                structured_products=[],
                chat_session_id=str(uuid.uuid4())[:8],
                status=oos_resp.get("status"),
            )
            return oos_reply

        if llm_result and llm_result.get("reply"):
            LOGGER.info("LLM chat activated", session_id=req.session_id)

            intent_label = llm_result.get("intent")
            if intent_label in ("information", "event_food_planning"):
                info_resp, info_ids, info_payload = prepare_information_response(
                    llm_result,
                    user_text,
                    structured_filters,
                    _fetch_items_for_reply,
                    session_id=req.session_id,
                )
                if info_ids and info_payload:
                    try:
                        rows = catalog_service.get_items_by_ids(info_ids)
                        cache_entry = {
                            "align_ids": info_ids,
                            "align_rows": rows,
                            "query_terms": [user_text],
                            "structured_items": info_payload.get("items", []),
                            "structured_summary": info_payload.get("summary", ""),
                        }
                        if structured_filters:
                            cache_entry["structured_filters"] = structured_filters
                        session_id = str(uuid.uuid4())[:8]
                        CHAT_SESSION_CACHE[session_id] = (time.time(), info_resp)
                        bundle_service.save_bundle(session_id, cache_entry)
                        info_resp["session_id"] = session_id
                    except Exception as e:
                        LOGGER.warning("Failed to cache information intent payload: %s", e, session_id=req.session_id)
                # 構建 ChatResponse 對象
                return ChatResponse(
                    ok=info_resp.get("ok", True),
                    reply=info_resp.get("reply", ""),
                    suggestion_ids=info_resp.get("suggestion_ids", []),
                    meta=info_resp.get("meta", {}),
                    action=info_resp.get("action", {"type": "none"}),
                    structured_filters=info_resp.get("structured_filters"),
                    structured_payload=info_resp.get("structured_payload"),
                    structured_products=info_resp.get("structured_products", []),
                    chat_session_id=info_resp.get("session_id") or info_resp.get("chat_session_id"),
                    status=info_resp.get("status")
                )

            # 如果是資訊/概覽或 OOS 模式，直接返回聊天回覆，不切換商品模式
            llm_intent = (llm_result.get("intent") or "").lower()
            if llm_intent in ("information", "confirmation_needed") or llm_result.get("overview"):
                info_payload = {
                    "ok": True,
                    "reply": llm_result.get("reply", ""),
                    "suggestion_ids": [],
                    "meta": llm_result.get("meta", {}),
                    "action": {"type": "none"},
                    "display_mode": llm_result.get("display_mode") or "text_only",
                    "structured_payload": llm_result.get("structured_payload"),
                    "structured_products": llm_result.get("structured_products", []),
                    "status": llm_result.get("status"),
                    "chat_session_id": str(uuid.uuid4())[:8],
                }
                return ChatResponse(**info_payload)

            shopping_resp, shopping_ids, shopping_payload = prepare_shopping_response(
                llm_result,
                user_text,
                structured_filters,
                planner_intent,
                party_context,
                has_budget_intent,
                _fetch_items_for_reply,
                _compose_structured_reply,
                _invoke_category_planner,
                _merge_planner_reply,
            )

            if shopping_ids:
                session_id = str(uuid.uuid4())[:8]
                CHAT_SESSION_CACHE[session_id] = (time.time(), shopping_resp)
                try:
                    rows = catalog_service.get_items_by_ids(shopping_ids)
                    cache_entry = {
                        "align_ids": shopping_ids,
                        "align_rows": rows,
                        "query_terms": [user_text],
                    }
                    if shopping_payload:
                        cache_entry["structured_items"] = shopping_payload.get("items", [])
                        cache_entry["structured_summary"] = shopping_payload.get("summary", "")
                    if structured_filters:
                        cache_entry["structured_filters"] = structured_filters
                    bundle_service.save_bundle(session_id, cache_entry)
                except Exception as e:
                    LOGGER.warning("Failed to sync recommendation bundle: %s", e, session_id=req.session_id)
                shopping_resp["session_id"] = session_id

            # 構建 ChatResponse 對象
            return ChatResponse(
                ok=shopping_resp.get("ok", True),
                reply=shopping_resp.get("reply", ""),
                suggestion_ids=shopping_resp.get("suggestion_ids", []),
                meta=shopping_resp.get("meta", {}),
                action=shopping_resp.get("action", {"type": "none"}),
                structured_filters=shopping_resp.get("structured_filters"),
                structured_payload=shopping_resp.get("structured_payload"),
                structured_products=shopping_resp.get("structured_products", []),
                chat_session_id=shopping_resp.get("session_id") or shopping_resp.get("chat_session_id"),
                status=shopping_resp.get("status")
            )
            
    except Exception as e:
        LOGGER.error("LLM chat failed: %s", e, session_id=req.session_id)
        
        # 即使 LLM 失敗也要透過增強的 Mock 模式維持智能互動
        try:
            catalog = catalog_service.snapshot(limit=100)
            
            # 使用增強的 Mock 回覆，仍保持商品需求理解能力
            mock_response = _create_enhanced_fallback_response(user_text, catalog)
            fallback_meta = {
                "has_budget_intent": has_budget_intent(user_text),
                "llm_fallback": True,
                "fallback_reason": f"LLM_ERROR: {str(e)}",
            }
            sanitized = _finalize_text_only_fallback(
                {"ok": True, "reply": mock_response.get("reply"), "meta": fallback_meta}
            )
            return ChatResponse(**sanitized)
        except Exception as fallback_error:
            LOGGER.error("Enhanced fallback also failed: %s", fallback_error, session_id=req.session_id)
            # 最後的回退，但仍保持禮貌和專業

    # 2. 嘗試 fallback 系統處理特殊查詢（如生日聚會）
    try:
        if party_context:
            _fb = run_fallback(user_text)
            if _fb and _fb.get("ok"):
                LOGGER.info("Fallback system activated", session_id=req.session_id)
                fallback_meta = dict(_fb.get("meta") or {})
                fallback_meta.setdefault("fallback_reason", "RULE_BASED_FALLBACK")
                fallback_meta["has_budget_intent"] = has_budget_intent(user_text)

                extra_fields: Dict[str, Any] = {}
                if _fb.get("structured_filters"):
                    extra_fields["structured_filters"] = _fb["structured_filters"]

                sanitized = _finalize_text_only_fallback(
                    {"ok": _fb.get("ok", True), "reply": _fb.get("reply"), "meta": fallback_meta},
                    status=FALLBACK_STATUS_MESSAGE,
                    extra=extra_fields or None,
                )
                return ChatResponse(**sanitized)
    except Exception as e:
        LOGGER.error("Fallback system error: %s", e, session_id=req.session_id)
        
    # 3. 嘗試使用正常搜索系統
    try:
        items = search_products_strict(query=user_text, limit=10, filters=structured_filters)

        if items:
            meta_info = {
                "fallback_entry": "search_products_strict",
                "search_directional": True,
            }

            return _finalize_directional_products(
                items,
                user_text,
                meta=meta_info,
                structured_filters=structured_filters or None,
            )
    except Exception as e:
        LOGGER.error("Advanced search failed: %s", e, session_id=req.session_id)
    
    # 4. 最終回退：使用增強的回退響應
    try:
        catalog = catalog_service.snapshot(limit=100)
        fallback_response = _create_enhanced_fallback_response(user_text, catalog)
        fallback_meta = {
            "has_budget_intent": has_budget_intent(user_text),
            "final_fallback": True,
            "fallback_reason": "FINAL_FALLBACK",
        }
        sanitized = _finalize_text_only_fallback(
            {"ok": True, "reply": fallback_response.get("reply"), "meta": fallback_meta},
            status=FALLBACK_STATUS_MESSAGE,
        )
        return ChatResponse(**sanitized)
    except Exception as e:
        LOGGER.error("Final fallback failed: %s", e, session_id=req.session_id)
        # 最簡單的回退
        sanitized = _finalize_text_only_fallback(
            {
                "ok": True,
                "reply": "很抱歉，目前系統繁忙。請重新開始聊天或告訴我您需要什麼商品，我會為您提供協助。",
                "meta": {"system_error": True},
            },
            status=FALLBACK_STATUS_MESSAGE,
        )
        return ChatResponse(**sanitized)


def _default_intent_detector(ctx: ConversationContext) -> IntentDecision:
    """
    意圖檢測器：整合 LLM 意圖判斷
    優先檢查公司資料查詢，再路由到商品搜尋
    """
    from llm_service import _detect_conversation_intent
    
    user_text = ctx.input.user_text
    
    # 使用 LLM 意圖判斷
    try:
        detected_intent = _detect_conversation_intent(user_text)
        
        # 🆕 如果是公司資料查詢，優先處理
        if detected_intent == "company_info":
            return IntentDecision(
                intent_type="company_info",
                confidence=0.9,
                metadata={"detected_by": "llm_service"}
            )
        
        # 其他意圖回退到商品搜尋
        return IntentDecision(
            intent_type="shopping_support",
            confidence=0.6,
            metadata={"original_intent": detected_intent}
        )
    except Exception as e:
        LOGGER.warning("Intent detection failed: %s", e, session_id=ctx.input.session_id)
        # 降級：預設為商品搜尋
        return IntentDecision(
            intent_type="shopping_support",
            confidence=0.5,
            metadata={"fallback": True}
        )


_SHOPPING_HANDLER = ShoppingSupportHandler()
_COMPANY_INFO_HANDLER = CompanyInfoHandler()  # 🆕 公司資料處理器
_INTENT_ROUTER = IntentRouter()
_INTENT_ROUTER.register("shopping_support", _SHOPPING_HANDLER)
_INTENT_ROUTER.register("company_info", _COMPANY_INFO_HANDLER)  # 🆕 註冊處理器
_INTENT_ROUTER.set_fallback(_SHOPPING_HANDLER)
_ORCHESTRATOR = ConversationOrchestrator(
    intent_detector=_default_intent_detector,
    router=_INTENT_ROUTER,
    default_handler=_SHOPPING_HANDLER,
)


@router.post("/api/chat", response_model=ChatResponse)
def chat_handler(req: ChatReq) -> ChatResponse:
    """Entry point that delegates to the modular conversation orchestrator."""
    supabase_session_id = CHAT_LOGGING_BRIDGE.log_user_message(
        req.session_id,
        req.user_message,
        {
            "history_length": len(req.safe_history),
            "topn": req.topn,
            "voice_mode": req.voice_mode,
        },
    )

    convo_input = ConversationInput(
        user_text=req.user_message.strip(),
        history=req.safe_history,
        session_id=req.session_id,
        metadata={"raw_request": req},
    )
    result = _ORCHESTRATOR.handle(convo_input)
    payload = dict(result.payload or {})
    if "reply" not in payload:
        payload["reply"] = result.reply
    payload.setdefault("ok", result.ok)
    if result.session_id and not payload.get("chat_session_id"):
        payload["chat_session_id"] = result.session_id

    final_ui_session_id = payload.get("chat_session_id") or req.session_id
    if not final_ui_session_id:
        final_ui_session_id = str(uuid.uuid4())[:8]
        payload["chat_session_id"] = final_ui_session_id

    CHAT_LOGGING_BRIDGE.bind_ui_session(final_ui_session_id, supabase_session_id)

    assistant_record = CHAT_LOGGING_BRIDGE.log_assistant_message(
        final_ui_session_id,
        payload.get("reply", ""),
        payload,
        supabase_session_id=supabase_session_id,
    )
    _log_recommendations_for_payload(assistant_record, payload)

    return ChatResponse(**payload)
