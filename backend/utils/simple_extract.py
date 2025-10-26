from __future__ import annotations
import re
from typing import Dict, Any, List

CATE_MAP = {
    "餅乾": "餅乾類",
    "餅乾類": "餅乾類",
    "飲料": "飲料類",
    "飲料類": "飲料類",
}

def extract_budget_and_cats(text: str) -> Dict[str, Any]:
    text = text or ""
    # 預算（取最大片段數字）
    budget = None
    nums = re.findall(r"\d{2,}", text)
    if nums:
        try:
            budget = float(nums[-1])
        except Exception:
            budget = None
    # 類別
    cats: List[str] = []
    for k, v in CATE_MAP.items():
        if k in text and v not in cats:
            cats.append(v)
    return {"budget": budget, "categories": cats}