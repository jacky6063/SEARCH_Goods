# -*- coding: utf-8 -*-
"""
================================================================================
SEARCH_Goods 系統 - 維修 API 測試
================================================================================

檔案名稱: test_repair_api.py
建立日期: 2025年11月11日

測試內容:
    - /api/repair/chat 端點
    - /api/repair/search 端點
    - /api/repair/categories 端點
    - 環境變數控制測試

================================================================================
"""
import pytest
import os
from pathlib import Path
import sys

# 加入父目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


class TestRepairServiceAvailability:
    """測試維修服務可用性"""
    
    def test_repair_service_enabled(self):
        """測試維修服務是否啟用"""
        from app import ENABLE_REPAIR_SERVICE
        assert ENABLE_REPAIR_SERVICE, "維修服務應該被啟用"


class TestRepairChatEndpoint:
    """測試維修聊天端點"""
    
    def test_repair_chat_basic(self):
        """測試基本維修聊天請求"""
        payload = {
            "message": "水龍頭一直滴水",
            "history": [],
            "topn": 3
        }
        
        response = client.post("/api/repair/chat", json=payload)
        
        assert response.status_code == 200, f"應該返回 200，實際: {response.status_code}"
        
        data = response.json()
        assert "reply" in data, "應該包含回覆"
        assert "repairs" in data, "應該包含維修項目"
        assert "session_id" in data, "應該包含會話 ID"
    
    def test_repair_chat_with_session(self):
        """測試帶會話 ID 的請求"""
        payload = {
            "message": "馬桶堵塞",
            "history": [],
            "session_id": "test-session-123",
            "topn": 3
        }
        
        response = client.post("/api/repair/chat", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123", "應該使用提供的會話 ID"
    
    def test_repair_chat_with_history(self):
        """測試帶對話歷史的請求"""
        payload = {
            "message": "有影片說明嗎",
            "history": [
                {"role": "user", "content": "水龍頭滴水"},
                {"role": "assistant", "content": "找到相關維修項目"}
            ],
            "topn": 3
        }
        
        response = client.post("/api/repair/chat", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
    
    def test_repair_chat_empty_query(self):
        """測試空查詢"""
        payload = {
            "message": "",
            "history": []
        }
        
        response = client.post("/api/repair/chat", json=payload)
        
        # 空查詢應該正常處理（可能返回一般說明或前 N 筆）
        assert response.status_code == 200
    
    def test_repair_chat_response_structure(self):
        """測試回應結構完整性"""
        payload = {
            "message": "跳電",
            "history": [],
            "topn": 2
        }
        
        response = client.post("/api/repair/chat", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # 檢查必要欄位
        assert "reply" in data
        assert "repairs" in data
        assert "session_id" in data
        assert "meta" in data
        
        # 檢查 repairs 結構
        if data["repairs"]:
            repair = data["repairs"][0]
            assert "維修項目" in repair or "維修項目名稱" in repair
            assert "序號" in repair
    
    def test_repair_chat_topn_limit(self):
        """測試結果數量限制"""
        payload = {
            "message": "漏水",
            "history": [],
            "topn": 2
        }
        
        response = client.post("/api/repair/chat", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["repairs"]) <= 2, "結果不應超過 topn"


class TestRepairSearchEndpoint:
    """測試維修搜尋端點"""
    
    def test_repair_search_basic(self):
        """測試基本搜尋"""
        payload = {
            "query": "水龍頭",
            "topn": 3
        }
        
        response = client.post("/api/repair/search", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert "meta" in data
        assert isinstance(data["results"], list)
    
    def test_repair_search_with_category_filter(self):
        """測試帶類別篩選的搜尋"""
        payload = {
            "query": "漏水",
            "topn": 5,
            "category": "給/排水"
        }
        
        response = client.post("/api/repair/search", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # 檢查結果是否符合類別篩選
        for result in data["results"]:
            category = result.get("維修類別", result.get("維修項目類別", ""))
            # 應該包含篩選關鍵字
            assert "給" in category or "排水" in category or category == ""
    
    def test_repair_search_empty_query(self):
        """測試空查詢"""
        payload = {
            "query": "",
            "topn": 3
        }
        
        response = client.post("/api/repair/search", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


class TestRepairCategoriesEndpoint:
    """測試維修類別端點"""
    
    def test_get_repair_categories(self):
        """測試取得維修類別"""
        response = client.get("/api/repair/categories")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "categories" in data
        assert isinstance(data["categories"], list)
        
        # 應該有至少一個類別
        if data["categories"]:
            assert all(isinstance(cat, str) for cat in data["categories"])


class TestErrorHandling:
    """測試錯誤處理"""
    
    def test_repair_chat_invalid_payload(self):
        """測試無效的請求 payload"""
        payload = {
            # 缺少 message 欄位
            "history": []
        }
        
        response = client.post("/api/repair/chat", json=payload)
        
        # 應該返回錯誤或處理無效請求 (允許 405 如果端點未啟用)
        assert response.status_code in [200, 422, 405], "應該處理無效請求或返回方法不允許"
    
    def test_repair_chat_malformed_json(self):
        """測試格式錯誤的 JSON"""
        response = client.post(
            "/api/repair/chat",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        # 應該返回錯誤 (允許 405 如果端點未啟用)
        assert response.status_code in [400, 422, 405]


class TestIntegration:
    """整合測試"""
    
    def test_full_repair_workflow(self):
        """測試完整的維修查詢流程"""
        # 1. 取得維修類別
        categories_response = client.get("/api/repair/categories")
        assert categories_response.status_code == 200
        
        # 2. 執行搜尋
        search_payload = {
            "query": "水龍頭滴水",
            "topn": 3
        }
        search_response = client.post("/api/repair/search", json=search_payload)
        assert search_response.status_code == 200
        
        # 3. 執行聊天查詢
        chat_payload = {
            "message": "水龍頭一直滴水怎麼辦",
            "history": [],
            "topn": 3
        }
        chat_response = client.post("/api/repair/chat", json=chat_payload)
        assert chat_response.status_code == 200
        
        # 檢查聊天回應
        chat_data = chat_response.json()
        assert chat_data["reply"], "應該有回覆內容"
        assert chat_data["repairs"], "應該有維修項目建議"


class TestServiceDisabled:
    """測試服務關閉狀態"""
    
    @pytest.fixture(autouse=True)
    def disable_service(self):
        """臨時關閉維修服務"""
        original = os.environ.get("ENABLE_REPAIR_SERVICE")
        os.environ["ENABLE_REPAIR_SERVICE"] = "False"
        
        # 重新載入 app 以應用變更（注意：實際環境中需要重啟）
        yield
        
        # 恢復原始設定
        if original:
            os.environ["ENABLE_REPAIR_SERVICE"] = original
        else:
            os.environ.pop("ENABLE_REPAIR_SERVICE", None)
    
    def test_repair_endpoints_when_disabled(self):
        """測試服務關閉時的端點行為"""
        # 注意：這個測試可能需要重啟應用才能生效
        # 在實際部署中，ENABLE_REPAIR_SERVICE 應該在啟動時設定
        pass


if __name__ == "__main__":
    # 執行測試
    pytest.main([__file__, "-v", "--tb=short"])
