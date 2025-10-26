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
        reply = f"""我為您規劃的生日聚會商品組合：

🍪 **餅乾類** (8款，約400-500元)：
- 洋芋片系列 (玫瑰鹽、香辣、岩燒海苔) 
- 蘇達餅系列 (黑芝麻、椒鹽、燕麥起司、紅藜紫菜)
- 星米果 (蒜香海苔)

🥤 **飲料類商品** 會在下一輪為您推薦

總預算控制在 1000 元內，需要我顯示詳細商品資訊嗎？也可輸入 1=查看推薦、2=特價商品、3=智慧搭配。"""
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
    """主聊天處理器，整合真正的 LLM 聊天功能"""
    user_text = req.user_message.strip()
    history = req.history or []
    
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
        
        if llm_result and llm_result.get("reply"):
            print(f"[INFO] LLM chat activated for: {user_text[:50]}...")
            
            # 處理 LLM 聊天結果
            suggestion_ids = []
            alignment = llm_result.get("alignment")
            if alignment and alignment.get("items"):
                suggestion_ids = [item.get("id") for item in alignment["items"] if item.get("id")]
            has_action = isinstance(llm_result.get("action"), dict) and llm_result["action"].get("type") and llm_result["action"].get("type") != "none"
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
            
            # 為 LLM 聊天結果生成 session_id 並同步快取
            if suggestion_ids:
                session_id = str(uuid.uuid4())[:8]
                CHAT_SESSION_CACHE[session_id] = (time.time(), resp)
                
                # 同步更新 SUGGEST_CACHE
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
        
    # 3. 嘗試使用正常搜索系統
    try:
        items = search_products_strict(query=user_text, limit=10)
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
            
            # 為高級搜索結果生成 session_id 並同步快取
            session_id = str(uuid.uuid4())[:8]
            CHAT_SESSION_CACHE[session_id] = (time.time(), resp)
            
            # 同步更新 app.py 的 SUGGEST_CACHE 以支援建議功能
            if suggestion_ids:
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
            
            resp["session_id"] = session_id
            return resp
    except Exception as e:
        print(f"[ERROR] Advanced search failed: {e}")
    
    # 4. 最終回退：使用簡單處理器
    return simple_chat_handler(req)
