import math
import sys
from pathlib import Path


def _find_repo_root(marker: str = "backend") -> Path:
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / marker).exists():
            return parent
    return current  # fallback for unusual layouts


ROOT = _find_repo_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND_DIR = ROOT / "backend"
if BACKEND_DIR.exists() and str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.goods_search_service import _parse_numeric_filters


def _price_filters(query):
    return _parse_numeric_filters(query).get("Price") or []


def test_parse_bare_chinese_greater_than():
    filters = _price_filters("想找3000元以上的包包")
    assert filters, "應該解析出價格下限"
    low, high = filters[0]
    assert math.isclose(low or 0, 3000)
    assert high is None


def test_parse_bare_chinese_less_than():
    filters = _price_filters("我想找3000以下的耳機")
    assert filters
    low, high = filters[0]
    assert low is None
    assert math.isclose(high or 0, 3000)


def test_parse_bare_range_without_alias():
    filters = _price_filters("3000到5000元的女包")
    assert filters
    low, high = filters[0]
    assert math.isclose(low or 0, 3000)
    assert math.isclose(high or 0, 5000)


def test_parse_alias_with_natural_language_comparator():
    filters = _price_filters("價格 4000 以內的商品")
    assert filters
    low, high = filters[0]
    assert low is None
    assert math.isclose(high or 0, 4000)


def test_parse_budget_alias():
    filters = _price_filters("預算5000以內的咖啡機")
    assert filters
    low, high = filters[0]
    assert low is None
    assert math.isclose(high or 0, 5000)
