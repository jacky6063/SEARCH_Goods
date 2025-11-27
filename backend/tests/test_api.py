import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app import app


client = TestClient(app)


def test_api_search_success():
    resp = client.post("/api/search", json={"query": "包 休閒", "topn": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data and "items" in data


def test_api_search_empty():
    # Query that likely returns empty
    resp = client.post("/api/search", json={"query": "qwertyuiopasdfgh", "topn": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("items"), list)


def test_branding_endpoint_roundtrip(tmp_path, monkeypatch):
    import config_store

    new_path = tmp_path / "branding_config.json"
    monkeypatch.setattr(config_store, "CONFIG_PATH", new_path)
    app._branding_cache = config_store.DEFAULT_CONFIG.copy()

    resp = client.get("/api/branding")
    assert resp.status_code == 200
    data = resp.json()
    assert "logo_url" in data and "youtube_url" in data and "nl_prompt" in data
    assert "voice_mode_enabled" in data

    payload = {
        "logo_url": "https://example.com/logo.png",
        "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
        "nl_prompt": "請協助解析自然語言查詢。",
        "voice_mode_enabled": True,
    }
    save_resp = client.post("/api/branding", json=payload)
    assert save_resp.status_code == 200
    saved = save_resp.json().get("data")
    assert saved == payload
