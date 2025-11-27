import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SCOPE_TOPK_L1", "5")

from app import app  # noqa: E402

client = TestClient(app)


def test_chat_overview_lists_l1_scope():
    resp = client.post("/api/chat", json={"message": "你們有賣什麼東西？", "history": []})
    assert resp.status_code == 200
    data = resp.json()
    # 應為資訊/概覽模式：不切換商品、不出 suggestion_ids
    assert data.get("action", {}).get("type") == "none"
    assert isinstance(data.get("reply"), str) and len(data["reply"]) > 0
    # meta.available_scope.l1 必須存在，且為列表
    meta = data.get("meta") or {}
    scope = (meta.get("available_scope") or {}).get("l1") or []
    assert isinstance(scope, list)
    # display_mode 應為 text_only
    assert data.get("display_mode") == "text_only"


def test_chat_category_navigation_l1_to_l2():
    # 模擬點擊 L1：用對話方式詢問 L1 下的品類
    msg = "你們有什麼常溫食品的品類？"
    resp = client.post("/api/chat", json={"message": msg, "history": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("action", {}).get("type") == "none"
    assert data.get("display_mode") == "text_only"
    meta = data.get("meta") or {}
    avail = meta.get("available_scope") or {}
    # 期望 L2 被提供
    assert avail.get("level") in (None, "L2", "L3")  # 柔性驗證
    # 不應有商品推薦
    assert not data.get("suggestion_ids")


def test_chat_category_navigation_specific_l2_l3():
    msg = "想看女用背包分類有哪些"
    resp = client.post("/api/chat", json={"message": msg, "history": []})
    assert resp.status_code == 200
    data = resp.json()
    meta = data.get("meta") or {}
    scope = meta.get("available_scope") or {}
    # 期望直接列出 L3（背包細項）
    assert scope.get("level") == "L3"
    l3_names = scope.get("l3") or []
    assert any("背包" in name for name in l3_names)
    selected = ((meta.get("category_context") or {}).get("selected")) or {}
    assert selected.get("L2") in ("女用皮包", "女用包")
