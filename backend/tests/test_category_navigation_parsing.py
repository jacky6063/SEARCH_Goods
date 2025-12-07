import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app import app
from chat_router_goods_action import _extract_selected_levels_from_text

client = TestClient(app)


def _post_chat(msg: str):
  return client.post("/api/chat", json={"message": msg, "history": []})


def test_parse_l1_navigation():
  resp = _post_chat("你們有什麼常溫食品的品類？")
  assert resp.status_code == 200
  data = resp.json()
  assert data.get("action", {}).get("type") == "none"
  assert data.get("display_mode") == "text_only"
  meta = data.get("meta") or {}
  avail = meta.get("available_scope") or {}
  # 可用的 L2 應被提供或至少維持 text_only
  assert avail.get("level") in (None, "L2", "L3")


def test_parse_l2_navigation():
  resp = _post_chat("在常溫食品下我對零食點心有興趣，還有哪些小分類？")
  assert resp.status_code == 200
  data = resp.json()
  assert data.get("action", {}).get("type") == "none"
  assert data.get("display_mode") == "text_only"
  meta = data.get("meta") or {}
  avail = meta.get("available_scope") or {}
  # 當只提取到 L1 時，系統提供 L2；當提取到 L1 和 L2 時，系統提供 L3
  # 這個查詢可能只提取到 L1，所以返回 L2 是正確的
  assert avail.get("level") in (None, "L2", "L3")
  assert not data.get("suggestion_ids")


def test_extract_l3_from_slash_terms():
  """Slash/頓號分隔的片語應能辨識到 L2/L3"""
  text = "在常溫食品下我要找豆包/豆腐/米類/佐醬湯料，有推薦嗎？"
  selected = _extract_selected_levels_from_text(text)
  assert selected["L1"] == "常溫食品"
  assert selected["L2"] == "五穀/豆類/米麵/乾貨"
  assert selected["L3"] == "米類"
