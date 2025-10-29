from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from search_ext_goods_1024001 import search_products_strict, infer_filters_from_query
from field_utils import FieldAccessor, create_product_summary

router = APIRouter()

AGREE_WORDS = {"要","ok","OK","Ok","好","可以","行","確定","沒問題","那就這些","都可以","ＯＫ","Ｏk","ｏｋ"}

def has_budget_intent(text: str) -> bool:
    t = (text or "").strip()
    if not t: return False
    import re
    kw = re.compile(r"(預算|多少錢|多少元|價位|上限|便宜|貴不貴|價格)")
    money = re.compile(r"(\d[\d,\.]*)(\s*)(元|塊|\$)")
    return bool(kw.search(t) or money.search(t))

class ChatReq(BaseModel):
    text: str

@router.post("/api/chat")
def chat_handler(req: ChatReq):
    # 用強化搜尋拿 10 支（會依需求自動套類別/必含詞）
    base_filters = infer_filters_from_query(req.text)
    items = search_products_strict(query=req.text, limit=10, filters=base_filters)
    suggestion_ids = [FieldAccessor.get_product_id(x) for x in items if FieldAccessor.get_product_id(x)]

    # 基本文案（不含預算）
    if items:
        samples = create_product_summary(items, max_items=3)
        reply = f"我找到 {len(items)} 款商品，例如 {samples}。需要我顯示詳細介紹與圖片嗎？也可輸入 1=原建議、2=特價關聯、3=智慧搭配。"
    else:
        # 若套了鞋類過濾仍為 0，就明確回覆「此類無結果」，避免回不相干商品
        if base_filters:
            reply = "目前沒有符合此品類的結果。要不要換個關鍵詞或尺寸再試試？"
        else:
            reply = "目前找不到相符的商品，可以提供更多關鍵字嗎？"

    # 無預算意圖 → 不加任何預算段落
    resp: Dict[str, Any] = {
        "ok": True,
        "reply": reply,
        "suggestion_ids": suggestion_ids,   # ★ 等同「1.原建議」
        "meta": {
            "has_budget_intent": has_budget_intent(req.text)
        }
    }
    return resp
