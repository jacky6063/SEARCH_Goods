from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

CATE_MAP = {
    "餅乾": "餅乾類",
    "餅乾類": "餅乾類",
    "飲料": "飲料類",
    "飲料類": "飲料類",
}

_STRICT_PRODUCT_ID_PATTERNS: Sequence[re.Pattern[str]] = (
    re.compile(r"^[A-Za-z]{1,4}\d+[A-Za-z0-9\-]*$"),
    re.compile(r"^\d{10,}$"),
)
_PRODUCT_ID_WITH_TEXT = re.compile(
    r"(?:商品|產品)?編號[:：]?\s*[A-Za-z]*\d+[A-Za-z0-9\-]*", re.IGNORECASE
)
_PRODUCT_ID_KEYWORDS: Sequence[str] = ("商品編號", "產品編號", "編號", "ID", "id")

_RANGE_PATTERN = re.compile(
    r"(?P<min>\d{2,})(?:\s*元)?\s*(?:-|~|～|到|至)\s*(?P<max>\d{2,})(?:\s*元)?"
)
_SINGLE_PATTERNS: Sequence[re.Pattern[str]] = (
    re.compile(r"(?P<max>\d{2,})(?:元)?(?:以下|內|以內)"),
    re.compile(r"預算(?:是|為|在)?(?:大概)?(?P<max>\d{2,})(?:元)?"),
    re.compile(r"不超過(?P<max>\d{2,})(?:元)?"),
    re.compile(r"最多(?P<max>\d{2,})(?:元)?"),
    re.compile(r"上限(?P<max>\d{2,})(?:元)?"),
    re.compile(r"(?P<max>\d{2,})(?:元)?左右"),
)

_NUMBER_WITH_UNIT_PATTERN = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)(?P<unit>萬|千|k|K)?"
)
_BUDGET_KEYWORDS: Sequence[str] = ("預算", "價", "費", "上限", "最多", "不要超過")
_CONTEXT_WINDOW = 6


def _safe_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _looks_like_product_id(query: str) -> bool:
    """檢測查詢是否看起來像商品編號"""
    if not query:
        return False

    query = query.strip()
    if not query:
        return False

    for pattern in _STRICT_PRODUCT_ID_PATTERNS:
        if pattern.fullmatch(query):
            return True
    if _PRODUCT_ID_WITH_TEXT.search(query):
        return True

    if any(keyword in query for keyword in _PRODUCT_ID_KEYWORDS):
        # 需要同時帶有數字，避免純文字問題
        if re.search(r"\d{3,}", query):
            return True
    return False


def _normalize_number_with_unit(match: re.Match[str]) -> Optional[float]:
    value = match.group("num")
    unit = match.group("unit")
    number = _safe_float(value)
    if number is None:
        return None
    if not unit:
        return number
    if unit in {"k", "K", "千"}:
        return number * 1000
    if unit == "萬":
        return number * 10000
    return number


def _select_budget_candidate(text: str) -> Tuple[Optional[float], Optional[float]]:
    """尋找最貼近使用者語句的預算資訊"""
    candidates: List[Tuple[int, Optional[float], Optional[float]]] = []

    for match in _RANGE_PATTERN.finditer(text):
        min_price = _safe_float(match.group("min"))
        max_price = _safe_float(match.group("max"))
        if min_price is None or max_price is None:
            continue
        if min_price > max_price:
            min_price, max_price = max_price, min_price
        candidates.append((match.start(), min_price, max_price))

    for pattern in _SINGLE_PATTERNS:
        for match in pattern.finditer(text):
            max_price = _safe_float(match.group("max"))
            if max_price is None:
                continue
            candidates.append((match.start(), None, max_price))

    if not candidates:
        return None, None

    _, min_price, max_price = max(candidates, key=lambda item: item[0])
    return min_price, max_price


def _fallback_budget_with_keywords(text: str) -> Optional[float]:
    """在找不到明確樣式時，用關鍵字鄰近的數字作為預算"""
    hits: List[Tuple[int, float]] = []
    for match in _NUMBER_WITH_UNIT_PATTERN.finditer(text):
        value = _normalize_number_with_unit(match)
        if value is None:
            continue
        start, end = match.span()
        before = text[max(0, start - _CONTEXT_WINDOW):start]
        after = text[end:end + _CONTEXT_WINDOW]
        context = before + after
        if any(keyword in context for keyword in _BUDGET_KEYWORDS):
            hits.append((start, value))

    if not hits:
        return None
    return max(hits, key=lambda item: item[0])[1]


def _extract_categories(text: str) -> List[str]:
    cats: List[str] = []
    for key, value in CATE_MAP.items():
        if key in text and value not in cats:
            cats.append(value)
    return cats


def extract_budget_and_cats(text: str) -> Dict[str, Any]:
    text = text or ""

    # 🛡️ 如果查詢看起來是商品編號，跳過價格檢測
    if _looks_like_product_id(text):
        return {
            "budget": None,
            "budget_info": {"max_price": None, "min_price": None},
            "categories": [],
        }

    budget = None
    budget_info = {"max_price": None, "min_price": None}

    min_price, max_price = _select_budget_candidate(text)
    if min_price is not None or max_price is not None:
        budget_info["min_price"] = min_price
        budget_info["max_price"] = max_price
        budget = max_price
    else:
        fallback = _fallback_budget_with_keywords(text)
        if fallback is not None:
            budget = fallback
            budget_info["max_price"] = fallback

    cats = _extract_categories(text)
    return {
        "budget": budget,  # 向後相容
        "budget_info": budget_info,
        "categories": cats,
    }
