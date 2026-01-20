#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from backend.llm_service import _call_chat, _get_client


GLOBAL_FIELDS = [
    "顏色",
    "材質",
    "尺寸",
    "功能",
    "容量",
    "款式",
    "口味",
    "風味",
    "產地",
    "規格",
    "成分",
    "重量",
]

FALLBACK_FIELDS = {
    "時尚女性": ["顏色", "材質", "尺寸", "功能", "容量", "款式"],
    "常溫食品": ["口味", "風味", "產地", "規格", "成分", "重量"],
}


def detect_l1_column(df: pd.DataFrame) -> Optional[str]:
    for col in ("CateName_L1", "大分類名稱", "CateName", "分類名稱"):
        if col in df.columns:
            return col
    return None


def build_text(row: pd.Series) -> str:
    fields = [
        row.get("Name"),
        row.get("商品名稱"),
        row.get("DESCRIPTION"),
        row.get("Description"),
        row.get("ShortDesc"),
        row.get("ShortDesc_20"),
        row.get("REMARK"),
        row.get("備註"),
        row.get("CateName"),
        row.get("分類名稱"),
    ]
    text = " ".join(str(x) for x in fields if x)
    return text.strip()


def sample_texts(df: pd.DataFrame, l1_value: str, sample_size: int) -> List[str]:
    l1_col = detect_l1_column(df)
    if not l1_col:
        return []
    subset = df[df[l1_col].astype(str) == l1_value]
    if subset.empty:
        return []
    size = min(sample_size, len(subset))
    try:
        sampled = subset.sample(n=size, random_state=1)
    except Exception:
        sampled = subset.head(size)
    texts = []
    for _, row in sampled.iterrows():
        text = build_text(row)
        if text:
            texts.append(text[:300])
    return texts


def fallback_for_l1(l1_value: str) -> List[str]:
    for key, fields in FALLBACK_FIELDS.items():
        if key in l1_value:
            return fields
    return GLOBAL_FIELDS


def build_prompt(l1_value: str) -> str:
    return (
        "你是商品條件白名單生成器。"
        "請從候選欄位中挑選適合此大分類的條件欄位。"
        "輸出 JSON 陣列（例如：[\"顏色\",\"材質\"]）。"
        f"大分類：{l1_value}。候選欄位：{', '.join(GLOBAL_FIELDS)}。"
    )


def call_llm_for_l1(l1_value: str, texts: List[str], model: Optional[str]) -> List[str]:
    client = _get_client()
    if not client:
        return fallback_for_l1(l1_value)
    prompt = build_prompt(l1_value)
    body = "\n".join(f"- {t}" for t in texts[:60])
    reply = _call_chat(body, system=prompt, max_tokens=200, model=model)
    if not reply:
        return fallback_for_l1(l1_value)
    try:
        raw = reply.strip()
        if not raw.startswith("["):
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1:
                raw = raw[start : end + 1]
        parsed = json.loads(raw)
    except Exception:
        return fallback_for_l1(l1_value)
    if not isinstance(parsed, list):
        return fallback_for_l1(l1_value)
    cleaned = [str(x).strip() for x in parsed if str(x).strip()]
    if not cleaned:
        return fallback_for_l1(l1_value)
    allowed = set(GLOBAL_FIELDS)
    return [x for x in cleaned if x in allowed]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate filter whitelist by L1 category.")
    parser.add_argument("--data", default=os.getenv("DATA_PATH") or "data/VIEW_GOODS_enhanced.csv")
    parser.add_argument("--out", default="data/filter_whitelist.json")
    parser.add_argument("--sample", type=int, default=80)
    parser.add_argument("--model", default=os.getenv("CHAT_OPENAI_MODEL"))
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        raise SystemExit(f"data not found: {data_path}")

    df = pd.read_csv(data_path, dtype=str, encoding="utf-8-sig")
    l1_col = detect_l1_column(df)
    if not l1_col:
        raise SystemExit("L1 column not found in CSV")

    whitelist: Dict[str, List[str]] = {}
    for l1_value in sorted(set(df[l1_col].astype(str).fillna("").str.strip())):
        if not l1_value:
            continue
        texts = sample_texts(df, l1_value, args.sample)
        if not texts:
            whitelist[l1_value] = fallback_for_l1(l1_value)
            continue
        whitelist[l1_value] = call_llm_for_l1(l1_value, texts, args.model)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(whitelist, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
