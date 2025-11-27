# -*- coding: utf-8 -*-
"""
================================================================================
SEARCH_Goods 系統 - 住宅維修搜尋服務
================================================================================

檔案名稱: repair_search_service.py
建立日期: 2025年11月11日
撰寫模型: GitHub Copilot (Claude 3.5 Sonnet)

功能描述:
    住宅維修項目搜尋引擎，實現 CSV 格式維修資料的搜尋、評分和格式化
    參考 goods_search_service.py 架構設計，專門處理維修報修場景

核心功能:
    - search_repairs(query) - 執行維修項目搜尋並返回評分結果
    - format_for_chat(results) - 格式化為聊天介面格式
    - get_repairs_by_ids(ids) - 依 ID 批量取得維修項目

數據結構:
    CSV 欄位: 責任類型, 維修項目類別, 維修項目名稱, 常見維修反應細項,
             專業檢查方法, 處理建議 (SOP) 補充, 頁面連結, Youtube 影片說明

================================================================================
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import pandas as pd
import re
from typing import List, Tuple, Dict, Any, Optional
from difflib import get_close_matches

# 從 repair_constants 導入常數
try:
    from repair_constants import (
        REPAIR_KEYWORDS,
        REPAIR_CATEGORY_MAP,
        RESPONSIBILITY_TYPES,
        REPAIR_CSV_COLUMNS
    )
except ImportError:
    # 降級保護：如果常數檔案不存在，使用基本配置
    REPAIR_KEYWORDS = {
        "給排水": ["漏水", "滴水", "堵塞", "水龍頭", "馬桶"],
        "電力": ["跳電", "斷電", "漏電", "開關", "插座"],
        "門窗": ["門鎖", "窗戶", "紗窗"],
        "空調": ["冷氣", "空調", "不冷"],
        "結構": ["壁癌", "裂縫", "滲水"],
    }
    REPAIR_CATEGORY_MAP = {}
    RESPONSIBILITY_TYPES = ["住家", "公設"]
    REPAIR_CSV_COLUMNS = {
        "responsibility": "責任類型",
        "category": "維修項目類別",
        "name": "維修項目名稱",
        "symptoms": "常見維修反應細項",
        "inspection": "專業檢查方法",
        "solution": "處理建議 (SOP) 補充",
        "link": "頁面連結",
        "video": "Youtube 影片說明"
    }

# 設定資料路徑
ROOT = Path(__file__).resolve().parents[1]

# 使用集中式路徑管理器（替代重複的 _get_repair_csv_path 邏輯）
from path_manager import REPAIR_DATA_PATH as DEFAULT_REPAIR_CSV_PATH

# 全局快取
_REPAIR_DF_CACHE: Optional[pd.DataFrame] = None
_REPAIR_ROWS_CACHE: Optional[List[Dict[str, Any]]] = None


def load_repair_data(csv_path: Optional[str] = None, refresh: bool = False) -> pd.DataFrame:
    """
    載入維修資料 CSV
    
    Args:
        csv_path: CSV 檔案路徑，若為 None 則使用預設路徑
        refresh: 是否強制重新載入
    
    Returns:
        pd.DataFrame: 維修資料
    """
    global _REPAIR_DF_CACHE
    
    if not refresh and _REPAIR_DF_CACHE is not None:
        return _REPAIR_DF_CACHE
    
    if csv_path is None:
        csv_path = str(DEFAULT_REPAIR_CSV_PATH)
    
    try:
        df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig").fillna("")
        
        # 🔧 建立文本快取（加速搜尋）
        if not df.empty:
            import time as time_module
            cache_start = time_module.time()
            df["__text_cache__"] = df.apply(_row_text, axis=1)
            cache_elapsed = (time_module.time() - cache_start) * 1000
            print(f"[INFO] 維修資料文本快取構建完成: {len(df)} 行, 耗時 {cache_elapsed:.1f}ms")
        
        _REPAIR_DF_CACHE = df
        return df
        
    except Exception as e:
        print(f"[ERROR] 載入維修資料失敗: {e}")
        return pd.DataFrame()


def _norm(s: str) -> str:
    """標準化字串（轉小寫、去空白）"""
    return str(s or "").strip().lower()


def _row_text(row: Dict[str, Any]) -> str:
    """
    提取維修項目的所有文本內容用於搜尋
    
    組合欄位：
    - 責任類型
    - 維修項目類別
    - 維修項目名稱
    - 常見維修反應細項
    - 專業檢查方法
    - 處理建議
    """
    parts = [
        row.get(REPAIR_CSV_COLUMNS["responsibility"], ""),
        row.get(REPAIR_CSV_COLUMNS["category"], ""),
        row.get(REPAIR_CSV_COLUMNS["name"], ""),
        row.get(REPAIR_CSV_COLUMNS["symptoms"], ""),
        row.get(REPAIR_CSV_COLUMNS["inspection"], ""),
        row.get(REPAIR_CSV_COLUMNS["solution"], ""),
    ]
    return " ".join(str(p) for p in parts).lower()


def extract_repair_terms(query: str) -> List[str]:
    """
    從查詢中提取維修相關詞彙
    
    策略：
    1. 按空格、逗號等分割
    2. 提取中文片段（2-4字）
    3. 匹配預定義的維修關鍵字
    
    Args:
        query: 使用者查詢
    
    Returns:
        List[str]: 提取的詞彙列表
    """
    q = _norm(query)
    
    # 基本分割
    parts = [p for p in re.split(r"[ ,;|/+\-]+", q) if p]
    
    # 提取中文片段
    zh_terms: List[str] = []
    for token in parts:
        if any("\u4e00" <= ch <= "\u9fff" for ch in token) and len(token) >= 2:
            # 提取 2-4 字的中文詞組
            for size in range(2, min(5, len(token) + 1)):
                for idx in range(0, len(token) - size + 1):
                    zh_terms.append(token[idx:idx + size])
    
    # 匹配預定義的維修關鍵字
    matched_keywords: List[str] = []
    for category_keywords in REPAIR_KEYWORDS.values():
        for keyword in category_keywords:
            if keyword in q:
                matched_keywords.append(keyword)
    
    # 合併並去重（保持順序）
    all_terms = parts + zh_terms + matched_keywords
    seen = set()
    ordered = []
    for term in all_terms:
        if term and term not in seen:
            seen.add(term)
            ordered.append(term)
    
    return ordered


def score_repair_row(row: Dict[str, Any], terms: List[str], original_query: str = "") -> float:
    """
    計算維修項目相關性分數
    
    評分邏輯：
    - 維修項目名稱匹配: +5.0 分
    - 常見症狀匹配: +3.0 分
    - 類別匹配: +2.0 分
    - 其他欄位匹配: +1.0 分
    - 責任類型匹配（住家優先）: +0.5 分
    
    Args:
        row: 維修項目資料行
        terms: 提取的搜尋詞彙列表
        original_query: 原始查詢字串
    
    Returns:
        float: 相關性分數
    """
    # 使用文本快取（如果存在）
    if "__text_cache__" in row and row["__text_cache__"]:
        text = row["__text_cache__"]
    else:
        text = _row_text(row)
    
    score = 0.0
    
    # 欄位內容（用於精確匹配）
    name = _norm(row.get(REPAIR_CSV_COLUMNS["name"], ""))
    symptoms = _norm(row.get(REPAIR_CSV_COLUMNS["symptoms"], ""))
    category = _norm(row.get(REPAIR_CSV_COLUMNS["category"], ""))
    responsibility = _norm(row.get(REPAIR_CSV_COLUMNS["responsibility"], ""))
    
    for term in terms:
        normalized = _norm(term)
        if not normalized:
            continue
        
        # 檢查詞彙出現在哪個欄位
        if normalized in name:
            score += 5.0  # 項目名稱最重要
        elif normalized in symptoms:
            score += 3.0  # 症狀描述次要
        elif normalized in category:
            score += 2.0  # 類別匹配
        elif normalized in text:
            score += 1.0  # 其他欄位匹配
    
    # 責任類型加分（住家優先）- 只在有基礎分數時加分
    if score > 0 and "住家" in responsibility:
        score += 0.5
    
    return score


def search_repairs(
    df: Optional[pd.DataFrame] = None,
    query: str = "",
    topn: int = 5,
    min_score: float = 1.0,
    responsibility_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    搜尋維修項目
    
    Args:
        df: DataFrame（若為 None 則自動載入）
        query: 使用者查詢
        topn: 返回結果數量
        min_score: 最低分數閾值
        responsibility_filter: 責任類型篩選（"住家" 或 "公設"）
        category_filter: 維修類別篩選
    
    Returns:
        (results, terms): 搜尋結果和提取的關鍵字
    """
    # 載入資料
    if df is None:
        df = load_repair_data()
    
    if df.empty:
        return [], []
    
    # 提取查詢詞彙
    terms = extract_repair_terms(query)
    
    if not terms and not query:
        # 無查詢詞彙，返回前 N 筆
        return df.head(topn).to_dict(orient="records"), []
    
    # 計算分數
    records = df.to_dict(orient="records")
    scores: List[float] = [score_repair_row(r, terms, query) for r in records]
    
    sdf = df.copy()
    sdf["__score__"] = scores
    
    # 應用篩選條件
    if responsibility_filter:
        responsibility_col = REPAIR_CSV_COLUMNS["responsibility"]
        if responsibility_col in sdf.columns:
            sdf = sdf[sdf[responsibility_col].str.contains(responsibility_filter, na=False)]
    
    if category_filter:
        category_col = REPAIR_CSV_COLUMNS["category"]
        if category_col in sdf.columns:
            sdf = sdf[sdf[category_col].str.contains(category_filter, na=False)]
    
    # 分數閾值篩選
    filtered = sdf[sdf["__score__"] >= min_score]
    
    if filtered.empty:
        # 降低閾值重試
        filtered = sdf[sdf["__score__"] >= 0.5]
    
    if filtered.empty:
        return [], terms
    
    # 排序
    sorted_df = filtered.sort_values("__score__", ascending=False)
    
    # 智能篩選：只返回與最高分相近的結果
    # 如果最高分 >= 5.0（高相關性），則只返回分數 >= 最高分*0.6 的結果
    # 否則返回前 topn 筆
    if not sorted_df.empty:
        max_score = sorted_df["__score__"].iloc[0]
        if max_score >= 5.0:
            # 高相關性結果：只保留分數接近最高分的項目
            score_threshold = max(min_score, max_score * 0.6)
            sorted_df = sorted_df[sorted_df["__score__"] >= score_threshold]
    
    # 取前 N 筆
    results = sorted_df.head(topn).drop(columns=["__score__"], errors="ignore").to_dict(orient="records")
    
    return results, terms


def format_for_chat(records: List[Dict[str, Any]], slim_mode: bool = False) -> List[Dict[str, Any]]:
    """
    格式化維修項目列表為聊天介面格式
    
    Args:
        records: 維修項目記錄列表
        slim_mode: 瘦身模式，僅返回必需欄位
    
    Returns:
        格式化後的維修項目列表
    """
    out: List[Dict[str, Any]] = []
    
    for idx, r in enumerate(records, start=1):
        if slim_mode:
            # 瘦身模式：只返回核心欄位
            item = {
                "序號": idx,
                "維修項目": r.get(REPAIR_CSV_COLUMNS["name"], ""),
                "維修類別": r.get(REPAIR_CSV_COLUMNS["category"], ""),
                "常見症狀": r.get(REPAIR_CSV_COLUMNS["symptoms"], "")[:80],  # 簡化
                "頁面連結": r.get(REPAIR_CSV_COLUMNS["link"], ""),
                "影片說明": r.get(REPAIR_CSV_COLUMNS["video"], ""),
            }
        else:
            # 完整模式：返回所有欄位
            item = {
                "序號": idx,
                "責任類型": r.get(REPAIR_CSV_COLUMNS["responsibility"], ""),
                "維修類別": r.get(REPAIR_CSV_COLUMNS["category"], ""),
                "維修項目": r.get(REPAIR_CSV_COLUMNS["name"], ""),
                "常見症狀": r.get(REPAIR_CSV_COLUMNS["symptoms"], ""),
                "檢查方法": r.get(REPAIR_CSV_COLUMNS["inspection"], ""),
                "處理建議": r.get(REPAIR_CSV_COLUMNS["solution"], ""),
                "頁面連結": r.get(REPAIR_CSV_COLUMNS["link"], ""),
                "影片說明": r.get(REPAIR_CSV_COLUMNS["video"], ""),
            }
        
        out.append(item)
    
    return out


def get_repairs_by_ids(df: Optional[pd.DataFrame] = None, id_list: List[int] = None) -> List[Dict[str, Any]]:
    """
    依序號取得維修項目（用於對話追蹤）
    
    Args:
        df: DataFrame（若為 None 則自動載入）
        id_list: 序號列表（1-based index）
    
    Returns:
        維修項目列表
    """
    if df is None:
        df = load_repair_data()
    
    if df.empty or not id_list:
        return []
    
    results = []
    for idx in id_list:
        # 轉換為 0-based index
        row_idx = idx - 1
        if 0 <= row_idx < len(df):
            results.append(df.iloc[row_idx].to_dict())
    
    return results


def find_repair_by_name(df: Optional[pd.DataFrame] = None, name: str = "", limit: int = 1) -> List[Dict[str, Any]]:
    """
    依維修項目名稱模糊搜尋
    
    Args:
        df: DataFrame（若為 None 則自動載入）
        name: 維修項目名稱
        limit: 返回數量
    
    Returns:
        維修項目列表
    """
    if df is None:
        df = load_repair_data()
    
    if df.empty or not name:
        return []
    
    name_col = REPAIR_CSV_COLUMNS["name"]
    normalized_name = _norm(name)
    
    # 精確匹配
    exact_match = df[df[name_col].str.lower().str.strip() == normalized_name]
    if not exact_match.empty:
        return exact_match.head(limit).to_dict(orient="records")
    
    # 包含匹配
    contains_match = df[df[name_col].str.lower().str.contains(re.escape(normalized_name), na=False)]
    if not contains_match.empty:
        return contains_match.head(limit).to_dict(orient="records")
    
    # 模糊匹配
    all_names = df[name_col].str.lower().tolist()
    matches = get_close_matches(normalized_name, all_names, n=limit, cutoff=0.4)
    if matches:
        mask = df[name_col].str.lower().isin(matches)
        return df[mask].head(limit).to_dict(orient="records")
    
    return []


def get_repair_categories(df: Optional[pd.DataFrame] = None) -> List[str]:
    """
    取得所有維修類別
    
    Args:
        df: DataFrame（若為 None 則自動載入）
    
    Returns:
        維修類別列表
    """
    if df is None:
        df = load_repair_data()
    
    if df.empty:
        return []
    
    category_col = REPAIR_CSV_COLUMNS["category"]
    if category_col not in df.columns:
        return []
    
    return df[category_col].dropna().unique().tolist()


def clear_cache():
    """清除全局快取（用於資料更新後重新載入）"""
    global _REPAIR_DF_CACHE, _REPAIR_ROWS_CACHE
    _REPAIR_DF_CACHE = None
    _REPAIR_ROWS_CACHE = None
    print("[INFO] 維修資料快取已清除")


# 模組測試用的便利函數
if __name__ == "__main__":
    import sys
    
    # 載入資料
    df = load_repair_data()
    print(f"✅ 載入 {len(df)} 筆維修資料")
    
    # 測試搜尋
    test_queries = [
        "水龍頭滴水",
        "馬桶堵塞",
        "跳電",
        "冷氣不冷",
        "門鎖壞了",
    ]
    
    for query in test_queries:
        results, terms = search_repairs(df, query, topn=3)
        print(f"\n🔍 查詢: {query}")
        print(f"   關鍵字: {terms}")
        print(f"   結果數: {len(results)}")
        for idx, item in enumerate(results, 1):
            name = item.get(REPAIR_CSV_COLUMNS["name"], "")
            category = item.get(REPAIR_CSV_COLUMNS["category"], "")
            print(f"   {idx}. [{category}] {name}")
