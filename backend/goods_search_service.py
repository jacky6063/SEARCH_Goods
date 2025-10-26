# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import os
from pathlib import Path
import pandas as pd
import re
from typing import List, Tuple, Dict, Any, Iterable, Optional
from difflib import get_close_matches

DEFAULT_KWS: List[str] = [
    "鞋","球鞋","籃球","跑步","登山","包","背包","手提包","斜背包","肩背包","外套","褲","襪",
    "廚房","料理","調味","醬","油","鹽","糖","胡椒","香料","醋","醬油","芝麻","胡麻","昆布","高湯"
]


_COLUMN_DEFINITION_PATH = Path(__file__).with_name("column_definitions.json")
ROOT = Path(__file__).resolve().parents[1]

# 自動檢測 Render 環境的正確 CSV 路徑
def _get_csv_path():
    """自動檢測並返回正確的 CSV 文件路徑"""
    # 如果環境變數已設定，直接使用
    env_path = os.getenv("DATA_PATH")
    if env_path:
        return Path(env_path)
    
    # Render 環境路徑檢測
    render_path = Path("/opt/render/project/src/data/VIEW_GOODS_enhanced.csv")
    if render_path.exists():
        return render_path
    
    # 默認本地開發路徑
    return ROOT / "data" / "VIEW_GOODS_enhanced.csv"

DEFAULT_DATA_PATH = _get_csv_path()
_GOODS_ROWS_CACHE: Optional[List[Dict[str, Any]]] = None


def _load_column_mapping() -> Dict[str, str]:
    """Load mapping from localized column labels to canonical column names."""
    if not _COLUMN_DEFINITION_PATH.exists():
        return {}
    try:
        data = json.loads(_COLUMN_DEFINITION_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    mapping: Dict[str, str] = {}
    if isinstance(data, dict):
        for canonical, labels in data.items():
            if isinstance(labels, list):
                for label in labels:
                    label = (label or "").strip()
                    if not label:
                        continue
                    mapping[label] = canonical
            elif isinstance(labels, str):
                label = labels.strip()
                if label:
                    mapping[label] = canonical
    return mapping


COLUMN_NAME_MAP: Dict[str, str] = _load_column_mapping()

# simple typo / synonym replacements applied before tokenising
QUERY_REPLACEMENTS: Dict[str, str] = {
    "磁心": "慈心",
    "慈新": "慈心",
}

NUMERIC_FIELD_ALIASES: Dict[str, List[str]] = {
    "Price": ["價格", "價錢", "價位", "price", "售價"],
    "SpecialOffer": ["特價", "優惠價", "促銷價", "折扣價", "specialoffer", "special_offer"],
}

CATEGORY_SYNONYMS: Dict[str, List[str]] = {
    "皮帶": ["腰帶"],
    "皮夾": ["錢包", "短夾", "長夾", "男用錢包", "男用短夾", "男用長夾"],
    "包": ["包包", "手提包", "肩背包", "斜背包", "背包", "女用包", "休閒包"],
    "休閒食品": ["零食", "點心", "小點", "餅乾"],
    "鞋": ["鞋子", "鞋款", "運動鞋", "跑鞋"],
}

GENERAL_TERM_HINTS: Tuple[str, ...] = (
    "男",
    "女",
    "童",
    "嬰",
    "孕",
    "紳士",
    "淑女",
    "大人",
    "小孩",
    "有機",
    "慈心",
    "純素",
    "全素",
    "奶素",
    "無糖",
    "無調味",
    "低糖",
    "低鹽",
    "無添加",
    "進口",
    "原味",
    "特價",
)

REQUIRED_PHRASE_CONFIG: Dict[str, Dict[str, Any]] = {
    "有機認證": {"aliases": ["有機認證", "有機驗證", "有機農產品驗證", "有機"], "columns": None},
    "醬油": {"aliases": ["醬油", "蔭油", "蔭油膏", "蔭油露", "soy sauce"], "columns": ["Name"]},
    "無調味": {"aliases": ["無調味", "原味", "不調味"], "columns": None},
    "核桃": {"aliases": ["核桃", "walnut"], "columns": ["Name", "DESCRIPTION"]},
    "堅果": {"aliases": ["堅果", "nut"], "columns": ["CateName", "Name", "DESCRIPTION"]},
}


def _normalize_query_text(text: str) -> str:
    out = text or ""
    for wrong, correct in QUERY_REPLACEMENTS.items():
        out = out.replace(wrong, correct)
    return out


def _requires_special_offer(query: str) -> bool:
    """Detect intent that explicitly asks for discounted items."""
    normalized = _normalize_query_text(query or "").lower()
    if "特價" not in normalized:
        return False
    # direct phrases like "有特價", "只要特價", "特價的"
    if "有特價" in normalized or "特價的" in normalized:
        return True
    patterns = [
        r"(只要|需要|想要|我要|給我)[^，。,.]{0,6}特價",
        r"特價[^，。,.]{0,4}(商品|貨|鞋|款|的)",
        r"特價[^，。,.]{0,4}(有哪些|有什麼|清單)",
    ]
    return any(re.search(pat, normalized) for pat in patterns)


def _required_phrases(query: str) -> List[Tuple[List[str], Optional[List[str]]]]:
    normalized = _normalize_query_text(query or "").lower()
    required: List[Tuple[List[str], Optional[List[str]]]] = []
    for key, cfg in REQUIRED_PHRASE_CONFIG.items():
        if key in normalized:
            required.append((cfg["aliases"], cfg.get("columns")))
    # handle generic "必須有機" etc.
    if "必須" in normalized and "有機" in normalized:
        required.append((["有機"], None))
    if "一定要" in normalized and "有機" in normalized:
        required.append((["有機"], None))
    return required


def _row_contains_all(row: Dict[str, Any], phrase_groups: List[Tuple[List[str], Optional[List[str]]]]) -> bool:
    if not phrase_groups:
        return True
    text = _row_text(row)
    for aliases, columns in phrase_groups:
        if columns:
            hit = False
            for col in columns:
                val = str(row.get(col, "")).lower()
                if any((alias or "").lower() in val for alias in aliases):
                    hit = True
                    break
            if not hit:
                return False
        else:
            if not any((alias or "").lower() in text for alias in aliases):
                return False
    return True


def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig").fillna("")
    if df.empty or not COLUMN_NAME_MAP:
        return df
    rename_map: Dict[str, str] = {}
    for col in df.columns:
        col_stripped = col.strip()
        target = COLUMN_NAME_MAP.get(col_stripped)
        if target:
            rename_map[col] = target
    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def _norm(s: str) -> str:
    return str(s or "").strip().lower()


def _ordered_unique(items: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for item in items:
        normalized = _norm(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _expand_category_terms(terms: List[str]) -> List[str]:
    expanded: List[str] = []
    for term in terms:
        normalized = _norm(term)
        if not normalized:
            continue
        expanded.append(normalized)
        for synonym in CATEGORY_SYNONYMS.get(normalized, []):
            expanded.append(_norm(synonym))
    return _ordered_unique(expanded)


def _chinese_ngrams(text: str, min_len: int = 2, max_len: int = 4) -> List[str]:
    chars = [c for c in text if "\u4e00" <= c <= "\u9fff"]
    joined = "".join(chars)
    if not joined:
        return []
    ngrams: List[str] = []
    length = len(joined)
    max_len = min(max_len, length)
    for size in range(min_len, max_len + 1):
        for idx in range(0, length - size + 1):
            ngrams.append(joined[idx:idx + size])
    # include single Chinese character if all longer ngrams failed later
    if length == 1 and min_len > 1:
        ngrams.append(joined)
    return ngrams


def extract_terms(query: str) -> List[str]:
    normalized = _normalize_query_text(query or "")
    q = _norm(normalized)
    parts = [p for p in re.split(r"[ ,;|/+\-]+", q) if p]
    number_tokens: List[str] = re.findall(r"\d+(?:\.\d+)?", q)
    ranges: List[str] = re.findall(r"(\d+(?:\.\d+)?)\s*[-~～至]\s*(\d+(?:\.\d+)?)", q)
    for low, high in ranges:
        number_tokens.append(low)
        number_tokens.append(high)
    zh_terms: List[str] = []
    if not parts:
        zh_terms = _chinese_ngrams(q)
    else:
        for token in parts:
            if any("\u4e00" <= ch <= "\u9fff" for ch in token) and len(token) >= 4:
                zh_terms.extend(_chinese_ngrams(token))
    extra = [kw for kw in DEFAULT_KWS if kw in q]
    ordered = _ordered_unique(parts + zh_terms + extra + number_tokens)
    if not ordered and q:
        ordered = _ordered_unique(_chinese_ngrams(q, min_len=1, max_len=2))
    return ordered


def _row_text(row: Dict[str, Any]) -> str:
    parts = [
        row.get("Name", ""),
        row.get("DESCRIPTION") or row.get("Description") or "",
        row.get("CateName") or row.get("分類名稱") or "",
        row.get("REMARK") or row.get("備註") or "",
    ]
    return " ".join(str(p) for p in parts).lower()


def score_row(row: Dict[str, Any], terms: List[str]) -> float:
    text = _row_text(row)
    score = 0.0
    for t in terms:
        normalized = _norm(t)
        if not normalized:
            continue
        expanded_terms = _expand_category_terms([normalized])
        if any(term in text for term in expanded_terms):
            in_name = normalized in str(row.get("Name","" )).lower()
            if in_name:
                score += 2.0
            elif normalized.isdigit() or re.fullmatch(r"\d+(?:\.\d+)?", normalized):
                score += 0.5
            else:
                score += 1.0

    if "Has_SpecialOffer" in row and str(row["Has_SpecialOffer"]).lower() in ("true","1"):
        score += 0.2
    return score


def search_products(
    df: pd.DataFrame,
    query: str,
    topn: int = 10,
    min_score: float = 1.5,
    sort_price: bool = False,
    required_terms: Optional[List[str]] = None,
    category_terms: Optional[List[str]] = None,
    excluded_terms: Optional[List[str]] = None,
) -> Tuple[list[dict], List[str]]:
    terms = extract_terms(query)
    if df.empty:
        return [], terms
    records = df.to_dict(orient="records")
    scores: List[float] = [score_row(r, terms) for r in records]
    sdf = df.copy()
    raw_category_terms: List[str] = _ordered_unique([_norm(c) for c in (category_terms or []) if c])
    category_terms_lower: List[str] = raw_category_terms.copy()
    sdf["__score__"] = scores
    if _requires_special_offer(query) and "SpecialOffer" in sdf.columns:
        sdf = sdf[sdf["SpecialOffer"].astype(str).str.strip() != ""]
        if sdf.empty:
            return [], terms
    category_terms_from_required: List[str] = []
    general_required_terms: List[str] = []
    if required_terms:
        for term in required_terms:
            normalized = _norm(term)
            if not normalized:
                continue
            if any(hint in normalized for hint in GENERAL_TERM_HINTS):
                general_required_terms.append(normalized)
            else:
                category_terms_from_required.append(normalized)
    category_terms_from_required = _ordered_unique(category_terms_from_required)
    general_required_terms = _ordered_unique(general_required_terms)
    if category_terms_from_required:
        category_terms_lower.extend(category_terms_from_required)
        raw_category_terms.extend(category_terms_from_required)
        raw_category_terms = _ordered_unique(raw_category_terms)
    grouped_results: Dict[str, pd.DataFrame] = {}
    singled_terms: List[str] = []
    for base, synonyms in category_group_synonyms.items() if "category_group_synonyms" in locals() else []:
        if base in category_group_candidates:
            grouped_results[base] = category_group_candidates[base]
        else:
            singled_terms.extend(synonyms)
    combined_category_terms = _expand_category_terms(category_terms_lower)
    category_group_synonyms: Dict[str, List[str]] = {
        base: _expand_category_terms([base]) for base in raw_category_terms
    }
    # fallback group for general topics when no category_terms supplied
    fallback_group = None
    if not category_group_synonyms:
        category_group_synonyms = {}
    fallback_synonyms: List[str] = []
    fallback_base: Optional[str] = None
    if not category_group_synonyms:
        fallback_base = None
        for base in DEFAULT_FALLBACK_CATEGORIES:
            synonyms = _expand_category_terms([base])
            if any(term in query for term in synonyms):
                fallback_base = base
                fallback_synonyms = synonyms
                break
        if fallback_base:
            category_group_synonyms = {fallback_base: fallback_synonyms}
            fallback_group = fallback_base
    category_group_candidates: Dict[str, pd.DataFrame] = {}
    if category_group_synonyms:
        for base, synonyms in category_group_synonyms.items():
            group_df = df[df.apply(lambda row: any(term in _row_text(row.to_dict()) for term in synonyms), axis=1)]
            if not group_df.empty:
                category_group_candidates[base] = group_df
    if combined_category_terms:
        filtered_by_category = sdf[sdf.apply(lambda row: any(cat in _row_text(row.to_dict()) for cat in combined_category_terms), axis=1)]
        if not filtered_by_category.empty:
            sdf = filtered_by_category
    numeric_filters = _parse_numeric_filters(query)
    if numeric_filters:
        sdf = _apply_numeric_filters(sdf, numeric_filters)
        if sdf.empty:
            return [], terms
    thresholds: List[float] = [min_score]
    if min_score > 1.0:
        thresholds.append(1.0)
    if min_score > 0.5:
        thresholds.append(0.5)
    filtered_frames: List[pd.DataFrame] = []
    for threshold in thresholds:
        candidate = sdf[sdf["__score__"] >= threshold]
        if candidate.empty:
            continue
        filtered_frames.append(candidate)
        combined = pd.concat(filtered_frames).drop_duplicates()
        if len(combined.index) >= topn:
            break
    if filtered_frames:
        filtered = pd.concat(filtered_frames).drop_duplicates()
    else:
        filtered = sdf
    # if all scores are zero, treat as no match
    if filtered["__score__"].max() <= 0:
        return [], terms
    # apply optional required phrase filtering
    required_groups = _required_phrases(query)
    if general_required_terms:
        required_groups.extend([(general_required_terms, None)])
    if excluded_terms:
        lowered_excl = [e.lower() for e in excluded_terms if e]
    else:
        lowered_excl = []
    if required_groups:
        filtered_general = filtered[filtered.apply(lambda row: _row_contains_all(row.to_dict(), required_groups), axis=1)]
        if not filtered_general.empty:
            filtered = filtered_general
    if lowered_excl:
        filtered = filtered[~filtered.apply(lambda row: any(ex in _row_text(row.to_dict()) for ex in lowered_excl), axis=1)]
        if filtered.empty:
            return [], terms
    # domain-specific name filters
    name_filter_keywords: List[str] = []
    cleaned_query = query.replace("男生", "").replace("先生", "")
    if "醬油" in terms or any("醬油" in t for t in raw_category_terms) or (required_terms and any("醬油" in t for t in required_terms)):
        name_filter_keywords.extend(["醬油", "蔭油"])
    if any(keyword in cleaned_query for keyword in ["皮帶", "皮件", "belt"]):
        name_filter_keywords.extend(["皮帶"])
    if any(keyword in cleaned_query for keyword in ["女包", "包款", "背包", "包包"]):
        name_filter_keywords.extend(["包"])
    if "醬油" in terms or any("醬油" in t for t in raw_category_terms) or (required_terms and any("醬油" in t for t in required_terms)):
        name_filter_keywords.extend(["醬油", "蔭油"])
    if name_filter_keywords:
        pattern = "|".join(re.escape(keyword) for keyword in name_filter_keywords)
        name_series = filtered.get("Name")
        if name_series is not None:
            filtered = filtered[name_series.astype(str).str.contains(pattern, na=False)]
            if filtered.empty:
                return [], terms
    # sort by score first
    sorted_df = filtered.sort_values("__score__", ascending=False)
    id_column = "GoodIden" if "GoodIden" in sorted_df.columns else "Name"
    if category_group_synonyms:
        def _row_synonym_hits(row_series, synonyms: List[str]) -> Tuple[int, int]:
            row_dict = row_series.to_dict()
            name_text = str(row_dict.get("Name", "")).lower()
            full_text = _row_text(row_dict)
            hits_name = sum(1 for term in synonyms if term in name_text)
            hits_total = sum(1 for term in synonyms if term in full_text)
            return hits_name, hits_total

        final_df = sorted_df.copy()
        for base, synonyms in category_group_synonyms.items():
            if final_df.apply(lambda row: _row_synonym_hits(row, synonyms)[0] > 0, axis=1).any():
                continue
            group_df = category_group_candidates.get(base)
            if group_df is None or group_df.empty:
                continue
            group_df = group_df.copy()
            if "__score__" not in group_df.columns:
                group_df["__score__"] = [score_row(r, terms) for r in group_df.to_dict(orient="records")]
            metrics = group_df.apply(lambda row: pd.Series({
                "__synonym_hits_name__": _row_synonym_hits(row, synonyms)[0],
                "__synonym_hits__": _row_synonym_hits(row, synonyms)[1],
            }), axis=1)
            group_df = pd.concat([group_df, metrics], axis=1)
            group_df = group_df.sort_values([
                "__synonym_hits_name__",
                "__synonym_hits__",
                "__score__"
            ], ascending=[False, False, False])
            candidate = group_df.iloc[:1]
            final_df = pd.concat([final_df, candidate])
            final_df = final_df.drop_duplicates(subset=[id_column], keep="first")
        sorted_df = final_df.sort_values("__score__", ascending=False)
    if sort_price and "SpecialOffer" in sorted_df.columns:
        sorted_df["__price_sort__"] = pd.to_numeric(
            sorted_df["SpecialOffer"].replace("", pd.NA), errors="coerce"
        )
        sorted_df["__price_sort__"] = sorted_df["__price_sort__"].fillna(
            pd.to_numeric(sorted_df.get("Price"), errors="coerce")
        )
        sorted_df = sorted_df.sort_values(["__price_sort__", "__score__"], ascending=[True, False])
    elif sort_price and "Price" in sorted_df.columns:
        sorted_df["__price_sort__"] = pd.to_numeric(sorted_df["Price"], errors="coerce")
        sorted_df = sorted_df.sort_values(["__price_sort__", "__score__"], ascending=[True, False])
    if topn and topn > 0:
        sorted_df = sorted_df.head(topn)
    return sorted_df.drop(columns=["__price_sort__"], errors="ignore").to_dict(orient="records"), terms

def format_for_chat(records: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in records:
        desc = (
            r.get("ShortDesc_20")
            or r.get("ShortDesc")
            or r.get("ShortDesc_10")
            or r.get("DESCRIPTION")
            or r.get("Description")
            or r.get("REMARK")
            or r.get("備註")
            or ""
        )
        out.append({
            "商品編號": r.get("GoodIden",""),
            "商品名稱": r.get("Name",""),
            "商品描述": desc,
            "商品價格": r.get("Price_fmt") or r.get("Price",""),
            "商品特價": r.get("SpecialOffer_fmt") or r.get("SpecialOffer",""),
            "商品購物網址": r.get("Goods_Link1",""),
            "商品圖片網址": r.get("Goodspic_Link1",""),
        })
    return out


def polite_fallback(query: str) -> str:
    q = (query or "").strip()
    return (
        "很抱歉，目前沒有找到符合您需求的商品喔 🙏\n"
        "您可以嘗試其他關鍵字，或告訴我品牌、型號或預算範圍，"
        "我再幫您推薦合適的商品 💡\n"
        f"（目前查詢關鍵字：{q}）"
    )
def _parse_numeric_filters(query: str) -> Dict[str, List[Tuple[Optional[float], Optional[float]]]]:
    """Parse simple numeric filters like '價格 100~200' or '價格<=300' (supports 中文 or 英文)."""
    normalized = _normalize_query_text(query or "")
    q = _norm(normalized)
    if not q:
        return {}
    filters: Dict[str, List[Tuple[Optional[float], Optional[float]]]] = {}

    def add_filter(field: str, low: Optional[float], high: Optional[float]):
        filters.setdefault(field, []).append((low, high))

    def to_float(val: str) -> Optional[float]:
        try:
            return float(val)
        except Exception:
            return None

    for field, aliases in NUMERIC_FIELD_ALIASES.items():
        for alias in aliases:
            pattern = re.compile(
                rf"{alias}\s*(?:(\d+(?:\.\d+)?)\s*[-~～至]\s*(\d+(?:\.\d+)?))"
            )
            for match in pattern.finditer(q):
                low = to_float(match.group(1))
                high = to_float(match.group(2))
                if low is not None or high is not None:
                    add_filter(field, low, high)

            # comparisons e.g. 價格<=200 or price >= 150
            pattern_cmp = re.compile(
                rf"{alias}\s*(<=|>=|<|>|到)\s*(\d+(?:\.\d+)?)"
            )
            for match in pattern_cmp.finditer(q):
                op = match.group(1)
                value = to_float(match.group(2))
                if value is None:
                    continue
                if op == "<=":
                    add_filter(field, None, value)
                elif op == "<":
                    add_filter(field, None, value - 1e-6)
                elif op == ">=":
                    add_filter(field, value, None)
                elif op == ">":
                    add_filter(field, value + 1e-6, None)
                elif op == "到":
                    add_filter(field, None, value)

    # direct patterns like "價格 100 200"
    for field, aliases in NUMERIC_FIELD_ALIASES.items():
        for alias in aliases:
            pattern = re.compile(
                rf"{alias}\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)"
            )
            for match in pattern.finditer(q):
                low = to_float(match.group(1))
                high = to_float(match.group(2))
                if low is not None or high is not None:
                    add_filter(field, low, high)

    return filters


def _apply_numeric_filters(df: pd.DataFrame, filters: Dict[str, List[Tuple[Optional[float], Optional[float]]]]) -> pd.DataFrame:
    if not filters:
        return df
    working = df
    for field, ranges in filters.items():
        col = field
        if col not in working.columns:
            continue
        series = pd.to_numeric(working[col], errors="coerce")
        mask = pd.Series(False, index=working.index)
        for low, high in ranges:
            cond = pd.Series(True, index=working.index)
            if low is not None:
                cond &= series >= low
            if high is not None:
                cond &= series <= high
            mask |= cond
        working = working[mask]
        if working.empty:
            break
    return working
DEFAULT_FALLBACK_CATEGORIES: Tuple[str, ...] = ("皮帶", "鞋", "包")


def load_goods_rows(refresh: bool = False) -> List[Dict[str, Any]]:
    """Return cached goods rows as list of dicts, loading from CSV on first use."""
    global _GOODS_ROWS_CACHE
    if refresh or _GOODS_ROWS_CACHE is None:
        try:
            df = load_data(str(DEFAULT_DATA_PATH))
        except Exception:
            df = pd.DataFrame()
        _GOODS_ROWS_CACHE = df.to_dict(orient="records") if not df.empty else []
    return _GOODS_ROWS_CACHE or []


# === Chat mode support: catalog snapshot ======================================
def get_catalog_snapshot(limit: int = 200) -> List[Dict[str, Any]]:
    """
    回傳精簡商品清單供聊天系統提示詞使用，避免把整份 CSV 塞進 prompt。
    格式：[{ "good_id": str, "name": str, "price": 任意, "special": 任意, "category": str }]
    """
    rows = load_goods_rows()
    if limit is None or limit <= 0:
        sliced = rows
    else:
        sliced = rows[:limit]
    snapshot: List[Dict[str, Any]] = []
    for r in sliced:
        snapshot.append({
            "good_id": str(r.get("GoodIden") or r.get("商品編號") or ""),
            "name": str(r.get("Name") or r.get("商品名稱") or "").strip(),
            "price": r.get("Price") or r.get("價格"),
            "special": r.get("SpecialOffer") or r.get("特價"),
            "category": str(r.get("CateName") or r.get("分類名稱") or "").strip(),
        })
    return snapshot


# [CHAT→QUERY] fetch items by GoodIden list
def get_items_by_ids(df: pd.DataFrame, id_list: List[Any], id_col: str = "GoodIden") -> List[Dict[str, Any]]:
    if not id_list or df is None or df.empty:
        return []
    id_set = {str(x).strip() for x in id_list if str(x or "").strip()}
    if not id_set:
        return []
    if id_col not in df.columns:
        return []
    filtered = df[df[id_col].astype(str).isin(id_set)]
    if filtered.empty:
        return []
    return filtered.to_dict(orient="records")


def find_product_by_name(df: pd.DataFrame, raw_name: str, limit: int = 1) -> List[Dict[str, Any]]:
    if df is None or df.empty or not raw_name:
        return []
    name = str(raw_name or "").strip().lower()
    if not name:
        return []
    candidates = df.copy()
    candidates["__name_lc"] = candidates.get("Name", candidates.get("name")).astype(str).str.lower()
    col_list = ["Name", "name", "商品名稱"]
    mask = pd.Series(False, index=candidates.index)
    for col in col_list:
        if col in candidates.columns:
            mask = mask | candidates[col].astype(str).str.lower().str.contains(re.escape(name), na=False)
    filtered = candidates[mask]
    if filtered.empty:
        name_series = candidates["__name_lc"].tolist()
        matches = get_close_matches(name, name_series, n=max(limit, 5), cutoff=0.4)
        if matches:
            mask = candidates["__name_lc"].isin(matches)
            filtered = candidates[mask]
    if filtered.empty:
        return []
    return filtered.head(limit).drop(columns=["__name_lc"], errors="ignore").to_dict(orient="records")
# ========== SUGGESTION HELPERS ==============================================


def _normalize(s):
    return str(s or "").strip().lower()


def suggest_original_ids(last_align_ids: List[str], limit: Optional[int] = None) -> List[str]:
    ids = [str(x).strip() for x in (last_align_ids or []) if str(x).strip()]
    if ids:
        if limit is None or limit <= 0:
            return ids
        return ids[:limit]

    birthday_party_suggestions = [
        "4713837032316",
        "4713837030497",
        "4713837032002",
        "4713837031999",
        "4711202224557",
        "4711202224038",
        "4711202224045",
        "4711202221693",
        "4714379952018",
        "4713517167611",
        "4710940006722",
        "4710940006715",
    ]
    if limit is None or limit <= 0:
        return birthday_party_suggestions
    return birthday_party_suggestions[:limit]


def _is_on_sale(row: dict) -> bool:
    special = str(row.get("SpecialOffer") or row.get("特價") or "").strip()
    if special:
        return True
    try:
        price = float(row.get("pric") or row.get("Price") or row.get("價格") or 0)
        special_price = float(row.get("pric_special") or row.get("SpecialOffer") or 0)
        if special_price and price and special_price < price:
            return True
    except Exception:
        return False
    return False


def suggest_on_sale_related(df: pd.DataFrame, last_query_terms: List[str], limit: int = 8) -> List[str]:
    if df is None or df.empty:
        return []
    working = df.copy()
    working["__on_sale"] = working.apply(_is_on_sale, axis=1)
    working = working[working["__on_sale"] == True]
    if working.empty:
        return []

    patterns = [re.escape(_normalize(term)) for term in (last_query_terms or []) if _normalize(term)]
    if patterns:
        pat = "|".join(patterns)
        mask = (
            working.get("Name", working.get("name")).astype(str).str.lower().str.contains(pat, regex=True, na=False) |
            working.get("CateName", working.get("category")).astype(str).str.lower().str.contains(pat, regex=True, na=False) |
            working.get("DESCRIPTION", working.get("Description")).astype(str).str.lower().str.contains(pat, regex=True, na=False)
        )
        filtered = working[mask]
    else:
        filtered = working
    if filtered.empty:
        return []
    return filtered.head(limit)["GoodIden"].astype(str).str.strip().tolist()


def suggest_complementary(df: pd.DataFrame, last_align_rows: List[Dict[str, Any]], limit: int = 8) -> List[str]:
    if df is None or df.empty:
        return []
    COMPLEMENT_MAP = {
        "醬油": ["麵", "米", "醬菜", "罐頭"],
        "醬菜": ["粥", "米", "麵"],
        "沐浴": ["牙膏", "牙刷", "漱口"],
        "口腔": ["牙膏", "牙刷", "漱口"],
        "堅果": ["茶", "咖啡"],
        "零食": ["茶", "咖啡"],
        "穀物": ["牛奶", "豆漿"],
        "燕麥": ["牛奶", "豆漿"],
    }

    cats = set()
    keywords = set()
    for row in last_align_rows or []:
        cats.add(_normalize(row.get("CateName") or row.get("category")))
        name_text = _normalize(row.get("Name") or row.get("name"))
        for token in re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]+", name_text):
            if token:
                keywords.add(token)

    desired = set()
    for source_cat in cats:
        for key, targets in COMPLEMENT_MAP.items():
            if key and key in source_cat:
                desired.update([_normalize(t) for t in targets])

    if not desired and keywords:
        desired.update(list(keywords)[:3])

    working = df.copy()
    if desired:
        pat = "|".join(map(re.escape, desired))
        mask = (
            working.get("Name", working.get("name")).astype(str).str.lower().str.contains(pat, regex=True, na=False) |
            working.get("CateName", working.get("category")).astype(str).str.lower().str.contains(pat, regex=True, na=False)
        )
        working = working[mask]
    if working.empty:
        return []
    return working.head(limit)["GoodIden"].astype(str).str.strip().tolist()
