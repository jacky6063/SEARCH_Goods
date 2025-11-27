from __future__ import annotations

import json
from pathlib import Path
from typing import List

_CONFIG_ROOT = Path(__file__).resolve().parent
_NEGATIVE_KEYWORDS_PATH = _CONFIG_ROOT / "negative_keywords.json"


def _load_negative_keywords() -> List[str]:
    try:
        data = json.loads(_NEGATIVE_KEYWORDS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
    except FileNotFoundError:
        return []
    except Exception as exc:
        print(f"[WARN] Failed to load negative keywords: {exc}")
    return []


negative_keywords = _load_negative_keywords()

__all__ = ["negative_keywords"]
