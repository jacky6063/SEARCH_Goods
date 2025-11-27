# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Optional
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modes.marketing_consultant import (  # noqa: E402
    prepare_information_response,
    _clear_event_state,
)


def _dummy_fetch(_: Optional[List[Dict[str, Any]]], __: List[str]) -> List[Dict[str, Any]]:
    return []


@pytest.fixture(autouse=True)
def cleanup_event_state():
    # 每個測試前後清理既有 session 狀態
    yield
    _clear_event_state("test-session")


def test_event_flow_preference_followup():
    session_id = "test-session"
    base_llm_result = {
        "intent": "event_food_planning",
        "reply": "",
        "meta": {},
    }

    # 第一輪：取得偏好追問
    resp, suggestion_ids, payload = prepare_information_response(
        base_llm_result,
        "我要幫 20 人辦生日派對，預算 15000，需要鹹食甜點和飲料的推薦",
        {},
        _dummy_fetch,
        session_id=session_id,
    )

    assert suggestion_ids == []
    assert payload is None
    assert "即食型派對" in resp["reply"]
    assert resp["meta"]["pending_preferences"] == ["heat_option", "beverage_style"]

    # 第二輪：使用者回覆 B，仍應追問飲品偏好
    resp2, _, payload2 = prepare_information_response(
        base_llm_result,
        "B",
        {},
        _dummy_fetch,
        session_id=session_id,
    )

    assert payload2 is None
    assert resp2["meta"]["pending_preferences"] == ["beverage_style"]
    assert "豆奶" in resp2["reply"]
