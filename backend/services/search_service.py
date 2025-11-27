from __future__ import annotations

import unicodedata
from typing import Any, Dict, Iterable, List

# 本服務不再依賴外部 app.config，內建一組常見的非販售品關鍵字白名單
DEFAULT_NEGATIVE_KEYWORDS = [
    "汽車", "房屋", "手機", "平板", "電腦", "相機",
    "腳踏車", "單車", "自行車", "家電", "冷氣", "冰箱",
    "洗衣機", "電視", "筆電", "主機板", "顯示卡"
]
_NEGATIVE_KEYWORDS = [kw.lower() for kw in DEFAULT_NEGATIVE_KEYWORDS if kw]

NEGATIVE_QUERY_MESSAGE = "目前沒有販售這類商品喔～但我可以協助您找到合適的生活用品！想請問您的用途是？"
LOW_CONFIDENCE_MESSAGE = "我可以協助您找到更適合的商品～您比較偏向哪一種用途呢？"
MIN_CONFIDENCE_SCORE = 0.55



def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", (text or "").strip())
    return normalized.lower()


def is_negative_query(query: str) -> bool:
    """Return True if the query contains any negative keywords (e.g., 汽車、房屋)."""
    normalized = _normalize_text(query)
    if not normalized:
        return False
    return any(kw in normalized for kw in _NEGATIVE_KEYWORDS)


def filter_low_confidence_products(
    products: Iterable[Dict[str, Any]], *, min_score: float = MIN_CONFIDENCE_SCORE
) -> List[Dict[str, Any]]:
    """Filter products by score to avoid irrelevant matches (e.g., 汽車→包包)."""
    filtered: List[Dict[str, Any]] = []
    for product in products or []:
        score = product.get("__score__")
        if score is None:
            score = product.get("score")
        try:
            score_value = float(score)
        except (TypeError, ValueError):
            score_value = 0.0
        if score_value >= min_score:
            filtered.append(product)
    return filtered


__all__ = [
    "is_negative_query",
    "filter_low_confidence_products",
    "NEGATIVE_QUERY_MESSAGE",
    "LOW_CONFIDENCE_MESSAGE",
    "MIN_CONFIDENCE_SCORE",
]
