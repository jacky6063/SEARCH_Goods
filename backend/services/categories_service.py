from __future__ import annotations
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Set
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CATEGORIES_PATH = os.getenv("CATEGORIES_PATH") or str(ROOT / "data" / "goods_categories.csv")
CATEGORIES_CACHE_TTL = int(os.getenv("CATEGORIES_CACHE_TTL", "300"))

@dataclass
class CategoriesState:
    df: Optional[pd.DataFrame] = None
    path: str = DEFAULT_CATEGORIES_PATH
    ts: float = 0.0
    last_error: Optional[str] = None

_state = CategoriesState()


def get_diagnostics() -> Dict[str, Any]:
    """Return basic diagnostics for admin panel without exposing sensitive data."""
    try:
        df = _ensure_loaded()
        entries = int(len(df.index)) if isinstance(df, pd.DataFrame) else 0
    except Exception:
        entries = 0
    return {
        "categories_path": os.getenv("CATEGORIES_PATH") or _state.path,
        "entries_count": entries,
        "last_loaded": _state.ts,
        "last_error": _state.last_error,
        "cache_ttl": CATEGORIES_CACHE_TTL,
    }

REQUIRED_COLS = ["L1", "L2", "L3"]
OPTIONAL_COLS = {
    "Enabled": True,
    "DisplayOrder": None,
    "Synonyms": None,
}

_CATEGORY_TERMS_CACHE: Set[str] = set()
_CATEGORY_TERMS_TS: float = 0.0
_TAXONOMY_INDEX_CACHE: Dict[str, Any] = {}
_TAXONOMY_INDEX_TS: float = 0.0


def _norm_name(val: Any) -> str:
    s = str(val or "").strip()
    # 全形斜線 → 半形，統一空白
    s = s.replace("／", "/")
    s = re.sub(r"\s+", " ", s)
    return s

# === 公開查詢輔助 ===
def get_all_categories(force: bool = False) -> List[Dict[str, Any]]:
    """
    取得啟用中的分類清單（已正規化、過濾 Disabled）。
    回傳欄位：L1/L2/L3/DisplayOrder。
    """
    df = _ensure_loaded(force=force)
    if df is None or df.empty:
        return []
    cols = ["L1", "L2", "L3", "DisplayOrder"]
    existing = [c for c in cols if c in df.columns]
    return df[existing].to_dict(orient="records")

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    # Ensure required columns exist
    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = ""
    for col, default in OPTIONAL_COLS.items():
        if col not in df.columns:
            df[col] = default
    # Normalize types
    def _to_bool(v: Any) -> bool:
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in ("1", "true", "yes", "y"): return True
        if s in ("0", "false", "no", "n", ""): return False
        return False
    def _to_int(v: Any) -> Optional[int]:
        try:
            return int(str(v).strip())
        except Exception:
            return None
    out = df.copy()
    # Strip whitespace
    for col in ["L1", "L2", "L3", "Synonyms"]:
        if col in out.columns:
            out[col] = out[col].astype(str).fillna("").map(lambda s: s.strip())
    # Enabled
    out["Enabled"] = out["Enabled"].map(_to_bool)
    # DisplayOrder
    out["DisplayOrder"] = out["DisplayOrder"].map(_to_int)
    # Drop disabled rows
    out = out[out["Enabled"] == True]
    # Remove fully empty rows
    out = out[~(out["L1"].astype(str).str.strip() == "")]
    # 產生正規化欄位（用於寬鬆比對）
    out["_L1n"] = out["L1"].map(_norm_name)
    out["_L2n"] = out["L2"].map(_norm_name)
    out["_L3n"] = out["L3"].map(_norm_name)
    # Deduplicate
    out = out.drop_duplicates(subset=["L1", "L2", "L3"], keep="first")
    return out


def _normalize_term_for_match(text: str) -> str:
    if not text:
        return ""
    folded = _norm_name(text)
    folded = re.sub(r"\s+", "", folded)
    return folded.lower()


def _sort_names(names: List[Tuple[str, Optional[int]]]) -> List[str]:
    # Sort by DisplayOrder (None treated as large), then by name asc
    def key_fn(x: Tuple[str, Optional[int]]):
        name, order = x
        order_key = order if order is not None else 10_000_000
        return (order_key, str(name))
    return [n for n, _ in sorted(names, key=key_fn)]


def _ensure_loaded(force: bool = False) -> pd.DataFrame:
    global _state
    now = time.time()
    path = os.getenv("CATEGORIES_PATH") or _state.path or DEFAULT_CATEGORIES_PATH
    need_reload = (
        _state.df is None or force or (now - _state.ts) > CATEGORIES_CACHE_TTL or _state.path != path
    )
    if not need_reload:
        return _state.df if _state.df is not None else pd.DataFrame()
    try:
        p = Path(path)
        if not p.exists():
            _state = CategoriesState(df=pd.DataFrame(), path=path, ts=now, last_error=f"not found: {path}")
            return _state.df
        raw = pd.read_csv(p, dtype=str, encoding="utf-8-sig").fillna("")
        df = _normalize_df(raw)
        _state = CategoriesState(df=df, path=path, ts=now, last_error=None)
        return df
    except Exception as e:
        _state = CategoriesState(df=pd.DataFrame(), path=path, ts=now, last_error=str(e))
        return _state.df


def get_category_terms(force: bool = False) -> Set[str]:
    """取得所有啟用分類與同義詞的白名單集合，用於查詢校驗。"""
    global _CATEGORY_TERMS_CACHE, _CATEGORY_TERMS_TS
    now = time.time()
    if not force and _CATEGORY_TERMS_CACHE and (now - _CATEGORY_TERMS_TS) <= CATEGORIES_CACHE_TTL:
        return _CATEGORY_TERMS_CACHE

    df = _ensure_loaded(force=force)
    terms: Set[str] = set()
    if df is None or df.empty:
        _CATEGORY_TERMS_CACHE = set()
        _CATEGORY_TERMS_TS = now
        return _CATEGORY_TERMS_CACHE

    for col in ("L1", "L2", "L3"):
        if col in df.columns:
            series = df[col].astype(str).fillna("")
            for raw in series:
                normalized = _normalize_term_for_match(raw)
                if normalized:
                    terms.add(normalized)

    if "Synonyms" in df.columns:
        for raw in df["Synonyms"].astype(str).fillna(""):
            if not raw.strip():
                continue
            for token in re.split(r"[、,/|；;，,\s]+", raw):
                normalized = _normalize_term_for_match(token)
                if normalized:
                    terms.add(normalized)

    _CATEGORY_TERMS_CACHE = terms
    _CATEGORY_TERMS_TS = now
    return terms


def is_known_category_term(term: str) -> bool:
    """檢查字詞是否屬於啟用分類或其同義詞。"""
    normalized = _normalize_term_for_match(term)
    if not normalized:
        return False
    whitelist = get_category_terms()
    if not whitelist:
        return False
    if normalized in whitelist:
        return True
    # 支援子字串匹配，避免「米」 vs 「米類」等命名差異
    for candidate in whitelist:
        if not candidate:
            continue
        if normalized in candidate or candidate in normalized:
            return True
    return False


def reset() -> None:
    """Clear cache to force reload on next access."""
    global _state, _CATEGORY_TERMS_CACHE, _CATEGORY_TERMS_TS, _TAXONOMY_INDEX_CACHE, _TAXONOMY_INDEX_TS
    _state = CategoriesState(df=None, path=os.getenv("CATEGORIES_PATH") or DEFAULT_CATEGORIES_PATH, ts=0.0, last_error=None)
    _CATEGORY_TERMS_CACHE = set()
    _CATEGORY_TERMS_TS = 0.0
    _TAXONOMY_INDEX_CACHE = {}
    _TAXONOMY_INDEX_TS = 0.0


def set_categories_path(path: str) -> None:
    """
    更新分類檔路徑並清除相關快取。
    """
    global _state, _CATEGORY_TERMS_CACHE, _CATEGORY_TERMS_TS, _TAXONOMY_INDEX_CACHE, _TAXONOMY_INDEX_TS
    _state = CategoriesState(df=None, path=str(path), ts=0.0, last_error=None)
    _CATEGORY_TERMS_CACHE = set()
    _CATEGORY_TERMS_TS = 0.0
    _TAXONOMY_INDEX_CACHE = {}
    _TAXONOMY_INDEX_TS = 0.0


def get_scope(level: str = "L1", parent_l1: Optional[str] = None, parent_l2: Optional[str] = None, top_k: Optional[int] = None) -> Dict[str, Any]:
    df = _ensure_loaded()
    level = (level or "L1").upper()
    if df is None or df.empty:
        return {
            "level": level, "total": 0, "top_k": int(top_k or 0), "more_count": 0,
            "items": [], "context": _build_context(level, parent_l1, parent_l2)
        }
    working = df
    if level in ("L2", "L3") and parent_l1:
        working = working[working["_L1n"] == _norm_name(parent_l1)]
    if level == "L3" and parent_l2:
        working = working[working["_L2n"] == _norm_name(parent_l2)]
    if level == "L1":
        series = working["L1"].astype(str)
        # aggregate by L1 with min DisplayOrder
        orders = working.groupby("L1")["DisplayOrder"].min().to_dict()
        names_with_order = [(name, orders.get(name)) for name in sorted(set(series))]
    elif level == "L2":
        series = working["L2"].astype(str)
        series = series[series.str.strip() != ""]
        # aggregate by L2 with min DisplayOrder
        orders = working[working["L2"].astype(str).str.strip() != ""].groupby("L2")["DisplayOrder"].min().to_dict()
        names_with_order = [(name, orders.get(name)) for name in sorted(set(series))]
    else:  # L3
        series = working["L3"].astype(str)
        series = series[series.str.strip() != ""]
        orders = working[working["L3"].astype(str).str.strip() != ""].groupby("L3")["DisplayOrder"].min().to_dict()
        names_with_order = [(name, orders.get(name)) for name in sorted(set(series))]

    ordered_names = _sort_names(names_with_order)
    total = len(ordered_names)
    limit = None
    if top_k is not None:
        try:
            limit = max(0, int(top_k))
        except Exception:
            limit = None
    if limit is not None and limit > 0:
        visible = ordered_names[:limit]
        more_count = max(0, total - len(visible))
        topk_out = limit
    else:
        visible = ordered_names
        more_count = 0
        topk_out = len(visible)
    items = [{"name": n} for n in visible]
    return {
        "level": level,
        "total": total,
        "top_k": topk_out,
        "more_count": more_count,
        "items": items,
        "context": _build_context(level, parent_l1, parent_l2),
    }


def _build_taxonomy_index(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {"l1": [], "l2": [], "l3": []}

    l1_orders = df.groupby("L1")["DisplayOrder"].min().to_dict()
    l1_entries: List[Dict[str, Any]] = []
    for name in sorted(set(df["L1"].astype(str))):
        cleaned = name.strip()
        if not cleaned:
            continue
        l1_entries.append(
            {
                "name": cleaned,
                "norm": _normalize_term_for_match(cleaned),
                "order": l1_orders.get(name),
            }
        )
    l1_entries = sorted(
        l1_entries,
        key=lambda entry: (
            entry.get("order") if entry.get("order") is not None else 10_000_000,
            entry.get("name", ""),
        ),
    )

    l2_entries: List[Dict[str, Any]] = []
    l2_rows = (
        df[df["L2"].astype(str).str.strip() != ""]
        .groupby(["L1", "L2"])["DisplayOrder"]
        .min()
        .reset_index()
    )
    for _, row in l2_rows.iterrows():
        l1 = str(row["L1"]).strip()
        l2 = str(row["L2"]).strip()
        l2_entries.append(
            {
                "l1": l1,
                "l2": l2,
                "norm": _normalize_term_for_match(l2),
                "order": row.get("DisplayOrder"),
            }
        )
    l2_entries = sorted(
        l2_entries,
        key=lambda entry: (
            entry.get("order") if entry.get("order") is not None else 10_000_000,
            entry.get("l1", ""),
            entry.get("l2", ""),
        ),
    )

    l3_entries: List[Dict[str, Any]] = []
    l3_rows = (
        df[df["L3"].astype(str).str.strip() != ""]
        .groupby(["L1", "L2", "L3"])["DisplayOrder"]
        .min()
        .reset_index()
    )
    for _, row in l3_rows.iterrows():
        l1 = str(row["L1"]).strip()
        l2 = str(row["L2"]).strip()
        l3 = str(row["L3"]).strip()
        l3_entries.append(
            {
                "l1": l1,
                "l2": l2,
                "l3": l3,
                "norm": _normalize_term_for_match(l3),
                "order": row.get("DisplayOrder"),
            }
        )
    l3_entries = sorted(
        l3_entries,
        key=lambda entry: (
            entry.get("order") if entry.get("order") is not None else 10_000_000,
            entry.get("l1", ""),
            entry.get("l2", ""),
            entry.get("l3", ""),
        ),
    )

    return {"l1": l1_entries, "l2": l2_entries, "l3": l3_entries}


def get_taxonomy_index(force: bool = False) -> Dict[str, Any]:
    """提供 L1/L2/L3 唯一清單與層級關係，供聊天/導覽判斷。"""
    global _TAXONOMY_INDEX_CACHE, _TAXONOMY_INDEX_TS
    now = time.time()
    if (
        not force
        and _TAXONOMY_INDEX_CACHE
        and (now - _TAXONOMY_INDEX_TS) <= CATEGORIES_CACHE_TTL
    ):
        return _TAXONOMY_INDEX_CACHE
    df = _ensure_loaded(force=force)
    index = _build_taxonomy_index(df if isinstance(df, pd.DataFrame) else pd.DataFrame())
    _TAXONOMY_INDEX_CACHE = index
    _TAXONOMY_INDEX_TS = now
    return index


def _build_context(level: str, parent_l1: Optional[str], parent_l2: Optional[str]) -> Dict[str, Any]:
    level = (level or "L1").upper()
    if level == "L1":
        label = "熱門分類"
    elif level == "L2":
        label = f"熱門中分類（{(parent_l1 or '').strip()}）" if parent_l1 else "熱門中分類"
    else:
        if parent_l1 and parent_l2:
            label = f"熱門小分類（{parent_l1.strip()} > {parent_l2.strip()}）"
        else:
            label = "熱門小分類"
    return {
        "level": level,
        "parent_l1": parent_l1,
        "parent_l2": parent_l2,
        "label": label,
    }
