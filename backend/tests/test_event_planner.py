# -*- coding: utf-8 -*-
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from planner.event_food_planner import (
    EventContext,
    generate_event_plan,
    parse_event_context,
)


def _mock_df():
    data = [
        {
            "CateName": "餅乾類",
            "GoodIden": "B001",
            "Name": "親子星星餅乾",
            "Price": "120",
            "SpecialOffer": "",
            "DESCRIPTION": "可愛星星造型，小朋友最愛。",
            "Goods_Link1": "https://example.com/B001",
            "Goodspic_Link1": "https://example.com/B001.jpg",
        },
        {
            "CateName": "飲料類",
            "GoodIden": "D001",
            "Name": "沁涼水果茶飲",
            "Price": "80",
            "SpecialOffer": "65",
            "DESCRIPTION": "清爽解暑，戶外活動必備。",
            "Goods_Link1": "https://example.com/D001",
            "Goodspic_Link1": "https://example.com/D001.jpg",
        },
        {
            "CateName": "零食",
            "GoodIden": "S001",
            "Name": "脆口米果",
            "Price": "90",
            "SpecialOffer": "",
            "DESCRIPTION": "不沾手的小點心，適合邊走邊吃。",
            "Goods_Link1": "https://example.com/S001",
            "Goodspic_Link1": "https://example.com/S001.jpg",
        },
    ]
    return pd.DataFrame(data)


def test_generate_event_plan_basic():
    context = EventContext(
        activity_type="園遊會",
        people_count=50,
        budget_total=30000,
        audience="親子",
    )
    plan = generate_event_plan(context, _mock_df())
    assert plan is not None
    assert len(plan["items"]) >= 1
    assert plan["total_cost"] > 0


def test_parse_event_context_budget_without_unit():
    text = "我要幫 20 人辦生日派對，預算 15000，需要鹹食甜點和飲料的推薦"
    context = parse_event_context(text)
    assert context.people_count == 20
    assert context.budget_total == 15000
    assert context.activity_type is not None
