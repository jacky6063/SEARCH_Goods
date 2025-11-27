import os, re
from functools import lru_cache
from typing import Optional, Dict, Any
from field_utils import FieldAccessor
from services.llm_client import get_openai_client

def _clamp_zh(s: str, n: int = 40) -> str:
    s = re.sub(r"\s+", "", s or "")
    return s[:n]

def _rule_based(name: str, description: Optional[str], spec: Optional[str]) -> str:
    keys = []
    src = f"{name}{description or ''}{spec or ''}"
    for kw in ["無添加","無香料","無色素","低負擔","高纖","穀物","酥脆","清爽","果香","天然","嚴選","健康","能量","早餐","即沖即食"]:
        if kw in src and kw not in keys:
            keys.append(kw)
    base = f"{'、'.join(keys) or '果香酥脆'}，美味輕盈好開啟每個早晨。"
    return _clamp_zh(base, 40)

def _try_llm(name: str, description: Optional[str], brand: Optional[str], spec: Optional[str]) -> Optional[str]:
    client = get_openai_client()
    if not client:
        return None
    try:
        model = os.getenv("OPENAI_MODEL", os.getenv("CHAT_MODEL", "gpt-4o-mini"))
        prompt = f"""你是台灣行銷文案。用繁體中文，為下列商品寫「40字以內」宣傳短文：
- 名稱：{name}
- 規格：{spec or ''}
- 描述重點：{(description or '')[:200]}
限制：不要重複品牌或全名；自然健康、美味形象；40字內，一句話；只輸出文案本身。"""
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"user","content":prompt}],
            temperature=float(os.getenv("PROMO40_TEMPERATURE","0.5")),
            max_tokens=80,
        )
        text = (resp.choices[0].message.content or "").strip()
        return _clamp_zh(text, 40) if text else None
    except Exception:
        return None

def _item_texts(item: Dict[str, Any]):
    """使用統一的欄位存取器獲取商品資訊"""
    name = FieldAccessor.get_name(item)
    desc = FieldAccessor.get_description(item)
    spec = FieldAccessor.get_size(item)
    brand = FieldAccessor.get_brand(item)
    return name, desc, brand, spec

@lru_cache(maxsize=8192)
def get_promo_text_cache(key: str, name: str, desc: str, brand: str, spec: str) -> str:
    text = _try_llm(name, desc, brand, spec)
    if not text:
        text = _rule_based(name, desc, spec)
    return text

def get_promo_text(item: Dict[str, Any]) -> str:
    name, desc, brand, spec = _item_texts(item)
    key = FieldAccessor.get_product_id(item) or name
    return get_promo_text_cache(str(key)[:128], name, desc, brand, spec)
