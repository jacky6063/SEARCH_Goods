from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

import pandas as pd

from goods_search_service import (
    DEFAULT_DATA_PATH,
    get_catalog_snapshot,
    get_items_by_ids,
    load_data,
)


class ProductCatalogService:
    """
    封裝商品資料的載入與查詢行為，提供集中式快取與查詢介面。
    """

    def __init__(self, data_path: Optional[str] = None) -> None:
        self._data_path = str(data_path or DEFAULT_DATA_PATH)
        self._df_cache: Optional[pd.DataFrame] = None
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._df_cache = None

    def set_data_path(self, data_path: str) -> None:
        """更新資料來源路徑並清除快取。"""
        with self._lock:
            self._data_path = str(data_path)
            self._df_cache = None

    def set_dataframe(self, df: pd.DataFrame) -> None:
        """以記憶體中的 DataFrame 覆蓋快取（需呼叫端保證 df 穩定）。"""
        with self._lock:
            self._df_cache = df

    def refresh(self) -> pd.DataFrame:
        with self._lock:
            self._df_cache = load_data(self._data_path)
            return self._df_cache

    def get_dataframe(self, refresh: bool = False) -> pd.DataFrame:
        # 快速路徑：如果快取存在且不需要刷新，直接返回
        if not refresh and self._df_cache is not None:
            return self._df_cache
            
        with self._lock:
            # 雙重檢查鎖定模式
            if not refresh and self._df_cache is not None:
                return self._df_cache
            self._df_cache = load_data(self._data_path)
            return self._df_cache

    def get_items_by_ids(self, ids: List[Any]) -> List[Dict[str, Any]]:
        df = self.get_dataframe()
        return get_items_by_ids(df, ids)

    def snapshot(self, limit: int = 200) -> List[Dict[str, Any]]:
        return get_catalog_snapshot(limit=limit)


catalog_service = ProductCatalogService()
