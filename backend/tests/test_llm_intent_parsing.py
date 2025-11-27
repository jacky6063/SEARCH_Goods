import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goods_search_service import _required_phrases


@pytest.mark.llm
def test_required_phrases_contains_walnut():
    groups = _required_phrases("無調味核桃")
    flat = [alias for aliases, _ in groups for alias in aliases]
    assert any("核桃" in alias for alias in flat)
    assert any("無調味" in alias for alias in flat)
