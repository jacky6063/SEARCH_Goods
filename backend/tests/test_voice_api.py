import asyncio
import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app
from voice_service import (
    VoiceServiceError,
    build_intent_reject_payload,
    build_voice_directives,
    is_intent_allowed,
)


def test_voice_intent_whitelist():
    assert is_intent_allowed("goods_search")
    assert is_intent_allowed("company_profile")
    assert not is_intent_allowed("random")
    assert not is_intent_allowed("")


def test_voice_directives_toggle():
    results = [
        {"商品名稱": "測試包款", "售價": "NT$1200"},
        {"商品名稱": "測試鞋款", "售價": "NT$2200"},
    ]
    payload = build_voice_directives(results, "goods_search", total_count=5)
    assert payload["voice_session_end"] is True
    assert payload["voice_mode_active"] is False
    assert "測試包款" in payload["voice_summary"]
    assert "5 件" in payload["voice_summary"] or "5 件商品" in payload["voice_summary"]


def test_voice_directives_when_no_results_keeps_session_active():
    payload = build_voice_directives([], "goods_search", total_count=0)
    assert payload["voice_mode_active"] is True
    assert payload["voice_session_end"] is False
    assert "找不到" in payload["voice_summary"] or "暫時" in payload["voice_summary"]


def test_voice_reject_payload():
    payload = build_intent_reject_payload()
    assert payload["voice_session_end"] is True
    assert payload["voice_mode_active"] is False
    assert "語音模式" in payload["voice_summary"]
    assert payload["reply"] == payload["voice_summary"]


def test_transcribe_audio_success(monkeypatch):
    import voice_service

    class _DummyClient:
        class audio:
            class transcriptions:
                @staticmethod
                def create(**kwargs):
                    return type("Resp", (), {"text": "測試語音", "language": "zh"})

    monkeypatch.setattr(voice_service, "_get_openai_client", lambda: _DummyClient())

    result = asyncio.run(voice_service.transcribe_audio(b"binary-data"))
    assert result["text"] == "測試語音"
    assert result["language"] == "zh"


def test_transcribe_audio_error(monkeypatch):
    import voice_service

    class _DummyFail:
        class audio:
            class transcriptions:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("boom")

    monkeypatch.setattr(voice_service, "_get_openai_client", lambda: _DummyFail())

    with pytest.raises(VoiceServiceError):
        asyncio.run(voice_service.transcribe_audio(b"bytes"))


def _voice_test_client(monkeypatch, voice_enabled=True):
    def _load_branding():
        return {"voice_mode_enabled": voice_enabled}

    monkeypatch.setattr(app.config_store, "load_branding_config", _load_branding)
    return TestClient(app.app)


def test_voice_transcribe_requires_voice_mode(monkeypatch, tmp_path):
    client = _voice_test_client(monkeypatch, voice_enabled=False)
    resp = client.post(
        "/api/voice/transcribe",
        files={"audio": ("sample.webm", b"123", "audio/webm")},
    )
    assert resp.status_code == 403


def test_voice_transcribe_success(monkeypatch):
    async def _fake_transcribe(data):
        return {"text": "嗨", "language": "zh", "confidence": 1.0}

    import voice_service

    async def _fake_reader(upload):
        return b"abc"

    monkeypatch.setattr(app.config_store, "load_branding_config", lambda: {"voice_mode_enabled": True})
    monkeypatch.setattr(app, "_read_audio_bytes", _fake_reader)
    monkeypatch.setattr(voice_service, "transcribe_audio", _fake_transcribe, raising=False)

    client = TestClient(app.app)
    resp = client.post(
        "/api/voice/transcribe",
        files={"audio": ("sample.webm", b"abc", "audio/webm")},
    )
    assert resp.status_code == 200
    assert resp.json()["text"] == "嗨"


def test_voice_chat_flow(monkeypatch):
    async def _fake_transcribe(_audio):
        return {"text": "我要找包包", "language": "zh"}

    import voice_service

    async def _fake_reader(upload):
        return b"abc"

    monkeypatch.setattr(app.config_store, "load_branding_config", lambda: {"voice_mode_enabled": True})
    monkeypatch.setattr(app, "_read_audio_bytes", _fake_reader)
    monkeypatch.setattr(voice_service, "transcribe_audio", _fake_transcribe, raising=False)

    def _fake_chat_endpoint(req):
        assert req.voice_mode is True
        return app.ChatResp(reply="為您找到 1 件商品", suggestion_ids=["1"], voice_summary="summary", voice_session_end=True)

    monkeypatch.setattr(app, "chat_endpoint", _fake_chat_endpoint)

    client = TestClient(app.app)
    resp = client.post(
        "/api/voice/chat",
        data={"session_id": "s1"},
        files={"audio": ("sample.webm", b"abc", "audio/webm")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["recognized_text"] == "我要找包包"
    assert data["voice_summary"] == "summary"
