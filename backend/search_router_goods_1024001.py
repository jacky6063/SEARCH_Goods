from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from goods_search_service import search_products
from promo_cache_goods_1024001 import get_promo_text

router = APIRouter()

class SearchReq(BaseModel):
    query: Optional[str] = None
    ids: Optional[List[str]] = None
    limit: Optional[int] = 40

@router.post("/api/search")
def search_with_promo(req: SearchReq):
    try:
        items: List[Dict[str, Any]] = search_products(
            query=req.query,
            ids=req.ids,
            limit=req.limit or 40
        ) or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SEARCH_ERROR: {e}")

    for it in items:
        if not it.get("promo"):
            try:
                it["promo"] = get_promo_text(it)
            except Exception:
                it["promo"] = ""

    return {"ok": True, "items": items, "total": len(items)}
