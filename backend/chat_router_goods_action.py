from fallback.multi_category_party import run_fallback
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from utils.llm_guard import safe_call_async
from utils.simple_extract import extract_budget_and_cats
__LLM_GUARD_INSTALLED__ = True
from search_ext_goods_1024001 import search_products_strict, infer_filters_from_query
from field_utils import FieldAccessor, create_product_summary
import uuid
import time

router = APIRouter()

# 聊天會話結果快取
CHAT_SESSION_CACHE = {}
CACHE_TTL = 300  # 5 分鐘 TTL

AGREE_WORDS = {"要","ok","OK","Ok","好","可以","行","確定","沒問題","那就這些","都可以","ＯＫ","Ｏk","ｏｋ"}

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
    
    if has_party and has_food:
        # 生日聚會場景的固定建議商品 ID
        suggestion_ids = [
            "4711202224557",  # 九福小餅(原味)
            "4713837028005",  # 星米果-蒜香海苔
            "4711202224403",  # 麻花(海苔口味)
            "4711202224410",  # 麻花(芝麻口味)
            "4713837030497",  # 海鹽洋芋片-香辣口味
        ]
        reply = f"我為您找到適合生日聚會的商品組合！包含餅乾和飲料的搭配建議，需要我顯示詳細介紹與圖片嗎？"
    elif "餅乾" in user_text or "cookie" in user_text.lower():
        suggestion_ids = [
            "4711202224557",  # 九福小餅(原味)
            "4711202224403",  # 麻花(海苔口味)
            "4711202224410",  # 麻花(芝麻口味)
        ]
        reply = f"我找到 {len(suggestion_ids)} 款餅乾商品，需要我顯示詳細介紹與圖片嗎？"
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
    
    # 儲存聊天結果並加入會話 ID
    if suggestion_ids:
        session_id = str(uuid.uuid4())[:8]
        CHAT_SESSION_CACHE[session_id] = (time.time(), resp)
        
        # 同步更新 app.py 的 SUGGEST_CACHE 以支援建議功能
        try:
            from app import SUGGEST_CACHE, get_items_by_ids, get_df
            df = get_df()
            rows = get_items_by_ids(df, suggestion_ids)
            SUGGEST_CACHE[session_id] = {
                "align_ids": suggestion_ids,
                "align_rows": rows,
                "query_terms": [user_text],
                "ts": time.time(),
            }
        except Exception as e:
            print(f"[WARNING] Failed to sync SUGGEST_CACHE: {e}")
        
        resp["chat_session_id"] = session_id
        resp["display_mode"] = "flat"
    
    return resp@router.post("/api/chat", response_model=ChatResponse)
def chat_handler(req: ChatReq):
    """主聊天處理器，優先使用複雜系統，失敗時回退到簡單處理"""
    try:
        # 優先嘗試 fallback 系統處理特殊查詢（如生日聚會）
        user_text = req.user_message.strip()
        _fb = run_fallback(user_text)
        if _fb and _fb.get("ok"):
            print(f"[INFO] Fallback system activated for: {user_text[:50]}...")
            
            # 為 fallback 結果加入會話追蹤
            session_id = _store_chat_result(_fb)
            if session_id:
                # 同步更新 app.py 的 SUGGEST_CACHE 以支援建議功能
                suggestion_ids = _fb.get("suggestion_ids", [])
                if suggestion_ids:
                    try:
                        from app import SUGGEST_CACHE, get_items_by_ids, get_df
                        df = get_df()
                        rows = get_items_by_ids(df, suggestion_ids)
                        SUGGEST_CACHE[session_id] = {
                            "align_ids": suggestion_ids,
                            "align_rows": rows,
                            "query_terms": [user_text],
                            "ts": time.time(),
                        }
                    except Exception as e:
                        print(f"[WARNING] Failed to sync SUGGEST_CACHE: {e}")
                        
                _fb["chat_session_id"] = session_id
                _fb["display_mode"] = "grouped" if _fb.get("category_suggestions") else "flat"
            
            return _fb
    except Exception as e:
        print(f"[ERROR] Fallback system error: {e}")
        # 回退到簡單處理器
        
    try:
        # 嘗試使用正常搜索系統
        items = search_products_strict(query=req.user_message.strip(), limit=10)
        suggestion_ids = [FieldAccessor.get_product_id(x) for x in items if FieldAccessor.get_product_id(x)]
        
        if items:
            samples = create_product_summary(items, max_items=3)
            reply = f"我找到 {len(items)} 款商品，例如 {samples}。需要我顯示詳細介紹與圖片嗎？"
            
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
            
            session_id = _store_chat_result(resp)
            if session_id:
                # 同步更新 app.py 的 SUGGEST_CACHE 以支援建議功能
                try:
                    from app import SUGGEST_CACHE, get_items_by_ids, get_df
                    df = get_df()
                    rows = get_items_by_ids(df, suggestion_ids)
                    SUGGEST_CACHE[session_id] = {
                        "align_ids": suggestion_ids,
                        "align_rows": rows,
                        "query_terms": [req.user_message],
                        "ts": time.time(),
                    }
                except Exception as e:
                    print(f"[WARNING] Failed to sync SUGGEST_CACHE: {e}")
                    
                resp["chat_session_id"] = session_id
                resp["display_mode"] = "flat"
            
            return resp
    except Exception as e:
        print(f"[ERROR] Advanced search failed: {e}")
    
    # 最終回退：使用簡單處理器
    return simple_chat_handler(req)
