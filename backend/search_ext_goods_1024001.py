from typing import List, Dict, Any, Optional
from goods_search_service import search_products as base_search

SHOE_SYNS = ["慢跑鞋","跑鞋","運動鞋","球鞋","鞋"]

def infer_filters_from_query(text: str) -> Dict[str, Any]:
    t = (text or "").strip()
    if any(s in t for s in SHOE_SYNS):
        return {
            "category_filter": "鞋",           # 用於字面過濾
            "must_have_keywords": ["鞋"],      # 名稱必含詞，避免拌麵之類誤入
        }
    return {}

def filter_items(items: List[Dict[str, Any]],
                 category_filter: Optional[str]=None,
                 must_have_keywords: Optional[List[str]]=None) -> List[Dict[str, Any]]:
    out = items
    if category_filter:
        out = [x for x in out if category_filter in str(x.get("分類名稱",""))]
    if must_have_keywords:
        name_get = lambda x: str(x.get("name") or x.get("商品名稱") or "").lower()
        for kw in must_have_keywords:
            k = str(kw).lower()
            out = [x for x in out if k in name_get(x)]
    return out

def search_products_strict(query: Optional[str]=None,
                           ids: Optional[List[str]]=None,
                           limit: int=40) -> List[Dict[str, Any]]:
    # 先用原本的搜尋拿候選，再做強化過濾
    candidates = base_search(query=query, ids=ids, limit=limit*3 if query else limit)
    if query and not ids:
        f = infer_filters_from_query(query)
        candidates = filter_items(candidates, f.get("category_filter"), f.get("must_have_keywords"))
    return candidates[:limit]
