# -*- coding: utf-8 -*-
"""
================================================================================
SEARCH_Goods 系統 - 路徑管理器
================================================================================

檔案名稱: path_manager.py
建立日期: 2025年11月12日

功能描述:
    集中管理所有資料檔案的路徑偵測邏輯，避免重複代碼

核心功能:
    - get_data_path(env_var, filename) - 通用路徑偵測
    - GOODS_DATA_PATH - 商品資料路徑
    - REPAIR_DATA_PATH - 維修資料路徑

設計理念:
    - DRY (Don't Repeat Yourself) - 消除 app.py、goods_search_service.py、
      repair_search_service.py 中重複的路徑偵測邏輯
    - 單一職責 - 專門處理資料檔案路徑
    - 易於測試 - 獨立模組便於單元測試
================================================================================
"""
from pathlib import Path
import os
import logging
from typing import Optional

# 專案根目錄
ROOT = Path(__file__).resolve().parents[1]

# 設定日誌
logger = logging.getLogger(__name__)


def get_data_path(
    env_var: str,
    default_filename: str,
    render_path: Optional[str] = None
) -> Path:
    """
    通用的資料檔案路徑偵測函數
    
    偵測順序（優先級由高到低）:
    1. 環境變數指定的路徑
    2. Render 環境的標準路徑
    3. 本地開發環境的默認路徑
    
    Args:
        env_var: 環境變數名稱 (例: "DATA_PATH", "REPAIR_DATA_PATH")
        default_filename: 默認檔案名稱 (例: "VIEW_GOODS_enhanced.csv")
        render_path: Render 環境的完整路徑 (可選)
    
    Returns:
        Path: 偵測到的檔案路徑
    
    Examples:
        >>> get_data_path("DATA_PATH", "VIEW_GOODS_enhanced.csv")
        PosixPath('/path/to/data/VIEW_GOODS_enhanced.csv')
        
        >>> get_data_path(
        ...     "REPAIR_DATA_PATH",
        ...     "集合式住宅報修資料.csv",
        ...     render_path="/opt/render/project/src/data/集合式住宅報修資料.csv"
        ... )
        PosixPath('/opt/render/project/src/data/集合式住宅報修資料.csv')
    """
    # 1. 優先使用環境變數
    env_path = os.getenv(env_var)
    if env_path:
        raw_env_path = Path(env_path).expanduser()
        # 若為相對路徑，視為相對專案根目錄（避免測試環境給相對路徑時產生不一致）
        path = raw_env_path if raw_env_path.is_absolute() else (ROOT / raw_env_path).resolve()
        if path.exists():
            logger.info(f"使用環境變數路徑: {env_var}={path}")
            return path
        else:
            # 如果環境變數設定的路徑不存在，記錄警告但繼續偵測
            logger.warning(
                f"環境變數 {env_var}={env_path} 指向的路徑不存在，"
                f"將使用默認偵測邏輯"
            )
    
    # 2. 檢查 Render 環境路徑
    if render_path:
        render_full_path = Path(render_path)
        if render_full_path.exists():
            logger.info(f"偵測到 Render 環境路徑: {render_full_path}")
            return render_full_path
    
    # 3. 默認本地開發路徑
    default_path = ROOT / "data" / default_filename
    logger.info(f"使用默認本地開發路徑: {default_path}")
    return default_path


# ============================================================================
# 預定義的資料路徑
# ============================================================================

def _get_goods_data_path() -> Path:
    """
    獲取商品資料路徑的輔助函數
    用於支援測試環境中動態重載路徑
    """
    return get_data_path(
        env_var="DATA_PATH",
        default_filename="VIEW_GOODS_enhanced.csv",
        render_path="/opt/render/project/src/data/VIEW_GOODS_enhanced.csv"
    )

def _get_repair_data_path() -> Path:
    """
    獲取維修資料路徑的輔助函數
    用於支援測試環境中動態重載路徑
    """
    return get_data_path(
        env_var="REPAIR_DATA_PATH",
        default_filename="集合式住宅報修資料.csv",
        render_path="/opt/render/project/src/data/集合式住宅報修資料.csv"
    )

# 商品資料路徑（模組載入時初始化）
GOODS_DATA_PATH = _get_goods_data_path()

# 維修資料路徑（模組載入時初始化）
REPAIR_DATA_PATH = _get_repair_data_path()


# ============================================================================
# 工具函數
# ============================================================================

def get_all_data_paths() -> dict:
    """
    返回所有資料路徑的字典（用於診斷）
    
    Returns:
        dict: 包含所有資料路徑及其狀態的字典，包括：
            - path: 路徑字串
            - exists: 檔案是否存在
            - size: 檔案大小（bytes）
            - env_var: 對應的環境變數名稱
            - env_value: 環境變數的值
    
    Examples:
        >>> paths = get_all_data_paths()
        >>> print(paths['goods_data']['path'])
        '/path/to/data/VIEW_GOODS_enhanced.csv'
    """
    return {
        "goods_data": {
            "path": str(GOODS_DATA_PATH),
            "exists": GOODS_DATA_PATH.exists(),
            "size": GOODS_DATA_PATH.stat().st_size if GOODS_DATA_PATH.exists() else 0,
            "env_var": "DATA_PATH",
            "env_value": os.getenv("DATA_PATH"),
            "readable": os.access(GOODS_DATA_PATH, os.R_OK) if GOODS_DATA_PATH.exists() else False
        },
        "repair_data": {
            "path": str(REPAIR_DATA_PATH),
            "exists": REPAIR_DATA_PATH.exists(),
            "size": REPAIR_DATA_PATH.stat().st_size if REPAIR_DATA_PATH.exists() else 0,
            "env_var": "REPAIR_DATA_PATH",
            "env_value": os.getenv("REPAIR_DATA_PATH"),
            "readable": os.access(REPAIR_DATA_PATH, os.R_OK) if REPAIR_DATA_PATH.exists() else False
        }
    }


def validate_data_paths() -> bool:
    """
    驗證所有資料路徑是否有效
    
    檢查項目：
    - 檔案是否存在
    - 檔案是否可讀
    
    Returns:
        bool: 如果所有路徑都存在且可讀則返回 True，否則返回 False
    
    Examples:
        >>> if not validate_data_paths():
        ...     print("警告：部分資料檔案無法訪問")
    """
    paths = {
        "商品資料": GOODS_DATA_PATH,
        "維修資料": REPAIR_DATA_PATH
    }
    
    all_valid = True
    
    for name, path in paths.items():
        if not path.exists():
            logger.error(f"{name}檔案不存在: {path}")
            all_valid = False
        elif not os.access(path, os.R_OK):
            logger.error(f"{name}檔案無法讀取: {path}")
            all_valid = False
        else:
            logger.info(f"{name}檔案驗證通過: {path}")
    
    return all_valid


def get_data_dir() -> Path:
    """
    取得資料目錄路徑
    
    Returns:
        Path: data 目錄的路徑
    """
    return ROOT / "data"


# ============================================================================
# 診斷與測試
# ============================================================================

if __name__ == "__main__":
    # 設定日誌格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    print("=" * 70)
    print("SEARCH_Goods 資料路徑診斷")
    print("=" * 70)
    
    # 顯示所有路徑資訊
    import json
    paths_info = get_all_data_paths()
    print(json.dumps(paths_info, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 70)
    print("路徑驗證")
    print("=" * 70)
    
    # 驗證路徑
    is_valid = validate_data_paths()
    
    if is_valid:
        print("\n✅ 所有資料路徑驗證通過")
    else:
        print("\n❌ 部分資料路徑驗證失敗，請檢查上方日誌")
    
    print("\n" + "=" * 70)
