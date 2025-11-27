from typing import List, Dict, Any, Optional
from goods_search_service import (
    search_products as base_search,
    is_product_id_query,
)
from field_utils import FieldAccessor
from services.search_service import (
    is_negative_query,
    filter_low_confidence_products,
    MIN_CONFIDENCE_SCORE,
)

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
                 excluded_keywords: Optional[List[str]]=None,
                 price_filter: Optional[Dict[str, Any]]=None) -> List[Dict[str, Any]]:
    out = items
    
    # 類別過濾
    if category_filter:
        lowered_category = str(category_filter).lower()
        out = [
            x for x in out
            if lowered_category in FieldAccessor.get_category(x).lower()
        ]
    
    # 關鍵字必須包含過濾
    if must_have_keywords:
        for kw in must_have_keywords:
            k = str(kw).lower()
            def _has_keyword(item: Dict[str, Any]) -> bool:
                name = FieldAccessor.get_name(item).lower()
                desc = str(item.get("DESCRIPTION") or item.get("商品描述") or "").lower()
                category = FieldAccessor.get_category(item).lower()
                # 🔧 新增：檢查 REMARK 欄位（商品標籤）
                remark = str(item.get("REMARK") or item.get("備註") or "").lower()
                return k in name or k in desc or k in category or k in remark
            out = [x for x in out if _has_keyword(x)]
    
    # 排除關鍵字過濾  
    if excluded_keywords:
        lowered_excluded = [str(kw).lower() for kw in excluded_keywords if kw]
        if lowered_excluded:
            def _is_excluded(item: Dict[str, Any]) -> bool:
                haystack = " ".join([
                    FieldAccessor.get_name(item).lower(),
                    FieldAccessor.get_category(item).lower(),
                    str(item.get("DESCRIPTION") or item.get("商品描述") or "").lower(),
                    # 🔧 新增：檢查 REMARK 欄位（商品標籤）
                    str(item.get("REMARK") or item.get("備註") or "").lower(),
                ])
                return any(kw in haystack for kw in lowered_excluded)
            out = [x for x in out if not _is_excluded(x)]
    
    # 🆕 價格過濾
    if price_filter:
        min_price = price_filter.get("min_price")
        max_price = price_filter.get("max_price")
        
        def _price_in_range(item: Dict[str, Any]) -> bool:
            # 優先使用特價，再使用原價
            special_price = FieldAccessor.get_special_price(item)
            regular_price = FieldAccessor.get_price(item)
            
            # 取得有效價格（特價優先，否則用原價）
            effective_price = special_price if special_price and special_price > 0 else regular_price
            
            if not effective_price or effective_price <= 0:
                return False  # 沒有有效價格的商品被排除
                
            # 檢查價格範圍
            if min_price is not None and effective_price < min_price:
                return False
            if max_price is not None and effective_price > max_price:
                return False
            return True
        
        out = [x for x in out if _price_in_range(x)]
    
    return out

def search_products_strict(query: Optional[str]=None,
                           ids: Optional[List[str]]=None,
                           limit: int=40,
                           filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    # 先用原本的搜尋拿候選，再做強化過濾
    if query and is_negative_query(query):
        return []
    product_id_query = bool(query and is_product_id_query(query))
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
    if product_id_query:
        return candidates[:limit]
    if query and not ids:
        inferred = infer_filters_from_query(query, filters)
        combined_filters: Dict[str, Any] = dict(filters or {})
        if inferred:
            if inferred.get("category_filter"):
                combined_filters["category_filter"] = inferred["category_filter"]
            if inferred.get("must_have_keywords"):
                existing_must = combined_filters.get("must_have_keywords") or []
                combined_filters["must_have_keywords"] = list(
                    dict.fromkeys(existing_must + inferred.get("must_have_keywords", []))
                )
            if inferred.get("excluded_keywords"):
                existing_excluded = combined_filters.get("excluded_keywords") or []
                combined_filters["excluded_keywords"] = list(
                    dict.fromkeys(existing_excluded + inferred.get("excluded_keywords", []))
                )
            if inferred.get("price_filter"):
                existing_price = combined_filters.get("price_filter") or {}
                merged_price = dict(existing_price)
                merged_price.update(
                    {k: v for k, v in inferred["price_filter"].items() if v is not None}
                )
                combined_filters["price_filter"] = merged_price
        category_filter = combined_filters.get("category_filter") if combined_filters else None
        must_keywords = combined_filters.get("must_have_keywords") if combined_filters else None
        excluded_keywords = combined_filters.get("excluded_keywords") if combined_filters else None
        price_filter = combined_filters.get("price_filter") if combined_filters else None
        candidates = filter_items(candidates, category_filter, must_keywords, excluded_keywords, price_filter)
    # 僅在候選包含分數欄位時才做低信心過濾，避免把無分數的基礎結果全數排除
    if any((c.get("__score__") is not None) or (c.get("score") is not None) for c in candidates):
        candidates = filter_low_confidence_products(candidates, min_score=MIN_CONFIDENCE_SCORE)
    return candidates[:limit]
