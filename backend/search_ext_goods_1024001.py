from typing import List, Dict, Any, Optional
from goods_search_service import search_products as base_search
from field_utils import FieldAccessor

SHOE_SYNS = ["慢跑鞋","跑鞋","運動鞋","球鞋","鞋"]
BAG_SYNS = ["背包","包包","包款","女包","女用背包","肩背包","後背包","雙肩包","手提包","隨身包"]

def infer_filters_from_query(text: str, extra_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    t = (text or "").strip()
    merged: Dict[str, Any] = {}
    if any(s in t for s in SHOE_SYNS):
        merged = {
            "category_filter": "鞋",
            "must_have_keywords": ["鞋"],
        }
    if any(s in t for s in BAG_SYNS):
        must = ["背包", "包"]
        bag_filter = {
            "category_filter": "包",
            "must_have_keywords": must,
            "excluded_keywords": ["湯", "燉包", "茶", "醬", "調味", "湯包"],
        }
        if merged:
            merged["category_filter"] = bag_filter["category_filter"]
            merged["must_have_keywords"] = list(dict.fromkeys((merged.get("must_have_keywords") or []) + bag_filter["must_have_keywords"]))
            excluded = list(dict.fromkeys((merged.get("excluded_keywords") or []) + bag_filter.get("excluded_keywords") or []))
            if excluded:
                merged["excluded_keywords"] = excluded
        else:
            merged = bag_filter
    if extra_filters:
        category = extra_filters.get("category_filter") or merged.get("category_filter")
        must = list(dict.fromkeys((merged.get("must_have_keywords") or []) + (extra_filters.get("must_have_keywords") or [])))
        excluded = list(dict.fromkeys((merged.get("excluded_keywords") or []) + (extra_filters.get("excluded_keywords") or [])))
        merged = {}
        if category:
            merged["category_filter"] = category
        if must:
            merged["must_have_keywords"] = must
        if excluded:
            merged["excluded_keywords"] = excluded
    return merged

def filter_items(items: List[Dict[str, Any]],
                 category_filter: Optional[str]=None,
                 must_have_keywords: Optional[List[str]]=None,
                 excluded_keywords: Optional[List[str]]=None) -> List[Dict[str, Any]]:
    out = items
    if category_filter:
        lowered_category = str(category_filter).lower()
        out = [
            x for x in out
            if lowered_category in FieldAccessor.get_category(x).lower()
        ]
    if must_have_keywords:
        for kw in must_have_keywords:
            k = str(kw).lower()
            def _has_keyword(item: Dict[str, Any]) -> bool:
                name = FieldAccessor.get_name(item).lower()
                desc = str(item.get("DESCRIPTION") or item.get("商品描述") or "").lower()
                category = FieldAccessor.get_category(item).lower()
                return k in name or k in desc or k in category
            out = [x for x in out if _has_keyword(x)]
    if excluded_keywords:
        lowered_excluded = [str(kw).lower() for kw in excluded_keywords if kw]
        if lowered_excluded:
            def _is_excluded(item: Dict[str, Any]) -> bool:
                haystack = " ".join([
                    FieldAccessor.get_name(item).lower(),
                    FieldAccessor.get_category(item).lower(),
                    str(item.get("DESCRIPTION") or item.get("商品描述") or "").lower(),
                ])
                return any(kw in haystack for kw in lowered_excluded)
            out = [x for x in out if not _is_excluded(x)]
    return out

def search_products_strict(query: Optional[str]=None,
                           ids: Optional[List[str]]=None,
                           limit: int=40,
                           filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    # 先用原本的搜尋拿候選，再做強化過濾
    if query:
        # 需要載入 DataFrame 來調用 base_search
        from app import get_df
        df = get_df()
        if df is not None:
            products, _ = base_search(df=df, query=query, topn=limit*3)
            candidates = products
        else:
            candidates = []
    else:
        candidates = []
    if query and not ids:
        inferred = infer_filters_from_query(query, filters)
        combined_filters = filters or {}
        if inferred:
            combined_filters = {
                "category_filter": inferred.get("category_filter") or combined_filters.get("category_filter"),
                "must_have_keywords": list(dict.fromkeys((combined_filters.get("must_have_keywords") or []) + (inferred.get("must_have_keywords") or []))),
                "excluded_keywords": list(dict.fromkeys((combined_filters.get("excluded_keywords") or []) + (inferred.get("excluded_keywords") or []))),
            }
        category_filter = combined_filters.get("category_filter") if combined_filters else None
        must_keywords = combined_filters.get("must_have_keywords") if combined_filters else None
        excluded_keywords = combined_filters.get("excluded_keywords") if combined_filters else None
        candidates = filter_items(candidates, category_filter, must_keywords, excluded_keywords)
    return candidates[:limit]
