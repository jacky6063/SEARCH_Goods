import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_catalog_scope_l1_basic():
    resp = client.get("/api/catalog/scope?level=L1&top_k=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("level") == "L1"
    assert isinstance(data.get("items"), list)
    # 如果資料存在，items 可能非空；但為了兼容空資料，也只檢查型別
    assert "more_count" in data
