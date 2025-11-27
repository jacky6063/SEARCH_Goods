import datetime
from typing import Dict, List
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
for path in (PROJECT_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import importlib

backend_chat_logging = importlib.import_module("backend.chat_logging")
backend_supabase_client = importlib.import_module("backend.supabase_client")
backend_chat_logging_bridge = importlib.import_module("backend.chat_logging_bridge")

sys.modules.setdefault("chat_logging", backend_chat_logging)
sys.modules.setdefault("supabase_client", backend_supabase_client)
sys.modules.setdefault("chat_logging_bridge", backend_chat_logging_bridge)

from chat_logging import ChatLoggingError  # type: ignore  # noqa: E402
from chat_logging_bridge import ChatLoggingBridge  # type: ignore  # noqa: E402


@pytest.fixture(autouse=True)
def no_session_event(monkeypatch):
    monkeypatch.setattr(
        "chat_logging_bridge.supabase_log_session_event",
        lambda **_: None,
    )


def test_ensure_session_caches_and_logs_once(monkeypatch):
    calls: List[Dict] = []

    def fake_start_session(**kwargs):
        calls.append(kwargs)
        return {"session_id": "sup-123"}

    monkeypatch.setattr("chat_logging_bridge.supabase_start_session", fake_start_session)

    bridge = ChatLoggingBridge("goods", "chat_api")

    session_id = bridge.ensure_session("ui-1", metadata={"foo": "bar"})
    assert session_id == "sup-123"
    assert calls == [
        {
            "module_type": "goods",
            "channel": "chat_api",
            "metadata": {"foo": "bar"},
        }
    ]

    # Calling again with相同 UI session，不會再呼叫 start_session
    session_id_2 = bridge.ensure_session("ui-1")
    assert session_id_2 == "sup-123"
    assert len(calls) == 1


def test_log_user_message_handles_supabase_errors(monkeypatch):
    bridge = ChatLoggingBridge("goods", "chat_api")
    bridge.bind_ui_session("ui-err", "sup-err")

    def fake_append(**kwargs):
        raise ChatLoggingError("boom")

    monkeypatch.setattr("chat_logging_bridge.supabase_append_message", fake_append)

    result = bridge.log_user_message("ui-err", "hello", {"k": "v"})
    # 仍返回 session id，但不會拋出例外
    assert result == "sup-err"


def test_log_assistant_message_snapshot(monkeypatch):
    bridge = ChatLoggingBridge("goods", "chat_api")
    bridge.bind_ui_session("ui-assistant", "sup-assistant")

    captured: Dict = {}

    def fake_append(**kwargs):
        captured.update(kwargs)
        return {"message_id": 99, "session_id": kwargs["session_id"]}

    monkeypatch.setattr("chat_logging_bridge.supabase_append_message", fake_append)

    payload = {
        "meta": {"intent": "company_info"},
        "action": {"type": "display"},
        "items": [{"id": "a"}, {"id": "b"}],
        "display_mode": "rich",
    }

    record = bridge.log_assistant_message(
        "ui-assistant",
        "reply text",
        payload,
        created_at=datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc),
    )
    assert record == {"message_id": 99, "session_id": "sup-assistant"}
    assert captured["session_id"] == "sup-assistant"
    assert captured["role"] == "llm"
    assert captured["payload"]["items_count"] == 2
