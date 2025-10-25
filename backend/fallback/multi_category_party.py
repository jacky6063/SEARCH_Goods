import os, re, json
from typing import List, Dict, Tuple, Optional

try:
    import pandas as pd
except Exception:
    pd = None

CAT_KEYWORDS = {
    "餅乾類": ["餅乾", "餅乾類", "餅乾乾", "蘇打餅", "洋芋片", "餅乾點心"],
    "飲料類": ["飲料", "飲料類", "果汁", "茶飲", "烏梅汁", "茶", "飲品"],
}

NUMBER_RE = re.compile(r'(\d{2,6})\s*元?')

def parse_budget(text: str) -> Optional[int]:
    if not text:
        return None
    m = NUMBER_RE.search(text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None

def need_fallback(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    has_cookie = any(k in t for k in CAT_KEYWORDS["餅乾類"])
    has_drink  = any(k in t for k in CAT_KEYWORDS["飲料類"])
    return bool(has_cookie and has_drink)

def _possible_goods_paths() -> List[str]:
    cands = [
        os.path.join("data", "goods.csv"),
        os.path.join("backend", "data", "goods.csv"),
        os.path.join(os.getcwd(), "data", "goods.csv"),
        os.path.join(os.getcwd(), "backend", "data", "goods.csv"),
    ]
    return [p for p in cands if os.path.isfile(p)]

def load_catalog() -> Optional["pd.DataFrame"]:
    if pd is None:
        return None
    for p in _possible_goods_paths():
        try:
            df = pd.read_csv(p, dtype=str, encoding="utf-8")
            # 正規化欄位
            cols = {c.lower(): c for c in df.columns}
            # 期待存在：商品名/名稱、價格、id 或條碼
            # 常見可能：Name, Title, 商品名稱, 商品名, Price, 價格, id, GoodIden, 條碼, barcode
            return df
        except Exception:
            continue
    return None

def _col(df, *cands):
    # 找出第一個存在的欄位名（不區分大小寫 / 中英）
    lower = {c.lower(): c for c in df.columns}
    for x in cands:
        if x.lower() in lower:
            return lower[x.lower()]
    return None

def select_by_category(df, cat_words: List[str], limit: int = 10) -> List[Dict]:
    name_col = _col(df, "商品名稱", "商品名", "name", "title")
    price_col = _col(df, "價格", "price", "售價")
    id_col = _col(df, "GoodIden", "goodiden", "id", "barcode", "條碼", "sku")
    if not (name_col and price_col and id_col):
        return []

    hits = []
    for _, row in df.iterrows():
        name = str(row.get(name_col, ""))
        price = str(row.get(price_col, ""))
        gid = str(row.get(id_col, ""))
        if not gid or not name:
            continue
        # 關鍵字命中算進此類
        if any(w in name for w in cat_words):
            # 價格取整數（取數字部分）
            m = re.search(r'\d+', price)
            p = int(m.group(0)) if m else None
            hits.append({"id": gid, "name": name, "price": p})
        if len(hits) >= limit:
            break
    return hits

def compose_reply(bucket: Dict[str, List[Dict]], budget: Optional[int]) -> Tuple[str, List[str]]:
    lines = ["以下是我為您推薦的商品組合："]
    all_ids: List[str] = []
    total = 0

    order = ["餅乾類", "飲料類"]
    for k in order:
        items = bucket.get(k, [])
        if not items:
            continue
        lines.append(f"\n{order.index(k)+1}. {k}：")
        for it in items:
            all_ids.append(it["id"])
            if it.get("price") is not None:
                total += it["price"]
            pr = f"{it['price']}元" if it.get("price") is not None else "—"
            lines.append(f"   - {it['name']}  價格: {pr}")

    if budget:
        remain = budget - total
        lines.append(f"\n預估金額約 {total} 元，預算 {budget} 元，剩餘 {remain} 元。")
    else:
        lines.append(f"\n預估金額約 {total} 元。")

    return ("\n".join(lines), all_ids)

def run_fallback(user_text: str, per_cat_limit: int = 8) -> Optional[Dict]:
    if not need_fallback(user_text):
        return None

    df = load_catalog()
    if df is None:
        # 沒找到商品清單，返回 None 讓上層改回原路徑
        return None

    bucket = {
        "餅乾類": select_by_category(df, CAT_KEYWORDS["餅乾類"], limit=per_cat_limit),
        "飲料類": select_by_category(df, CAT_KEYWORDS["飲料類"], limit=per_cat_limit),
    }
    # 若兩類都空，放棄回退
    if not bucket["餅乾類"] and not bucket["飲料類"]:
        return None

    budget = parse_budget(user_text)
    reply, ids = compose_reply(bucket, budget)

    payload = {
        "ok": True,
        "reply": reply,
        "suggestion_ids": ids,                 # 重要：全部 ids，用於商品模式完整呈現
        "action": {
            "type": "switch_to_search",
            "items": [{"id": i} for i in ids]  # 保險：前端可由此渲染
        },
        "meta": {"source": "fallback_multi_category"}
    }
    return payload
