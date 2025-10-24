
# --- Hotfix for Card 2: performance improvements in goods_search_service ---
from __future__ import annotations
import os
from functools import lru_cache
from typing import Dict, List, Any, Optional

import pandas as pd

DATA_PATH = os.environ.get("DATA_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "VIEW_GOODS_enhanced.csv"))
_df: Optional[pd.DataFrame] = None
_row_by_id: Dict[str, Dict[str, Any]] = {}
_name_lower_col = "name_lower"

def ensure_dataset() -> None:
    global _df, _row_by_id
    if _df is not None:
        return
    dtype = {
        "GoodIden": "string",
        "name": "string",
        "分類名稱": "string",
    }
    df = pd.read_csv(DATA_PATH, dtype=dtype, na_filter=False)
    if "name" in df.columns:
        df[_name_lower_col] = df["name"].astype("string").str.lower()
    elif "商品名稱" in df.columns:
        df[_name_lower_col] = df["商品名稱"].astype("string").str.lower()
    else:
        df[_name_lower_col] = ""

    _row_by_id = {}
    id_col = "GoodIden" if "GoodIden" in df.columns else ("商品編號" if "商品編號" in df.columns else None)
    if id_col:
        for _, row in df.iterrows():
            rid = str(row.get(id_col))
            _row_by_id[rid] = row.to_dict()
    _df = df

def df_loaded_ok() -> bool:
    return _df is not None

@lru_cache(maxsize=2048)
def _norm_token(s: str) -> str:
    return (s or "").strip().lower()

def validate_plan_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ensure_dataset()
    out: List[Dict[str, Any]] = []
    if not items:
        return out
    for it in items:
        pid = str(it.get("id") or it.get("GoodIden") or "")
        if pid and pid in _row_by_id:
            out.append(_row_by_id[pid])
            continue
        nm = it.get("name") or it.get("商品名稱") or ""
        nm = _norm_token(nm)
        if not nm:
            continue
        mask = _df[_name_lower_col].str.contains(nm, na=False)
        if mask.any():
            out.append(_df[mask].iloc[0].to_dict())
    return out

def search_products(query: Optional[str]=None, ids: Optional[List[str]]=None, limit: int=40) -> List[Dict[str, Any]]:
    ensure_dataset()
    if ids:
        res = []
        for pid in ids:
            row = _row_by_id.get(str(pid))
            if row:
                res.append(row)
        return res[:limit]
    if not query:
        return _df.head(limit).to_dict(orient="records")

    q = _norm_token(query)
    mask = _df[_name_lower_col].str.contains(q, na=False)
    if not mask.any():
        return []
    return _df[mask].head(limit).to_dict(orient="records")
