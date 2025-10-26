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
    CHAT_SESSION_CACHE[session_id] = {
        "category_suggestions": result.get("category_suggestions"),
        "suggestion_ids": result.get("suggestion_ids", []),
        "action": result.get("action"),
        "meta": result.get("meta", {}),
        "timestamp": time.time()
    }
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

@router.post("/api/chat", response_model=ChatResponse)
def chat_handler(req: ChatReq):
    # === goods_1024002 fallback: 餅乾+飲料＋(預算) → 規則式回覆 ===
    user_text = req.user_message.strip()
    
    # 清理過期快取
    _cleanup_session_cache()
    
    # 優先嘗試 fallback 系統處理特殊查詢（如生日聚會）
    try:
        _fb = run_fallback(user_text)
        if _fb and _fb.get("ok"):
            print(f"[INFO] Fallback system activated for: {user_text[:50]}...")
            
            # 為 fallback 結果加入會話追蹤
            session_id = _store_chat_result(_fb)
            if session_id:
                _fb["chat_session_id"] = session_id
                _fb["display_mode"] = "grouped" if _fb.get("category_suggestions") else "flat"
            
            return _fb
    except Exception as _e:
        print(f"[ERROR] Fallback system error: {_e}")
        # 繼續執行正常搜索
        
    # 執行正常商品搜尋
    items = search_products_strict(query=user_text, limit=10)
    suggestion_ids = [FieldAccessor.get_product_id(x) for x in items if FieldAccessor.get_product_id(x)]

    # 如果正常搜索沒結果且包含特殊場景關鍵字，提供更好的回覆
    if not items:
        # 檢查是否包含生日聚會等特殊場景
        party_keywords = ["生日", "聚會", "派對", "party", "慶祝", "活動"]
        food_keywords = ["餅乾", "飲料", "點心", "零食", "茶", "汁"]
        
        has_party = any(kw in user_text for kw in party_keywords)
        has_food = any(kw in user_text for kw in food_keywords)
        
        if has_party and has_food:
            reply = "我為您找到適合生日聚會的商品組合！正在為您準備餅乾和飲料的搭配建議，請稍候..."
            # 嘗試再次觸發 fallback 或提供基本建議
            from fallback.multi_category_party import select_all_by_keywords, CAT_KEYWORDS, load_catalog
            try:
                df = load_catalog()
                if df is not None:
                    cookie_items = select_all_by_keywords(df, CAT_KEYWORDS["餅乾類"])
                    drink_items = select_all_by_keywords(df, CAT_KEYWORDS["飲料類"])
                    if cookie_items or drink_items:
                        # 提取一些 ID 作為建議，使用統一的 ID 存取方式
                        backup_ids = []
                        if cookie_items:
                            backup_ids.extend([item.get("id", "") for item in cookie_items[:5] if item.get("id")])
                        if drink_items:
                            backup_ids.extend([item.get("id", "") for item in drink_items[:5] if item.get("id")])
                        suggestion_ids = [id for id in backup_ids[:10] if id]  # 限制在 10 個且過濾空值
                        reply = f"我找到了適合生日聚會的商品！包含 {len(cookie_items)} 款餅乾和 {len(drink_items)} 款飲料。"
            except Exception as e:
                print(f"[ERROR] Backup fallback failed: {e}")
    
    # 正常搜索有結果的回覆
    if items:
        samples = create_product_summary(items, max_items=3)
        reply = f"我找到 {len(items)} 款商品，例如 {samples}。需要我顯示詳細介紹與圖片嗎？也可輸入 1=原建議、2=特價關聯、3=智慧搭配。"
    elif not suggestion_ids:  # 沒有商品也沒有備用建議
        if infer_filters_from_query(user_text):
            reply = "目前沒有符合此品類的結果。要不要換個關鍵詞或尺寸再試試？"
        else:
            reply = "目前在資料中找不到符合的商品 🙏\n您可以提供品牌、類型或預算範圍嗎？我再幫您縮小範圍。"

    resp: Dict[str, Any] = {
        "ok": True,
        "reply": reply,
        "suggestion_ids": suggestion_ids,
        "meta": {"has_budget_intent": has_budget_intent(user_text)},
        # ★ 新增 action，舊前端也能切商品模式
        "action": {
            "type": "switch_to_search",
            "items": [{"id": sid} for sid in suggestion_ids]
        } if suggestion_ids else None
    }
    
    # 儲存聊天結果並加入會話 ID
    session_id = _store_chat_result(resp)
    if session_id:
        resp["chat_session_id"] = session_id
        resp["display_mode"] = "flat"  # 一般聊天為平面顯示
    
    return resp
