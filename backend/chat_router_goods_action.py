from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from search_ext_goods_1024001 import search_products_strict, infer_filters_from_query

router = APIRouter()

AGREE_WORDS = {"要","ok","OK","Ok","好","可以","行","確定","沒問題","那就這些","都可以","ＯＫ","Ｏk","ｏｋ"}

def has_budget_intent(text: str) -> bool:
    import re
    t = (text or "").strip()
    kw = re.compile(r"(預算|多少錢|多少元|價位|上限|便宜|貴不貴|價格)")
    money = re.compile(r"(\d[\d,\.]*)(\s*)(元|塊|\$)")
    return bool(kw.search(t) or money.search(t))

class ChatReq(BaseModel):
    text: str

@router.post("/api/chat")
def chat_handler(req: ChatReq):
    text = (req.text or "").strip()
    items = search_products_strict(query=text, limit=10)
    suggestion_ids = [str(x.get("GoodIden") or x.get("id")) for x in items if (x.get("GoodIden") or x.get("id"))]

    # 回覆文字
    if items:
        samples = "、".join((str(items[i].get("name") or items[i].get("商品名稱")) for i in range(min(3, len(items)))))
        reply = f"我找到 {len(items)} 款商品，例如 {samples}。需要我顯示詳細介紹與圖片嗎？也可輸入 1=原建議、2=特價關聯、3=智慧搭配。"
    else:
        if infer_filters_from_query(text):
            reply = "目前沒有符合此品類的結果。要不要換個關鍵詞或尺寸再試試？"
        else:
            reply = "目前找不到相符的商品，可以提供更多關鍵字嗎？"

    resp: Dict[str, Any] = {
        "ok": True,
        "reply": reply,
        "suggestion_ids": suggestion_ids,
        "meta": {"has_budget_intent": has_budget_intent(text)},
        # ★ 新增 action，舊前端也能切商品模式
        "action": {
            "type": "switch_to_search",
            "items": [{"id": sid} for sid in suggestion_ids]
        } if suggestion_ids else None
    }
    return resp
