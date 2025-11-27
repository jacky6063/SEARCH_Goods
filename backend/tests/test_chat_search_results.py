"""
聊天搜尋行為相關測試
"""
import os
import sys
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
DATA_PATH = ROOT / "data" / "VIEW_GOODS_enhanced.csv"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DATA_PATH", str(DATA_PATH))

import llm_service  # noqa: E402
from modes.shopping_recommender import prepare_shopping_response  # noqa: E402
from services import catalog_service  # noqa: E402


def _reload_llm_service():
    return importlib.reload(llm_service)


def test_prepare_chat_context_returns_multiple_results():
    """確保包包價格查詢可以取得候選商品"""
    _reload_llm_service()
    query = "我要購買女用包包價格在 3000~4000元之間"
    # 使用真實 catalog 而不是空列表
    df = llm_service._get_chat_df()
    catalog = df.to_dict(orient="records") if df is not None and not df.empty else []
    context = llm_service._prepare_chat_context(query, catalog)
    # 至少應返回一些候選商品或結構化過濾信息
    assert len(context["products"]) > 0 or context.get("structured_filters")
    filters = context.get("structured_filters") or {}
    price_filter = filters.get("price_filter") or {}
    assert price_filter.get("min_price") == 3000.0
    assert price_filter.get("max_price") == 4000.0


def test_prepare_shopping_response_fallback_builds_payload(monkeypatch):
    """當預取資料缺失時，應回退至商品資料集產生 JSON"""
    _reload_llm_service()

    suggestion_ids = ["V87407K-3138", "V81307G-0106"]
    llm_result = {
        "reply": "mock reply",
        "alignment": {
            "intent": "product_align",
            "items": [{"id": sid, "name": ""} for sid in suggestion_ids],
        },
        "meta": {},
        "intent": "product_search",  # 確保觸發 product_search 模式
    }

    # Mock 商品資料以模擬 fallback 情境
    mock_goods_data = [
        {"GoodIden": "V87407K-3138", "NAME": "測試商品1", "PRICE": 3500},
        {"GoodIden": "V81307G-0106", "NAME": "測試商品2", "PRICE": 3800},
    ]

    def fake_fetch(prefetched, ids):
        # 第一次調用返回空，觸發 fallback
        return []

    def fake_compose(items, include_suffix=True, user_query=""):
        structured = {
            "summary": f"{len(items)} 款商品",
            "items": [
                {
                    "index": idx + 1,
                    "商品編號": str(item.get("GoodIden") or item.get("商品編號") or ""),
                }
                for idx, item in enumerate(items)
            ],
        }
        return "formatted reply", structured

    def fake_invoke(intent):
        return None

    def fake_merge(base_reply, planner_payload, suggestions):
        return base_reply

    # Mock load_goods_rows 以提供 fallback 數據
    import goods_search_service
    original_load = goods_search_service.load_goods_rows
    
    def mock_load_goods_rows():
        return mock_goods_data
    
    monkeypatch.setattr(goods_search_service, "load_goods_rows", mock_load_goods_rows)

    resp, ids, payload = prepare_shopping_response(
        llm_result=llm_result,
        user_text="我要購買女用包包價格在 3000~4000元之間",
        structured_filters={},
        planner_intent=None,
        party_context=False,
        has_budget_intent=lambda _: False,
        fetch_items_for_reply=fake_fetch,
        compose_structured_reply=fake_compose,
        invoke_category_planner=fake_invoke,
        merge_planner_reply=fake_merge,
    )

    assert ids == suggestion_ids
    assert payload is not None, "Fallback 應該產生 structured_payload"
    assert resp["structured_payload"]["items"]
    assert resp["reply"] == "formatted reply"


def test_prepare_chat_context_includes_category_hierarchy(monkeypatch):
    """當 LLM 辨識分類時，structured_filters 應帶入 category_hierarchy，方便後續商品過濾。"""
    _reload_llm_service()

    fake_hierarchy = {"L1": "常溫食品", "L2": "廚房清潔", "L3": "洗碗精"}

    def fake_llm_analyze_query(query, use_search_config=False):
        return {
            "category_hierarchy": fake_hierarchy.copy(),
            "intent": "product_search",
        }

    monkeypatch.setattr(llm_service, "llm_analyze_query", fake_llm_analyze_query)

    context = llm_service._prepare_chat_context("我要買廚房洗滌清潔用品", [])
    filters = context.get("structured_filters") or {}
    assert filters.get("category_hierarchy") == fake_hierarchy


def test_prepare_shopping_response_filters_mismatched_category(monkeypatch):
    """建議商品若與分類不符，應在前端展示前被排除。"""
    _reload_llm_service()

    suggestion_ids = ["CLEAN-001", "BAG-001"]
    llm_result = {
        "reply": "mock reply",
        "alignment": {
            "intent": "product_align",
            "items": [{"id": sid, "name": ""} for sid in suggestion_ids],
        },
        "meta": {},
        "intent": "product_search",
    }

    catalog_rows = [
        {
            "GoodIden": "CLEAN-001",
            "大分類名稱": "常溫食品",
            "中分類名稱": "廚房清潔",
            "小分類名稱": "洗碗精",
            "NAME": "洗碗精",
        },
        {
            "GoodIden": "BAG-001",
            "大分類名稱": "時尚女性",
            "中分類名稱": "女用皮包",
            "小分類名稱": "後背包",
            "NAME": "後背包",
        },
    ]

    monkeypatch.setattr(
        catalog_service,
        "get_items_by_ids",
        lambda ids: [row for row in catalog_rows if row["GoodIden"] in ids],
    )

    def fake_fetch(prefetched, ids):
        return [row for row in catalog_rows if row["GoodIden"] in ids]

    def fake_compose(items, include_suffix=True, user_query=""):
        structured = {
            "summary": f"{len(items)} 款商品",
            "items": [
                {
                    "index": idx + 1,
                    "商品編號": str(item.get("GoodIden") or ""),
                }
                for idx, item in enumerate(items)
            ],
        }
        return "formatted reply", structured

    def fake_invoke(intent):
        return None

    def fake_merge(base_reply, planner_payload, suggestions):
        return base_reply

    structured_filters = {
        "category_hierarchy": {"L1": "常溫食品", "L2": "廚房清潔", "L3": "洗碗精"}
    }

    resp, ids, payload = prepare_shopping_response(
        llm_result=llm_result,
        user_text="我要買廚房洗滌清潔用品",
        structured_filters=structured_filters,
        planner_intent=None,
        party_context=False,
        has_budget_intent=lambda _: False,
        fetch_items_for_reply=fake_fetch,
        compose_structured_reply=fake_compose,
        invoke_category_planner=fake_invoke,
        merge_planner_reply=fake_merge,
    )

    assert ids == ["CLEAN-001"]
    assert resp["suggestion_ids"] == ["CLEAN-001"]
    assert payload is not None


def test_prepare_chat_context_flags_unknown_category_as_oos():
    """未出現在白名單的查詢應被視為 OOS。"""
    _reload_llm_service()
    query = "我要購買福特汽車"
    df = llm_service._get_chat_df()
    catalog = df.to_dict(orient="records") if df is not None and not df.empty else []
    context = llm_service._prepare_chat_context(query, catalog)
    assert context.get("oos_suspected") is True


def test_chat_reply_recovers_after_oos():
    _reload_llm_service()
    resp_oos = llm_service.chat_reply("我要購買自行車", [], [])
    meta = resp_oos.get("meta") or {}
    assert meta.get("oos_category") is True

    history = [
        {"role": "user", "content": "我要購買自行車"},
        {"role": "assistant", "content": resp_oos.get("reply", "")},
    ]
    resp_valid = llm_service.chat_reply("我要購買女用包包價格在 3000~4000元之間", history, [])
    assert not ((resp_valid.get("meta") or {}).get("oos_category"))
