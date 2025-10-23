import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goods_search_service import load_data, search_products, format_for_chat, polite_fallback


def test_load_data_and_search(tmp_path):
    # use existing sample CSV
    csv = ROOT.parent / "data" / "VIEW_GOODS_enhanced.csv"
    df = load_data(str(csv))
    assert not df.empty
    records, terms = search_products(df, "包 休閒", topn=5)
    assert isinstance(records, list)


def test_format_and_empty():
    data = []
    formatted = format_for_chat(data)
    assert formatted == []
    msg = polite_fallback("iPhone 17")
    assert "iPhone 17" in msg


def test_search_continuous_chinese_phrase():
    csv = ROOT.parent / "data" / "VIEW_GOODS_enhanced.csv"
    df = load_data(str(csv))
    records, terms = search_products(df, "有慈心認證的商品嗎", topn=5)
    # ensure terms include key phrase pieces and records found
    assert records
    assert any("慈心" in t for t in terms)
    assert any("慈心" in (str(r.get("DESCRIPTION")) + str(r.get("REMARK", ""))) for r in records)
