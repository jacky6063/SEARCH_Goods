# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from llm_service import _detect_conversation_intent  # type: ignore
from planner.event_food_planner import parse_event_context


def test_detect_event_intent():
    query = "我們下週要辦親子園遊會，要準備一些攤位點心，請給建議"
    assert _detect_conversation_intent(query) == "event_food_planning"


def test_parse_event_context():
    context = parse_event_context("50人親子園遊會，預算30000元，想準備健康一些的餐點")
    assert context.people_count == 50
    assert context.budget_total == 30000
    assert context.activity_type is not None
    assert context.audience == "親子"
