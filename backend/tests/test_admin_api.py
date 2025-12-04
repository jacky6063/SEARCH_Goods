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
    # 確保開發者 admin 模式被禁用，以便測試令牌驗證
    monkeypatch.setenv("ALLOW_DEV_ADMIN", "false")

    # prepare a temporary destination path and point DATA_PATH env var to it
    dst_dir = tmp_path / "data"
    dst_dir.mkdir()
    dst = dst_dir / "VIEW_GOODS_enhanced.csv"
    monkeypatch.setenv("DATA_PATH", str(dst))
    cat_dst = dst_dir / "goods_categories.csv"
    monkeypatch.setenv("CATEGORIES_PATH", str(cat_dst))

    # import and reload path_manager first to pick up the env var
    import path_manager
    importlib.reload(path_manager)
    
    # 直接修改 path_manager 中的路徑常數以確保測試環境正確
    monkeypatch.setattr(path_manager, "GOODS_DATA_PATH", dst)
    
    # import app after envs are set so module-level DATA_PATH/ADMIN_TOKEN read the test values
    app_mod = importlib.import_module("app")
    importlib.reload(app_mod)
    
    # 同時需要修改 app_mod 中的 DATA_PATH
    monkeypatch.setattr(app_mod, "DATA_PATH", dst)
    
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
    # bad csv should be rejected
    r_bad = client.post("/api/admin/upload-csv", files={"file": ("f.csv", "")}, headers=headers)
    assert r_bad.status_code == 400

    # clear cache endpoint
    r2 = client.post("/api/admin/clear-cache", headers=headers)
    assert r2.status_code == 200
    assert r2.json().get("status") == "ok"

    # upload categories csv
    cat_content = "L1,L2,L3,Enabled,DisplayOrder\nA,B,C,1,1\n"
    r3 = client.post("/api/admin/upload-categories", files={"file": ("cats.csv", cat_content)}, headers=headers)
    assert r3.status_code == 200
    assert cat_dst.exists()
    assert "A,B,C" in cat_dst.read_text()
    # missing columns should fail
    r4 = client.post("/api/admin/upload-categories", files={"file": ("cats.csv", "X,Y,Z\n1,2,3\n")}, headers=headers)
    assert r4.status_code == 400
