
# --- Hotfix for Card 1: flatten & dedupe items on /api/chat ---
from typing import Any, Dict, List, Optional, Set
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import time

try:
    from .goods_search_service import validate_plan_items, search_products, df_loaded_ok, ensure_dataset
except Exception:
    from goods_search_service import validate_plan_items, search_products, df_loaded_ok, ensure_dataset

try:
    from .llm_service import plan_from_chat
except Exception:
    def plan_from_chat(text: str) -> Dict[str, Any]:
        return {"groups": []}

router = APIRouter()

class ChatReq(BaseModel):
    text: str
    budget: Optional[float] = None
    user_id: Optional[str] = None

@router.post("/api/chat")
def chat(req: ChatReq):
    t0 = time.time()
    ensure_dataset()
    if not df_loaded_ok():
        raise HTTPException(status_code=503, detail="DATASET_NOT_READY")

    plan = plan_from_chat(req.text) or {}
    groups: List[List[Dict[str, Any]]] = plan.get("groups", []) or []

    validated_groups: List[List[Dict[str, Any]]] = []
    for g in groups:
        vg = validate_plan_items(g)
        if vg:
            validated_groups.append(vg)

    all_items: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for g in validated_groups:
        for it in g:
            pid = str(it.get("id") or it.get("GoodIden") or it.get("GoodID") or "")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            all_items.append({
                "id": pid,
                "name": it.get("name") or it.get("商品名稱") or it.get("Name") or ""
            })

    if not all_items:
        direct = search_products(query=req.text, limit=40)
        for it in direct:
            pid = str(it.get("GoodIden") or it.get("id") or "")
            if pid and pid not in seen:
                seen.add(pid)
                all_items.append({"id": pid, "name": it.get("name") or it.get("商品名稱") or ""})

    action = {
        "type": "switch_to_search",
        "reason": "chat_plan",
        "items": all_items,
    }
    meta = {
        "latency_ms": int((time.time() - t0) * 1000),
        "validated_groups": len(validated_groups),
        "total_items": len(all_items),
        "budget": req.budget,
    }
    return {"ok": True, "action": action, "meta": meta}
