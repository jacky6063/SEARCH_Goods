from __future__ import annotations
from typing import List, Dict, Any, Optional
import csv
import os

"""
run_fallback：當 LLM 沒有產生可用的結構化建議時，使用本地 goods.csv 做保底推薦。
輸入參數盡量寬鬆，避免上層呼叫報錯。

輸出格式（建議）：
{
    "items": [
        {"id": "471xxxxx", "name": "xxx", "price": 79, "category": "餅乾類", "img": "..."},
        ...
    ],
    "meta": {
        "reason": "fallback",
        "budget": 1000,
        "categories": ["餅乾類","飲料類"]
    }
}
"""

def _load_goods_csv() -> List[Dict[str, Any]]:
    candidates = [
        os.path.join("backend","data","goods.csv"),
        os.path.join("data","goods.csv"),
    ]
    path = None
    for p in candidates:
        if os.path.isfile(p):
            path = p
            break
    if not path:
        return []
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # 標準化欄位名（盡量相容）
            item = {
                "id": r.get("id") or r.get("GoodIden") or r.get("barcode") or r.get("ID") or r.get("編號") or "",
                "name": r.get("name") or r.get("商品名稱") or r.get("Name") or "",
                "price": _safe_price(r.get("price") or r.get("售價") or r.get("Price")),
                "category": r.get("category") or r.get("類別") or r.get("大分類") or "",
                "img": r.get("img") or r.get("image") or r.get("圖片") or "",
            }
            rows.append(item)
    return rows

def _safe_price(v: Any) -> int:
    try:
        return int(float(str(v).strip()))
    except Exception:
        return 0

def _by_categories(items: List[Dict[str,Any]], cats: List[str]) -> List[Dict[str,Any]]:
    catset = {c.strip() for c in cats if c}
    if not catset:
        return items
    def ok(it):
        return (it.get("category") or "").strip() in catset
    return [it for it in items if ok(it)]

def run_fallback(
    query: Optional[str] = None,
    budget: Optional[float] = None,
    categories: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    保底邏輯：
    - 有指定 categories 就過濾該類別（如 ["餅乾類","飲料類"]）
    - 沒有就直接回前 20 筆
    - 若有 budget，會嘗試讓合計不要爆太多（簡單 greedy）
    """
    goods = _load_goods_csv()
    if not goods:
        # 沒資料也要回傳合法結構，避免上游 500
        return {"items": [], "meta": {"reason": "fallback_no_goods", "budget": budget, "categories": categories or []}}

    pool = _by_categories(goods, categories or [])
    if not pool:
        pool = goods[:]  # 沒過濾到就回全部做保底

    # 簡單的 greedy：由低到高累加，直到接近 budget
    pool_sorted = sorted(pool, key=lambda x: x.get("price") or 0)
    picked: List[Dict[str, Any]] = []
    if budget is None:
        picked = pool_sorted[:20]
    else:
        total = 0
        for it in pool_sorted:
            price = it.get("price") or 0
            if price <= 0:
                continue
            if total + price <= float(budget) * 1.05:  # 允許 5% 誤差
                picked.append(it)
                total += price
            if len(picked) >= 40:  # 避免一次塞太多
                break

    return {
        "items": picked,
        "meta": {
            "reason": "fallback",
            "budget": budget,
            "categories": categories or [],
            "count": len(picked)
        }
    }
