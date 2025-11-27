# -*- coding: utf-8 -*-
"""
================================================================================
SEARCH_Goods 系統 - 常數和設定定義
================================================================================

檔案名稱: constants.py
撰寫日期: 2025年11月5日
撰寫時間: 18:00-18:30
撰寫模型: GitHub Copilot (Claude 3.5 Sonnet)
最後更新: 2025年11月5日 18:30

功能描述:
    集中管理系統中的常數定義，包括欄位對應、列舉值等
    提供單一修改點，減少代碼重複

核心功能:
    - COLUMN_MAPPING: 欄位對應定義 (CSV/程式碼/API)
    - LEVEL_NAMES: 層級名稱定義
    - 輔助函數: 欄位查詢和驗證

================================================================================
"""
from typing import Dict, List, Optional

# ============================================================================
# 🏷️ 欄位對應定義 - 統一管理 L1/L2/L3 層級欄位名稱
# ============================================================================

COLUMN_MAPPING = {
    "L1": {
        "csv": "大分類名稱",
        "code": "CateName_L1",
        "aliases": ["L1", "category_l1", "Category_L1"],
        "description": "大分類 (主分類)"
    },
    "L2": {
        "csv": "中分類名稱",
        "code": "CateName_L2",
        "aliases": ["L2", "category_l2", "Category_L2"],
        "description": "中分類 (次分類)"
    },
    "L3": {
        "csv": "小分類名稱",
        "code": "CateName_L3",
        "aliases": ["L3", "category_l3", "Category_L3"],
        "description": "小分類 (詳細分類)"
    }
}

# ============================================================================
# 📊 層級名稱 (用於顯示和文檔)
# ============================================================================

LEVEL_NAMES = {
    "L1": "大分類",
    "L2": "中分類",
    "L3": "小分類"
}

# ============================================================================
# 🔧 其他常數
# ============================================================================

# 層級評分權重 (用於 hierarchy_score 計算)
HIERARCHY_SCORE_WEIGHT = {
    "L1": 1,
    "L2": 2,
    "L3": 3
}

# 預設 Hierarchy 分數 (每個層級 3 分)
HIERARCHY_POINTS_PER_LEVEL = 3

# ============================================================================
# 🛠️ 輔助函數
# ============================================================================

def get_column_names(level: str) -> Dict[str, str]:
    """
    取得指定層級的所有欄位名稱變體
    
    Args:
        level: 層級代碼 ("L1", "L2", "L3")
    
    Returns:
        包含主欄位、備用欄位和別名的字典
        
    Example:
        >>> get_column_names("L1")
        {
            "csv": "大分類名稱",
            "code": "CateName_L1",
            "aliases": ["L1", "category_l1", "Category_L1"]
        }
    """
    if level not in COLUMN_MAPPING:
        raise ValueError(f"Invalid level: {level}. Must be one of {list(COLUMN_MAPPING.keys())}")
    return COLUMN_MAPPING[level]


def get_all_column_variants(level: str) -> List[str]:
    """
    取得指定層級的所有可能欄位名稱 (包括別名)
    
    Args:
        level: 層級代碼 ("L1", "L2", "L3")
    
    Returns:
        所有可能的欄位名稱列表
        
    Example:
        >>> get_all_column_variants("L1")
        ["大分類名稱", "CateName_L1", "L1", "category_l1", "Category_L1"]
    """
    mapping = get_column_names(level)
    variants = [mapping["csv"], mapping["code"]] + mapping["aliases"]
    return variants


def get_primary_column(level: str, prefer_code: bool = False) -> str:
    """
    取得指定層級的主要欄位名稱
    
    Args:
        level: 層級代碼 ("L1", "L2", "L3")
        prefer_code: 優先返回程式碼欄位名 (預設返回 CSV 欄位名)
    
    Returns:
        主要欄位名稱
        
    Example:
        >>> get_primary_column("L1")
        "大分類名稱"
        
        >>> get_primary_column("L1", prefer_code=True)
        "CateName_L1"
    """
    mapping = get_column_names(level)
    return mapping["code"] if prefer_code else mapping["csv"]


def find_column_level(column_name: str) -> Optional[str]:
    """
    根據欄位名稱反查層級
    
    Args:
        column_name: 欄位名稱
    
    Returns:
        層級代碼 ("L1", "L2", "L3") 或 None
        
    Example:
        >>> find_column_level("大分類名稱")
        "L1"
        
        >>> find_column_level("CateName_L2")
        "L2"
        
        >>> find_column_level("unknown_column")
        None
    """
    for level, mapping in COLUMN_MAPPING.items():
        all_variants = [mapping["csv"], mapping["code"]] + mapping["aliases"]
        if column_name in all_variants:
            return level
    return None


def get_hierarchy_columns() -> Dict[str, str]:
    """
    取得層級結構所需的所有欄位 (優先使用 CSV 欄位名)
    
    Returns:
        層級對應字典 {"L1": "大分類名稱", "L2": "中分類名稱", "L3": "小分類名稱"}
        
    Example:
        >>> get_hierarchy_columns()
        {
            "L1": "大分類名稱",
            "L2": "中分類名稱",
            "L3": "小分類名稱"
        }
    """
    return {level: get_primary_column(level) for level in ["L1", "L2", "L3"]}


def validate_hierarchy_levels(hierarchy: dict) -> bool:
    """
    驗證 Hierarchy 字典是否有效
    
    Args:
        hierarchy: Hierarchy 字典 {"L1": "...", "L2": "...", ...}
    
    Returns:
        True 如果所有 key 都是有效層級
        
    Example:
        >>> validate_hierarchy_levels({"L1": "常溫食品", "L2": "調味"})
        True
        
        >>> validate_hierarchy_levels({"L4": "invalid"})
        False
    """
    if not isinstance(hierarchy, dict):
        return False
    return all(level in COLUMN_MAPPING for level in hierarchy.keys())
