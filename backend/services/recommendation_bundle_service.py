from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional


class RecommendationBundleService:
    """
    管理聊天推薦快取的服務層，預設使用記憶體儲存，未來可替換為持久化實作。
    """

    def __init__(self, ttl_seconds: Optional[int] = None) -> None:
        default_ttl = int(os.getenv("CHAT_ALIGNMENT_CACHE_TTL", "600"))
        self._ttl = int(ttl_seconds or default_ttl)
        self._store: Dict[str, Dict[str, Any]] = {}
        self._last_cleanup = 0
        self._cleanup_interval = 60  # 每60秒才執行一次批量清理

    @property
    def ttl(self) -> int:
        return self._ttl

    def set_ttl(self, ttl_seconds: int) -> None:
        self._ttl = int(ttl_seconds)

    def cleanup(self, now: Optional[int] = None) -> None:
        current = int(now or time.time())
        expired = [
            key for key, data in self._store.items()
            if current - int(data.get("ts", 0) or 0) > self._ttl
        ]
        for key in expired:
            self._store.pop(key, None)

    def save_bundle(self, key: str, payload: Dict[str, Any]) -> None:
        data = dict(payload or {})
        data.setdefault("ts", int(time.time()))
        self._store[str(key)] = data
        
        # 定期執行批量清理
        current = int(time.time())
        if current - self._last_cleanup > self._cleanup_interval:
            self.cleanup(current)
            self._last_cleanup = current

    def get_bundle(self, key: str) -> Optional[Dict[str, Any]]:
        # 只在需要時清理，避免每次調用都執行清理
        stored = self._store.get(str(key))
        if stored is None:
            return None
        
        # 檢查當前項目是否過期
        current = int(time.time())
        if current - int(stored.get("ts", 0) or 0) > self._ttl:
            self._store.pop(str(key), None)
            return None
            
        return dict(stored)

    def delete_bundle(self, key: str) -> None:
        self._store.pop(str(key), None)

    def clear(self) -> None:
        self._store.clear()

    def raw_store(self) -> Dict[str, Dict[str, Any]]:
        """僅供除錯觀測，避免在核心流程外直接修改。"""
        return self._store


bundle_service = RecommendationBundleService()
