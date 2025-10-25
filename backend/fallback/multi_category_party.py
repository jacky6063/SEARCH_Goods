import os, re
from typing import List, Dict, Optional, Tuple

try:
    import pandas as pd
except Exception:
    pd = None

# 類別關鍵字（可再擴充）
CAT_KEYWORDS = {
    "餅乾類": ["餅乾", "餅乾類", "蘇打餅", "洋芋片", "餅乾點心", "脆餅", "餅"],
    "飲料類": ["飲料", "飲料類", "果汁", "茶飲", "烏梅汁", "茶", "飲品", "汽水"],
}

NUMBER_RE = re.compile(r'(\d{2,6})\s*元?')

# ===== 基本工具 =====
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

def _possible_paths() -> List[str]:
    cands = [
        "data/goods.csv",
        "backend/data/goods.csv",
        os.path.join(os.getcwd(), "data/goods.csv"),
        os.path.join(os.getcwd(), "backend/data/goods.csv"),
    ]
    return [p for p in cands if os.path.isfile(p)]

def load_catalog():
    if pd is None:
        return None
    for path in _possible_paths():
        try:
            return pd.read_csv(path, dtype=str, encoding="utf-8")
        except Exception:
            continue
    return None

def _col(df, *names):
    lowers = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lowers:
            return lowers[n.lower()]
    return None

def to_price_int(s: str) -> Optional[int]:
    if s is None:
        return None
    m = re.search(r'\d+', str(s))
    return int(m.group(0)) if m else None

# ===== 類別挑選 =====
def select_all_by_keywords(df, keywords: List[str]) -> List[Dict]:
    """取出命中該類別關鍵字的所有商品（含 name/price/id）"""
    name_col = _col(df, "商品名稱", "商品名", "name", "title")
    price_col = _col(df, "價格", "price", "售價")
    id_col = _col(df, "GoodIden", "goodiden", "id", "barcode", "條碼", "sku")
    if not (name_col and price_col and id_col):
        return []
    rows: List[Dict] = []
    for _, row in df.iterrows():
        name = str(row.get(name_col, "")).strip()
        price = to_price_int(row.get(price_col))
        gid = str(row.get(id_col, "")).strip()
        if not gid or not name:
            continue
        if any(w in name for w in keywords):
            rows.append({"id": gid, "name": name, "price": price})
    return rows

def avg_price(items: List[Dict]) -> Optional[float]:
    vals = [it["price"] for it in items if isinstance(it.get("price"), int)]
    if not vals:
        return None
    return sum(vals) / len(vals)

# ===== 混合式分配 =====
def count_terms(text: str, words: List[str]) -> int:
    t = text or ""
    return sum(t.count(w) for w in words)

def mixed_ratio(user_text: str, cookie_items: List[Dict], drink_items: List[Dict]) -> float:
    """
    回傳餅乾比例 (0.2 ~ 0.8)
    規則：
      1) 基準 0.6（餅乾）/ 0.4（飲料）
      2) 語意加權：若文字偏向某類 => 在 ±0.1 範圍微調
      3) 均價修正：某類均價 >= 1.8x 另一類 => 向該類 +0.1
    """
    cookie_base = 0.6
    cookie_ratio = cookie_base

    # 語意加權
    c_cnt = count_terms(user_text, CAT_KEYWORDS["餅乾類"])
    d_cnt = count_terms(user_text, CAT_KEYWORDS["飲料類"])
    if c_cnt > d_cnt:
        cookie_ratio += 0.1
    elif d_cnt > c_cnt:
        cookie_ratio -= 0.1

    # 均價修正
    ac = avg_price(cookie_items) or 0
    ad = avg_price(drink_items) or 0
    if ac and ad:
        if ad >= 1.8 * ac:      # 飲料貴很多 → 多給飲料
            cookie_ratio -= 0.1
        elif ac >= 1.8 * ad:    # 餅乾貴很多 → 多給餅乾
            cookie_ratio += 0.1

    # 夾在 [0.2, 0.8]
    cookie_ratio = max(0.2, min(0.8, cookie_ratio))
    return cookie_ratio

# ===== 在各自預算內裝配商品（貪婪，低價優先，避免超支）=====
def pack_under_budget(items: List[Dict], budget: int, max_items: int = 999) -> Tuple[List[Dict], int]:
    """依價格升冪裝配，回傳(入選清單, 小計)"""
    items_sorted = sorted(items, key=lambda x: (x["price"] is None, x["price"] if x["price"] is not None else 10**9))
    picked: List[Dict] = []
    total = 0
    for it in items_sorted:
        p = it["price"] or 0
        if p <= 0 and len(picked) < max_items:
            picked.append(it)
            continue
        if p > 0 and total + p <= budget and len(picked) < max_items:
            picked.append(it)
            total += p
    return picked, total

# ===== 組合回覆 =====
def compose_reply(cookie_picked: List[Dict], drink_picked: List[Dict],
                  cookie_budget: Optional[int], drink_budget: Optional[int],
                  grand_budget: Optional[int]) -> Tuple[str, List[str]]:
    ids: List[str] = []
    total = 0
    lines = ["以下是我為您規劃的商品組合："]

    # 餅乾類
    if cookie_picked:
        lines.append("\n1. 餅乾類：")
        for it in cookie_picked:
            ids.append(it["id"])
            pr = f"{it['price']}元" if it.get("price") is not None else "—"
            lines.append(f"   - {it['name']}  價格: {pr}")
            if it.get("price"): total += it["price"]
        if cookie_budget is not None:
            lines.append(f"   ▶ 餅乾類分配預算：{cookie_budget} 元")

    # 飲料類
    if drink_picked:
        lines.append("\n2. 飲料類：")
        for it in drink_picked:
            ids.append(it["id"])
            pr = f"{it['price']}元" if it.get("price") is not None else "—"
            lines.append(f"   - {it['name']}  價格: {pr}")
            if it.get("price"): total += it["price"]
        if drink_budget is not None:
            lines.append(f"   ▶ 飲料類分配預算：{drink_budget} 元")

    if grand_budget is not None:
        remain = grand_budget - total
        lines.append(f"\n預估金額約 {total} 元，總預算 {grand_budget} 元，剩餘 {remain} 元。")
    else:
        lines.append(f"\n預估金額約 {total} 元。")

    return ("\n".join(lines), ids)

# ===== 主入口 =====
def run_fallback(user_text: str) -> Optional[Dict]:
    if not need_fallback(user_text):
        return None

    df = load_catalog()
    if df is None:
        return None

    # 全量候選
    cookie_all = select_all_by_keywords(df, CAT_KEYWORDS["餅乾類"])
    drink_all  = select_all_by_keywords(df, CAT_KEYWORDS["飲料類"])
    if not cookie_all and not drink_all:
        return None

    budget = parse_budget(user_text)

    # --- 沒提供預算：沿用舊邏輯（各取多筆） ---
    if budget is None:
        # 取前 8 筆做展示
        cookie_picked = sorted(cookie_all, key=lambda x: (x["price"] is None, x["price"] if x["price"] else 10**9))[:8]
        drink_picked  = sorted(drink_all,  key=lambda x: (x["price"] is None, x["price"] if x["price"] else 10**9))[:8]
        reply, ids = compose_reply(cookie_picked, drink_picked, None, None, None)
        return {
            "ok": True,
            "reply": reply,
            "suggestion_ids": ids,
            "action": {"type": "switch_to_search", "items": [{"id": i} for i in ids]},
            "meta": {"source": "fallback_multi_category_no_budget"},
        }

    # --- 有預算：啟用混合式分配 ---
    cookie_ratio = mixed_ratio(user_text, cookie_all, drink_all)
    cookie_budget = int(budget * cookie_ratio)
    drink_budget  = budget - cookie_budget

    cookie_picked, cookie_sum = pack_under_budget(cookie_all, cookie_budget)
    drink_picked,  drink_sum  = pack_under_budget(drink_all,  drink_budget)

    # 若某類完全挑不到，嘗試從另一類補滿（保守，不超過總預算）
    used = cookie_sum + drink_sum
    if not cookie_picked and drink_picked and (budget - used) > 0:
        extra_cookie, add_sum = pack_under_budget(cookie_all, budget - used)
        cookie_picked.extend(extra_cookie); used += add_sum
    if not drink_picked and cookie_picked and (budget - used) > 0:
        extra_drink, add_sum = pack_under_budget(drink_all, budget - used)
        drink_picked.extend(extra_drink); used += add_sum

    reply, ids = compose_reply(cookie_picked, drink_picked, cookie_budget, drink_budget, budget)
    return {
        "ok": True,
        "reply": reply,
        "suggestion_ids": ids,
        "action": {"type": "switch_to_search", "items": [{"id": i} for i in ids]},
        "meta": {
            "source": "fallback_multi_category_mixed_ratio",
            "ratio_cookie": cookie_ratio,
            "budget_split": {"cookie": cookie_budget, "drink": drink_budget}
        },
    }
