# -*- coding: utf-8 -*-
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
    "nl_prompt": ""
}


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_branding_config() -> Dict[str, Any]:
    with _lock:
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    merged = DEFAULT_CONFIG.copy()
                    merged.update({k: v for k, v in data.items() if isinstance(v, str)})
                    return merged
            except Exception:
                pass
        return DEFAULT_CONFIG.copy()


def save_branding_config(logo_url: str, youtube_url: str, nl_prompt: str) -> Dict[str, Any]:
    with _lock:
        payload = {
            "logo_url": logo_url or "",
            "youtube_url": youtube_url or "",
            "nl_prompt": nl_prompt or ""
        }
        _ensure_parent(CONFIG_PATH)
        CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload.copy()
