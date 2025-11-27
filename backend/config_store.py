# -*- coding: utf-8 -*-
"""
================================================================================
SEARCH_Goods 系統 - 品牌設定存儲
================================================================================

檔案名稱: config_store.py
撰寫日期: 2025年11月5日
撰寫時間: 15:00-17:30
撰寫模型: GitHub Copilot (Claude 3.5 Sonnet)
最後更新: 2025年11月5日 17:30

功能描述:
    動態品牌設定管理，支援執行時修改和持久化存儲
    安全的執行緒式訪問控制

核心功能:
    - load_branding_config() - 載入品牌設定
    - save_branding_config(config) - 儲存設定
    - get_config_value(key) - 取得特定設定值

================================================================================
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any
import threading

_lock = threading.Lock()
CONFIG_PATH = Path(__file__).resolve().parent / "branding_config.json"
DEFAULT_CONFIG = {
    "logo_url": "",
    "youtube_url": "",
    "nl_prompt": "",
    "voice_mode_enabled": False,
}


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _cast_value(key: str, value: Any) -> Any:
    default = DEFAULT_CONFIG.get(key)
    if isinstance(default, bool):
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)
    if isinstance(default, str):
        return str(value or "").strip()
    return value


def load_branding_config() -> Dict[str, Any]:
    with _lock:
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    merged = DEFAULT_CONFIG.copy()
                    for key in DEFAULT_CONFIG.keys():
                        if key in data:
                            merged[key] = _cast_value(key, data[key])
                    return merged
            except Exception:
                pass
        return DEFAULT_CONFIG.copy()


def save_branding_config(
    logo_url: str,
    youtube_url: str,
    nl_prompt: str,
    voice_mode_enabled: bool,
) -> Dict[str, Any]:
    with _lock:
        payload = {
            "logo_url": (logo_url or "").strip(),
            "youtube_url": (youtube_url or "").strip(),
            "nl_prompt": (nl_prompt or "").strip(),
            "voice_mode_enabled": bool(voice_mode_enabled),
        }
        _ensure_parent(CONFIG_PATH)
        CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload.copy()
