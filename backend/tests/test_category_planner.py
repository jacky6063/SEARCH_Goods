# -*- coding: utf-8 -*-
"""
通用情境規劃器測試
"""
from __future__ import annotations

import pandas as pd

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from planner import detect_intent, build_plan


def _build_sample_catalog() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"GoodIden": "B001", "Name": "巧克力餅乾", "CateName": "餅乾類", "Price": "120"},
            {"GoodIden": "B002", "Name": "杏仁餅乾", "CateName": "餅乾類", "Price": "150"},
            {"GoodIden": "D001", "Name": "綠茶飲料", "CateName": "飲料類", "Price": "80"},
            {"GoodIden": "D002", "Name": "柳橙果汁", "CateName": "飲料類", "Price": "90"},
            {"GoodIden": "K001", "Name": "不鏽鋼平底鍋", "CateName": "廚房用品", "Price": "650"},
            {"GoodIden": "H001", "Name": "綜合維他命", "CateName": "健康保健", "Price": "520"},
        ]
    )


def test_detect_intent_with_multiple_categories():
    intent = detect_intent("我要辦生日派對，準備餅乾和飲料，預算 1000 元，越快越好！")
    assert "餅乾類" in intent.categories
    assert "飲料類" in intent.categories
    assert intent.budget == 1000
    assert intent.urgency is True
    assert intent.confidence > 0


def test_build_plan_allocates_budget_across_categories():
    catalog = _build_sample_catalog()
    intent = detect_intent("幫我準備餅乾跟飲料，預算 500 元")
    result = build_plan(intent, catalog, max_items_per_category=2)

    assert result.plans, "planner 應該至少產出一個品類方案"
    categories = {plan.category for plan in result.plans}
    assert {"餅乾類", "飲料類"}.issubset(categories)
    assert result.total_budget == 500
    assert result.total_cost <= 500
    assert result.notes["detected_categories"]


def test_build_plan_handles_single_category_without_budget():
    catalog = _build_sample_catalog()
    intent = detect_intent("需要健康保健類的產品")
    result = build_plan(intent, catalog)

    assert len(result.plans) == 1
    assert result.plans[0].category == "健康保健"
    assert result.plans[0].picked_items  # 至少有一個商品
