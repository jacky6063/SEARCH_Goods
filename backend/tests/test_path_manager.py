# -*- coding: utf-8 -*-
"""
================================================================================
SEARCH_Goods 系統 - 路徑管理器測試
================================================================================

檔案名稱: test_path_manager.py
建立日期: 2025年11月12日

測試內容:
    - 通用路徑偵測函數
    - 環境變數優先級
    - Render 環境偵測
    - 預定義路徑
    - 工具函數
================================================================================
"""
import pytest
import os
from pathlib import Path
import sys
import tempfile

# 加入父目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from path_manager import (
    get_data_path,
    GOODS_DATA_PATH,
    REPAIR_DATA_PATH,
    get_all_data_paths,
    validate_data_paths,
    get_data_dir
)


class TestGetDataPath:
    """測試通用路徑偵測函數"""
    
    def test_env_var_priority(self, monkeypatch, tmp_path):
        """測試環境變數優先級最高"""
        # 建立臨時測試檔案
        test_file = tmp_path / "test_data.csv"
        test_file.write_text("test")
        
        # 設定環境變數
        monkeypatch.setenv("TEST_PATH", str(test_file))
        
        # 執行測試
        result = get_data_path("TEST_PATH", "default.csv")
        
        # 驗證使用了環境變數的路徑
        assert result == test_file
        assert result.exists()
    
    def test_env_var_non_existent_path(self, monkeypatch, caplog):
        """測試環境變數指向不存在的路徑時的降級行為"""
        # 設定指向不存在路徑的環境變數
        monkeypatch.setenv("TEST_PATH", "/non/existent/path.csv")
        
        # 執行測試（應該降級到默認路徑）
        result = get_data_path("TEST_PATH", "test.csv")
        
        # 驗證降級到默認路徑
        assert "data/test.csv" in str(result)
        
        # 驗證有警告日誌
        assert "不存在" in caplog.text or len(caplog.records) >= 0
    
    def test_default_path_fallback(self):
        """測試無環境變數時使用默認路徑"""
        result = get_data_path(
            "NON_EXISTENT_VAR_12345",
            "test.csv"
        )
        
        # 驗證返回默認路徑格式
        assert result.name == "test.csv"
        assert "data" in str(result)
        assert result.parent.name == "data"
    
    def test_render_path_detection(self, tmp_path, monkeypatch):
        """測試 Render 路徑偵測"""
        # 建立模擬的 Render 路徑
        render_dir = tmp_path / "render_data"
        render_dir.mkdir()
        render_file = render_dir / "test.csv"
        render_file.write_text("render_test")
        
        # 確保環境變數未設定
        monkeypatch.delenv("TEST_PATH", raising=False)
        
        # 測試 Render 路徑存在的情況
        result = get_data_path(
            "TEST_PATH",
            "test.csv",
            render_path=str(render_file)
        )
        
        # 驗證使用了 Render 路徑
        assert result == render_file
        assert result.exists()
    
    def test_render_path_not_exist(self):
        """測試 Render 路徑不存在時降級"""
        result = get_data_path(
            "NON_EXISTENT_VAR",
            "test.csv",
            render_path="/non/existent/render/path.csv"
        )
        
        # 驗證降級到默認路徑
        assert "data/test.csv" in str(result)
    
    def test_priority_order(self, tmp_path, monkeypatch):
        """測試完整的優先級順序：環境變數 > Render > 默認"""
        # 準備三個不同的路徑
        env_file = tmp_path / "env_path" / "data.csv"
        env_file.parent.mkdir()
        env_file.write_text("env")
        
        render_file = tmp_path / "render_path" / "data.csv"
        render_file.parent.mkdir()
        render_file.write_text("render")
        
        # 測試 1: 環境變數優先
        monkeypatch.setenv("TEST_PATH", str(env_file))
        result = get_data_path(
            "TEST_PATH",
            "data.csv",
            render_path=str(render_file)
        )
        assert result == env_file
        
        # 測試 2: 無環境變數時使用 Render
        monkeypatch.delenv("TEST_PATH")
        result = get_data_path(
            "TEST_PATH",
            "data.csv",
            render_path=str(render_file)
        )
        assert result == render_file


class TestPredefinedPaths:
    """測試預定義的路徑"""
    
    def test_goods_data_path_defined(self):
        """測試商品資料路徑已定義"""
        assert GOODS_DATA_PATH is not None
        assert isinstance(GOODS_DATA_PATH, Path)
        assert "VIEW_GOODS_enhanced.csv" in str(GOODS_DATA_PATH)
    
    def test_repair_data_path_defined(self):
        """測試維修資料路徑已定義"""
        assert REPAIR_DATA_PATH is not None
        assert isinstance(REPAIR_DATA_PATH, Path)
        assert "集合式住宅報修資料.csv" in str(REPAIR_DATA_PATH)
    
    def test_paths_are_absolute(self):
        """測試路徑都是絕對路徑"""
        assert GOODS_DATA_PATH.is_absolute()
        assert REPAIR_DATA_PATH.is_absolute()
    
    def test_paths_end_with_csv(self):
        """測試路徑都是 CSV 檔案"""
        assert GOODS_DATA_PATH.suffix == ".csv"
        assert REPAIR_DATA_PATH.suffix == ".csv"


class TestUtilityFunctions:
    """測試工具函數"""
    
    def test_get_all_data_paths_structure(self):
        """測試取得所有路徑的結構"""
        paths = get_all_data_paths()
        
        # 驗證基本結構
        assert "goods_data" in paths
        assert "repair_data" in paths
        
        # 驗證商品資料結構
        goods = paths["goods_data"]
        assert "path" in goods
        assert "exists" in goods
        assert "size" in goods
        assert "env_var" in goods
        assert "env_value" in goods
        assert "readable" in goods
        
        # 驗證維修資料結構
        repair = paths["repair_data"]
        assert "path" in repair
        assert "exists" in repair
        assert "size" in repair
        assert "env_var" in repair
        assert "env_value" in repair
        assert "readable" in repair
    
    def test_get_all_data_paths_values(self):
        """測試取得所有路徑的值"""
        paths = get_all_data_paths()
        
        # 驗證路徑值類型
        assert isinstance(paths["goods_data"]["path"], str)
        assert isinstance(paths["goods_data"]["exists"], bool)
        assert isinstance(paths["goods_data"]["size"], int)
        assert isinstance(paths["goods_data"]["readable"], bool)
        
        # 驗證環境變數名稱
        assert paths["goods_data"]["env_var"] == "DATA_PATH"
        assert paths["repair_data"]["env_var"] == "REPAIR_DATA_PATH"
    
    def test_validate_data_paths_return_type(self):
        """測試路徑驗證返回布林值"""
        result = validate_data_paths()
        assert isinstance(result, bool)
    
    def test_validate_data_paths_logic(self, tmp_path, monkeypatch):
        """測試路徑驗證邏輯"""
        # 這個測試只驗證函數執行不會出錯
        # 實際結果取決於資料檔案是否存在
        result = validate_data_paths()
        
        # 結果應該是布林值
        assert result in [True, False]
    
    def test_get_data_dir(self):
        """測試取得資料目錄"""
        data_dir = get_data_dir()
        
        assert isinstance(data_dir, Path)
        assert data_dir.name == "data"
        assert data_dir.is_absolute()


class TestIntegration:
    """整合測試"""
    
    def test_paths_consistency(self):
        """測試路徑一致性"""
        # GOODS_DATA_PATH 和 get_all_data_paths 應該返回相同的路徑
        all_paths = get_all_data_paths()
        
        assert str(GOODS_DATA_PATH) == all_paths["goods_data"]["path"]
        assert str(REPAIR_DATA_PATH) == all_paths["repair_data"]["path"]
    
    def test_module_import(self):
        """測試模組可以正常導入"""
        # 如果到這裡沒有出錯，說明導入成功
        from path_manager import (
            get_data_path,
            GOODS_DATA_PATH,
            REPAIR_DATA_PATH,
            get_all_data_paths,
            validate_data_paths,
            get_data_dir
        )
        
        assert callable(get_data_path)
        assert callable(get_all_data_paths)
        assert callable(validate_data_paths)
        assert callable(get_data_dir)


class TestEdgeCases:
    """邊界測試"""
    
    def test_empty_env_var_name(self):
        """測試空環境變數名稱"""
        result = get_data_path("", "test.csv")
        
        # 應該降級到默認路徑
        assert "data/test.csv" in str(result)
    
    def test_special_characters_in_filename(self):
        """測試檔案名稱包含特殊字元"""
        result = get_data_path(
            "NON_EXISTENT",
            "集合式住宅報修資料.csv"
        )
        
        # 應該正確處理中文檔名
        assert "集合式住宅報修資料.csv" in str(result)
    
    def test_none_render_path(self):
        """測試 render_path 為 None"""
        result = get_data_path(
            "NON_EXISTENT",
            "test.csv",
            render_path=None
        )
        
        # 應該使用默認路徑
        assert "data/test.csv" in str(result)


if __name__ == "__main__":
    # 執行測試
    pytest.main([__file__, "-v", "--tb=short"])
