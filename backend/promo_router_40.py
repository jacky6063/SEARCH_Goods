from typing import Optional
import os, re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.llm_client import get_openai_client

router = APIRouter()

# ---- 入參資料模型 ----
class PromoReq(BaseModel):
    good_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    brand: Optional[str] = None
    spec: Optional[str] = None

# ---- 簡單字數截斷（全形字為主，保守以 40 字為上限）----
def clamp_zh(s: str, n: int = 40) -> str:
    s = re.sub(r"\s+", "", s or "")
    return s[:n]

# ---- 規則式 fallback（無 OPENAI_API_KEY 時仍可用）----
def rule_based_promo(name: str, description: Optional[str], spec: Optional[str]) -> str:
    # 擷取關鍵詞
    keys = []
    src = f"{name}{description or ''}{spec or ''}"
    for kw in ["無添加","無香料","無色素","低負擔","高纖","穀物","酥脆","清爽","果香","天然","嚴選","健康","能量","早餐","即沖即食"]:
        if kw in src and kw not in keys:
            keys.append(kw)
    # 組句（避免重複品牌/品名）
    base = f"{'、'.join(keys) or '果香酥脆'}，美味輕盈好開啟每個早晨。"
    return clamp_zh(base, 40)

# ---- OpenAI 生成（若環境有 OPENAI_API_KEY 才啟用）----
def llm_promo_zh_40(name: str, description: Optional[str], brand: Optional[str], spec: Optional[str]) -> str:
    client = get_openai_client()
    if not client:
        return None  # 交由 fallback
    try:
        model = os.getenv("OPENAI_MODEL", os.getenv("CHAT_MODEL", "gpt-4o-mini"))
        prompt = f"""
你是台灣行銷文案。請用繁體中文，為下列商品寫「40字以內」宣傳短文：
- 商品名稱：{name}
- 規格：{spec or ''}
- 描述重點：{(description or '')[:200]}
限制：
1) 不要出現品牌名與商品全名重複。
2) 用語自然、可口、健康形象，避免誇大與醫療功效。
3) 40字以內，一句話完成。
只輸出文案本身。
""".strip()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"user","content":prompt}],
            temperature=float(os.getenv("PROMO40_TEMPERATURE","0.5")),
            max_tokens=80,
        )
        text = (resp.choices[0].message.content or "").strip()
        return clamp_zh(text, 40) if text else None
    except Exception:
        return None

@router.post("/api/promo40")
def make_promo(req: PromoReq):
    if not req.name:
        raise HTTPException(status_code=400, detail="name required")
    text = llm_promo_zh_40(req.name, req.description, req.brand, req.spec)
    if not text:
        text = rule_based_promo(req.name, req.description, req.spec)
    return {"ok": True, "promo": text}

@router.get("/api/promo40/sample")
def sample():
    demo = PromoReq(name="米森覆盆莓麥片/400g", description="覆盆莓果香、層層穀物酥脆、無添加香料色素，早餐即沖即食")
    return make_promo(demo)
