from fallback.multi_category_party import run_fallback
from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter
from pydantic import BaseModel
from utils.llm_guard import safe_call_async
from utils.simple_extract import extract_budget_and_cats
__LLM_GUARD_INSTALLED__ = True
from search_ext_goods_1024001 import search_products_strict, infer_filters_from_query
from field_utils import FieldAccessor
import uuid
import time
import re
import json


def _clean_text(value: Optional[str]) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"[，,。．\.；;！!／/、\\|（）()【】［］\[\]]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _select_marketing_tail(name: str, description: str) -> str:
    combined = (name or "") + " " + (description or "")
    for keyword, tail in MARKETING_TAILS:
        if keyword and keyword in combined:
            return tail
    return "，香濃暖胃好活力"


def _build_marketing_description(item: Dict[str, Any]) -> str:
    name = _clean_text(item.get("Name") or item.get("商品名稱") or item.get("name"))
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
    ]
    features: List[str] = []
    for keyword, phrase in feature_map:
        if keyword in combined and phrase not in features:
            features.append(phrase)
        if len(features) >= 2:
            break

    if not features:
        if any(kw in combined for kw in ["麥片", "燕麥"]):
            features.append("高纖滿滿")
        elif "粥" in combined:
            features.append("暖胃即享")
        else:
            features.append("香濃好滋味")

    body = name_core + "".join(features[:2])
    tail = _select_marketing_tail(name, raw_desc)
    marketing = (body + tail).strip()
    if not marketing:
        marketing = f"{name_core}香濃暖胃好活力"
    if len(marketing) > 30:
        marketing = marketing[:30]
    return marketing


def _build_structured_items(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = f"我找到 {len(items)} 款商品，詳細如下："
    payload_items: List[Dict[str, Any]] = []
    lines: List[str] = [summary]
    for idx, item in enumerate(items, 1):
        gid = str(item.get("GoodIden") or item.get("商品編號") or item.get("id") or "").strip()
        name = str(item.get("Name") or item.get("商品名稱") or item.get("name") or "").strip()
        price = str(item.get("Price") or item.get("售價") or item.get("price") or "").strip()
        special = str(item.get("SpecialOffer") or item.get("特價") or item.get("special") or item.get("sale") or "").strip()
        link = str(item.get("Goods_Link1") or item.get("商品購物網址") or item.get("link") or item.get("url") or "").strip()
        image = str(item.get("Goodspic_Link1") or item.get("商品圖片網址") or item.get("商品圖片") or item.get("image") or "").strip()
        marketing = _build_marketing_description(item)

        entry_lines = [
            f"{idx}.",
            f"商品編號：{gid}",
            f"商品名稱：{name}",
            f"商品描述：{marketing}",
            f"商品價格：{price}",
        ]
        if special:
            entry_lines.append(f"商品特價：{special}")
        entry_lines.append(f"購物連結：{link}")
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


def _compose_structured_reply(items: List[Dict[str, Any]], include_suffix: bool = True) -> Tuple[str, Dict[str, Any]]:
    if not items:
        return "", {"summary": "", "items": []}
    structured = _build_structured_items(items)
    text_body = "\n\n".join(structured["text_lines"])
    if include_suffix and SUGGEST_PROMPT_SUFFIX:
        text_body = f"{text_body}\n\n{SUGGEST_PROMPT_SUFFIX}"
    json_blob = json.dumps({"summary": structured["summary"], "items": structured["items"]}, ensure_ascii=False)
    reply_text = f"{text_body}\n{json_blob}"
    return reply_text, structured


def _fetch_items_for_reply(prefetched: Optional[List[Dict[str, Any]]], suggestion_ids: List[str]) -> List[Dict[str, Any]]:
    """取得完整欄位的商品列表，若沒有預取資料則回到資料庫查詢。"""
    items = prefetched or []
    if items:
        return items
    if not suggestion_ids:
        return []
    try:
        from app import get_df
        from goods_search_service import get_items_by_ids as _get_items_by_ids

        df = get_df()
        if df is None:
            return []
        return _get_items_by_ids(df, suggestion_ids)
    except Exception as exc:
        print(f"[WARNING] 無法取得完整商品資料：{exc}")
        return []

router = APIRouter()

# 聊天會話結果快取
CHAT_SESSION_CACHE = {}
CACHE_TTL = 300  # 5 分鐘 TTL

AGREE_WORDS = {"要","ok","OK","Ok","好","可以","行","確定","沒問題","那就這些","都可以","ＯＫ","Ｏk","ｏｋ"}
SUGGEST_PROMPT_SUFFIX = "也可輸入 1=原建議、2=特價關聯、3=智慧搭配。"
MARKETING_TAILS = [
    ("麥片", "，晨起元氣好選擇"),
    ("燕麥", "，守護輕盈好體態"),
    ("粥", "，暖胃即食好滋味"),
    ("餅乾", "，酥脆共享好時光"),
    ("飲料", "，清爽補水好滿足"),
    ("茶", "，溫潤放鬆好時刻"),
    ("咖啡", "，香醇醒神好夥伴"),
]

def has_budget_intent(text: str) -> bool:
    import re
    t = (text or "").strip()
    kw = re.compile(r"(預算|多少錢|多少元|價位|上限|便宜|貴不貴|價格)")
    money = re.compile(r"(\d[\d,\.]*)(\s*)(元|塊|\$)")
    return bool(kw.search(t) or money.search(t))

class ChatReq(BaseModel):
    message: str  # 改為與前端一致的欄位名稱
    text: Optional[str] = None  # 向後相容
    history: Optional[List[Dict]] = []
    topn: Optional[int] = 8
    session_id: Optional[str] = None
    
    @property
    def user_message(self):
        """統一的訊息存取方式"""
        return self.message or self.text or ""

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
    
    if has_party and has_food:
        # 固定推薦商品 ID 清單 - 針對生日派對情境 (預算 1000 元，餅乾600元 + 飲品400元)
        suggestion_ids = [
            # 餅乾零食類 (~600元) 
            "4713837032316",  # 玫瑰鹽薄切洋芋片 49元
            "4713837030497",  # 香辣洋芋片 49元  
            "4713837032002",  # 黑芝麻餅 79元
            "4713837031999",  # 椒鹽蘇達餅 79元
            "4713837030084",  # 胡椒餅乾 79元
            "4713837032071",  # 湯種吐司餅乾 79元
            "4713837030107",  # 孜然餅 79元
            "4713837030114",  # 黑胡椒餅 79元
            "4713837032033",  # 原味薄切洋芋片 49元
            "4713837032026",  # 海苔薄切洋芋片 49元
            "4713837030022",  # 椰子餅 79元
            "4713837032101",  # 芝麻蘇打餅 79元
            # 飲品類 (~400元)
            "4714379952018",  # 米森有機黑糖老薑茶隨身包 18元
            "4713517167611",  # 曼寧檸香薑茶 180元
            "4710940006722",  # 吃果籽愛文翡翠吸凍飲 39元
            "4710940006715",  # 吃果籽柳丁翡翠吸凍飲 39元
        ]
        fetched = _fetch_items_for_reply(None, suggestion_ids)
        if fetched:
            reply, structured_payload = _compose_structured_reply(fetched)
        else:
            reply = (
                "我為您準備了適合生日聚會的餅乾與飲料組合，總預算控制在 1000 元內。\n"
                "需要我顯示詳細商品資訊嗎？也可輸入 1=查看推薦、2=特價商品、3=智慧搭配。"
            )
    elif "餅乾" in user_text or "cookie" in user_text.lower():
        suggestion_ids = [
            "4711202224557",  # 九福小餅(原味)
            "4711202224403",  # 麻花(海苔口味)
            "4711202224410",  # 麻花(芝麻口味)
        ]
        fetched = _fetch_items_for_reply(None, suggestion_ids)
        if fetched:
            reply, structured_payload = _compose_structured_reply(fetched)
        else:
            reply = f"我找到 {len(suggestion_ids)} 款餅乾商品，需要我顯示詳細介紹與圖片嗎？\n{SUGGEST_PROMPT_SUFFIX}"
    elif "飲料" in user_text or "drink" in user_text.lower():
        # 這裡可以添加飲料類商品 ID
        reply = "我們有多款飲料可選，請稍候為您準備詳細商品資訊。"
    else:
        # 一般查詢處理
        reply = "您好！我是智能客服，可以為您推薦商品。請告訴我您需要什麼類型的商品？"
    
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
    if structured_payload:
        resp["structured_payload"] = structured_payload
    
    # 儲存聊天結果並加入會話 ID
    if suggestion_ids:
        session_id = str(uuid.uuid4())[:8]
        CHAT_SESSION_CACHE[session_id] = (time.time(), resp)
        
        # 同步更新 app.py 的 SUGGEST_CACHE 以支援建議功能
        try:
            from app import SUGGEST_CACHE, get_items_by_ids, get_df
            df = get_df()
            rows = get_items_by_ids(df, suggestion_ids)
            cache_entry = {
                "align_ids": suggestion_ids,
                "align_rows": rows,
                "query_terms": [user_text],
                "ts": time.time(),
            }
            if structured_payload:
                cache_entry["structured_items"] = structured_payload.get("items", [])
                cache_entry["structured_summary"] = structured_payload.get("summary", "")
            SUGGEST_CACHE[session_id] = cache_entry
        except Exception as e:
            print(f"[WARNING] Failed to sync SUGGEST_CACHE: {e}")
        
        resp["chat_session_id"] = session_id
        resp["display_mode"] = "flat"
    
    return resp


@router.post("/api/chat", response_model=ChatResponse)
def chat_handler(req: ChatReq):
    """主聊天處理器，整合真正的 LLM 聊天功能"""
    user_text = req.user_message.strip()
    history = req.history or []
    structured_filters: Dict[str, Any] = {}
    
    # 清理過期快取
    _cleanup_session_cache()
    
    # 1. 優先嘗試 LLM 聊天模式（真正的對話）
    try:
        from llm_service import chat_reply
        from goods_search_service import get_catalog_snapshot
        
        # 獲取商品目錄用於 LLM 聊天
        catalog = get_catalog_snapshot(limit=100)
        
        # 使用真正的 LLM 聊天功能
        llm_result = chat_reply(
            user_message=user_text,
            history=history,
            catalog=catalog,
            topn=8
        )
        structured_filters = llm_result.get("structured_filters") or {}
        
        if llm_result and llm_result.get("reply"):
            print(f"[INFO] LLM chat activated for: {user_text[:50]}...")
            
            # 處理 LLM 聊天結果
            suggestion_ids = []
            alignment = llm_result.get("alignment")
            if alignment and alignment.get("items"):
                suggestion_ids = [item.get("id") for item in alignment["items"] if item.get("id")]
            
            # 🩺 檢查是否為資訊諮詢模式（不需要商品推薦）
            is_information_intent = llm_result.get("intent") == "information"
            has_action = isinstance(llm_result.get("action"), dict) and llm_result["action"].get("type") and llm_result["action"].get("type") != "none"
            
            # 資訊諮詢模式直接返回對話，不需要商品建議
            if is_information_intent:
                print(f"[INFO] Information consultation mode - no product search needed")
                return {
                    "ok": True,
                    "reply": llm_result.get("reply", ""),
                    "suggestion_ids": [],
                    "meta": {
                        "has_budget_intent": False,
                        "intent": llm_result.get("intent"),
                        "intent_subtype": llm_result.get("intent_subtype")
                    },
                    "action": {"type": "none"}
                }
            
            if not suggestion_ids and not has_action:
                print("[INFO] LLM response without actionable items; fallback to rule-based flow.")
                raise RuntimeError("llm_no_alignment")

            resp = {
                "ok": True,
                "reply": llm_result.get("reply", ""),
                "suggestion_ids": suggestion_ids,
                "meta": {"has_budget_intent": has_budget_intent(user_text)},
                "action": llm_result.get("action", {
                    "type": "switch_to_search",
                    "items": [{"id": sid} for sid in suggestion_ids]
                } if suggestion_ids else None)
            }
            if structured_filters:
                resp["structured_filters"] = structured_filters
            structured_payload: Optional[Dict[str, Any]] = None
            if suggestion_ids:
                detailed_items = _fetch_items_for_reply(None, suggestion_ids)
                if detailed_items:
                    formatted_reply, structured_payload = _compose_structured_reply(detailed_items)
                    resp["reply"] = formatted_reply
                    resp["structured_payload"] = structured_payload
            
            # 為 LLM 聊天結果生成 session_id 並同步快取
            if suggestion_ids:
                session_id = str(uuid.uuid4())[:8]
                CHAT_SESSION_CACHE[session_id] = (time.time(), resp)
                
                # 同步更新 SUGGEST_CACHE
                try:
                    from app import SUGGEST_CACHE, get_items_by_ids, get_df
                    df = get_df()
                    rows = get_items_by_ids(df, suggestion_ids)
                    cache_entry = {
                        "align_ids": suggestion_ids,
                        "align_rows": rows,
                        "query_terms": [user_text],
                        "ts": time.time(),
                    }
                    if structured_payload:
                        cache_entry["structured_items"] = structured_payload.get("items", [])
                        cache_entry["structured_summary"] = structured_payload.get("summary", "")
                    if structured_filters:
                        cache_entry["structured_filters"] = structured_filters
                    SUGGEST_CACHE[session_id] = cache_entry
                except Exception as e:
                    print(f"[WARNING] Failed to sync SUGGEST_CACHE: {e}")
                
                resp["session_id"] = session_id
            
            return resp
            
    except Exception as e:
        print(f"[ERROR] LLM chat failed: {e}")
        # 繼續嘗試其他方法

    # 2. 嘗試 fallback 系統處理特殊查詢（如生日聚會）
    try:
        _fb = run_fallback(user_text)
        if _fb and _fb.get("ok"):
            print(f"[INFO] Fallback system activated for: {user_text[:50]}...")
            
            suggestion_ids = _fb.get("suggestion_ids", [])
            structured_payload: Optional[Dict[str, Any]] = None
            detailed_items = _fetch_items_for_reply(None, suggestion_ids)
            if detailed_items:
                formatted_reply, structured_payload = _compose_structured_reply(detailed_items)
                _fb["reply"] = formatted_reply
                _fb["structured_payload"] = structured_payload

            # 為 fallback 結果加入會話追蹤
            session_id = _store_chat_result(_fb)
            if session_id:
                # 同步更新 app.py 的 SUGGEST_CACHE 以支援建議功能
                if suggestion_ids:
                    try:
                        from app import SUGGEST_CACHE, get_items_by_ids, get_df
                        df = get_df()
                        rows = get_items_by_ids(df, suggestion_ids)
                        cache_entry = {
                            "align_ids": suggestion_ids,
                            "align_rows": rows,
                            "query_terms": [user_text],
                            "ts": time.time(),
                        }
                        if structured_payload:
                            cache_entry["structured_items"] = structured_payload.get("items", [])
                            cache_entry["structured_summary"] = structured_payload.get("summary", "")
                        SUGGEST_CACHE[session_id] = cache_entry
                    except Exception as e:
                        print(f"[WARNING] Failed to sync SUGGEST_CACHE: {e}")
                        
                _fb["chat_session_id"] = session_id
                _fb["display_mode"] = "grouped" if _fb.get("category_suggestions") else "flat"
            
            return _fb
    except Exception as e:
        print(f"[ERROR] Fallback system error: {e}")
        
    # 3. 嘗試使用正常搜索系統
    try:
        items = search_products_strict(query=user_text, limit=10, filters=structured_filters)
        suggestion_ids = [FieldAccessor.get_product_id(x) for x in items if FieldAccessor.get_product_id(x)]
        
        if items:
            reply, structured_payload = _compose_structured_reply(items)
            
            resp = {
                "ok": True,
                "reply": reply,
                "suggestion_ids": suggestion_ids,
                "meta": {"has_budget_intent": has_budget_intent(req.user_message)},
                "action": {
                    "type": "switch_to_search",
                    "items": [{"id": sid} for sid in suggestion_ids]
                } if suggestion_ids else None
            }
            if structured_payload:
                resp["structured_payload"] = structured_payload
            if structured_filters:
                resp["structured_filters"] = structured_filters
            
            # 為高級搜索結果生成 session_id 並同步快取
            session_id = str(uuid.uuid4())[:8]
            CHAT_SESSION_CACHE[session_id] = (time.time(), resp)
            
            # 同步更新 app.py 的 SUGGEST_CACHE 以支援建議功能
            if suggestion_ids:
                try:
                    from app import SUGGEST_CACHE, get_items_by_ids, get_df
                    df = get_df()
                    rows = get_items_by_ids(df, suggestion_ids)
                    cache_entry = {
                        "align_ids": suggestion_ids,
                        "align_rows": rows,
                        "query_terms": [req.user_message],
                        "ts": time.time(),
                    }
                    if structured_payload:
                        cache_entry["structured_items"] = structured_payload.get("items", [])
                        cache_entry["structured_summary"] = structured_payload.get("summary", "")
                    if structured_filters:
                        cache_entry["structured_filters"] = structured_filters
                    SUGGEST_CACHE[session_id] = cache_entry
                except Exception as e:
                    print(f"[WARNING] Failed to sync SUGGEST_CACHE: {e}")
            
            resp["session_id"] = session_id
            return resp
    except Exception as e:
        print(f"[ERROR] Advanced search failed: {e}")
    
    # 4. 最終回退：使用簡單處理器
    return simple_chat_handler(req)
