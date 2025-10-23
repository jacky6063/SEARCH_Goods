import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure project root is on sys.path before importing app so env changes affect it
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import importlib


def test_admin_endpoints(tmp_path, monkeypatch):
    # configure ADMIN_TOKEN for the test before importing app
    monkeypatch.setenv("ADMIN_TOKEN", "secrettoken")

    # prepare a temporary destination path and point DATA_PATH env var to it
    dst_dir = tmp_path / "data"
    dst_dir.mkdir()
    dst = dst_dir / "VIEW_GOODS_enhanced.csv"
    monkeypatch.setenv("DATA_PATH", str(dst))

    # import app after envs are set so module-level DATA_PATH/ADMIN_TOKEN read the test values
    app_mod = importlib.import_module("app")
    importlib.reload(app_mod)
    client = TestClient(app_mod.app)

    # unauthorized upload should be rejected
    r = client.post("/api/admin/upload-csv", files={"file": ("f.csv", "a,b\n1,2\n")})
    assert r.status_code in (401, 403)

    # set header token and upload
    headers = {"x-admin-token": "secrettoken"}

    r = client.post("/api/admin/upload-csv", files={"file": ("f.csv", "col1,col2\n9,8\n")}, headers=headers)
    assert r.status_code == 200
    assert dst.exists()
    assert dst.read_text().startswith("col1,col2")

    # clear cache endpoint
    r2 = client.post("/api/admin/clear-cache", headers=headers)
    assert r2.status_code == 200
    assert r2.json().get("status") == "ok"
