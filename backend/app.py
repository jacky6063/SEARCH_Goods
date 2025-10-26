# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import re
import json
import time
from pathlib import Path
from fastapi import FastAPI
import logging
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from collections import defaultdict
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import Response
from fastapi import UploadFile, File, Header, HTTPException
import tempfile
import shutil
from datetime import datetime
import subprocess

from goods_search_service import (
    load_data,
    search_products,
    format_for_chat,
    polite_fallback,
    get_catalog_snapshot,
    get_items_by_ids,
    suggest_original_ids,
    suggest_on_sale_related,
    suggest_complementary,
    find_product_by_name,
)
from llm_service import (
    llm_expand_query,
    llm_shorten_20,
    llm_generate_promo,
    llm_rerank_products,
    llm_analyze_query,
    USE_RERANK,
    USE_INTENT,
    USE_PROMO,
    chat_reply,
    classify_recommendation_type,
    llm_generate_plan,
)
import pandas as pd
from config_store import load_branding_config, save_branding_config

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = Path(os.getenv("DATA_PATH", ROOT / "data" / "VIEW_GOODS_enhanced.csv"))


def _detect_git_value(cmd: list[str]) -> Optional[str]:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


BUILD_COMMIT = (
    os.getenv("RENDER_GIT_COMMIT")
    or os.getenv("GIT_COMMIT")
    or os.getenv("NETLIFY_COMMIT_REF")
    or _detect_git_value(["git", "rev-parse", "HEAD"])
    or "unknown"
)

BUILD_BRANCH = (
    os.getenv("RENDER_GIT_BRANCH")
    or os.getenv("GIT_BRANCH")
    or os.getenv("NETLIFY_BRANCH")
    or _detect_git_value(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    or "unknown"
)

BUILD_TIME = os.getenv("RENDER_DEPLOY_CREATED_AT") or datetime.utcnow().isoformat() + "Z"

SESSION_CACHE_TTL = int(os.getenv("CHAT_ALIGNMENT_CACHE_TTL", "600"))
SESSION_ALIGN_CACHE: Dict[str, Dict[str, Any]] = defaultdict(dict)
SUGGEST_CACHE: Dict[str, Dict[str, Any]] = defaultdict(dict)
USE_LLM_RECOMMEND = os.getenv("USE_LLM_RECOMMEND_TYPE", "true").lower() in ("1","true","yes")

AFFIRM_WHITELIST = set([
    "要","好","可以","顯示","看一下","給我看","看","需要","麻煩","是的","沒問題",
    "幫我顯示","幫我看","幫我開","ok","okay","show","yes","y","sure","pls","please","go","go ahead"
])

ALIGN_JSON_RE = re.compile(r"\{.*?\"intent\"\s*:\s*\"product_align\".*?\}\s*$", re.S)


def _cleanup_session_cache(now: Optional[int] = None) -> None:
    now = now or int(time.time())
    expired = [sid for sid, data in SESSION_ALIGN_CACHE.items() if now - data.get("ts", 0) > SESSION_CACHE_TTL]
    for sid in expired:
        SESSION_ALIGN_CACHE.pop(sid, None)
    expired_suggest = [sid for sid, data in SUGGEST_CACHE.items() if now - data.get("ts", 0) > SESSION_CACHE_TTL]
    for sid in expired_suggest:
        SUGGEST_CACHE.pop(sid, None)


def _contains_affirmation(text: str) -> bool:
    if not text:
        return False
    lowered = text.strip().lower()
    if lowered in AFFIRM_WHITELIST:
        return True
    tokens = re.findall(r"[a-zA-Z]+|[\u4e00-\u9fff]+", lowered)
    for token in tokens:
        if token in AFFIRM_WHITELIST:
            return True
    for term in AFFIRM_WHITELIST:
        if term in lowered and len(lowered) <= len(term) + 2:
            return True
    return False


def _sanitize_alignment_items(df: pd.DataFrame, items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    ids = [str((item or {}).get("id") or "").strip() for item in items if str((item or {}).get("id") or "").strip()]
    if not ids:
        return []
    rows = get_items_by_ids(df, ids)
    if not rows:
        return []
    row_map = {str(row.get("GoodIden") or "").strip(): row for row in rows}
    sanitized: List[Dict[str, str]] = []
    for gid in ids:
        row = row_map.get(gid)
        if not row:
            continue
        sanitized.append({
            "id": gid,
            "name": str(row.get("Name") or row.get("商品名稱") or "").strip(),
        })
        if len(sanitized) >= 8:
            break
    return sanitized


def _store_alignment(session_id: str, df: pd.DataFrame, items: List[Dict[str, Any]], now: int, query_terms: Optional[List[str]] = None) -> List[Dict[str, str]]:
    sanitized = _sanitize_alignment_items(df, items)
    if sanitized:
        ids = [entry["id"] for entry in sanitized]
        rows = get_items_by_ids(df, ids)
        SESSION_ALIGN_CACHE[session_id] = {
            "ids": ids,
            "items": sanitized,
            "ts": now,
        }
        SUGGEST_CACHE[session_id] = {
            "align_ids": ids,
            "align_rows": rows,
            "query_terms": query_terms or [],
            "ts": now,
        }
    else:
        SESSION_ALIGN_CACHE.pop(session_id, None)
        SUGGEST_CACHE.pop(session_id, None)
    return sanitized


def _parse_price(row: Dict[str, Any]) -> float:
    price_keys = ["SpecialOffer", "特價", "pric_special", "Price", "價格", "pric"]
    for key in price_keys:
        if key in row:
            value = str(row.get(key) or "").replace(",", "").strip()
            if value:
                try:
                    return float(value)
                except Exception:
                    continue
    return 0.0


class SuggestReq(BaseModel):
    session_id: Optional[str] = None
    type: int = 1


def _build_suggestion(session_id: str, suggestion_type: int, df: pd.DataFrame):
    cache = SUGGEST_CACHE.get(session_id) or {}
    align_ids = cache.get("align_ids") or []
    align_rows = cache.get("align_rows") or []
    query_terms = cache.get("query_terms") or []

    if suggestion_type == 1:
        ids = suggest_original_ids(align_ids)
    elif suggestion_type == 2:
        ids = suggest_on_sale_related(df, query_terms)
    else:
        ids = suggest_complementary(df, align_rows)

    rows = get_items_by_ids(df, ids)
    return ids, rows

app = FastAPI(title="SEARCH_Goods API", version="0.1.0")

# logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("search_goods")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)


@app.on_event("startup")
def _warmup_dataframe():
    try:
        app.state.DATAFRAME = get_df()
    except Exception:
        app.state.DATAFRAME = pd.DataFrame()


class SearchReq(BaseModel):
    query: str = ""
    topn: int = 10
    page: int = 1
    page_size: int = 10
    ids: Optional[List[str]] = None


# lazy load once
_df_cache: Optional[pd.DataFrame] = None
_branding_cache: Dict[str, str] = load_branding_config()


@app.get("/api/branding")
def get_branding():
    return JSONResponse(_branding_cache)


class BrandingReq(BaseModel):
    logo_url: str = ""
    youtube_url: str = ""
    nl_prompt: str = ""


@app.post("/api/branding")
def update_branding(req: BrandingReq):
    global _branding_cache
    updated = save_branding_config(req.logo_url.strip(), req.youtube_url.strip(), req.nl_prompt.strip())
    _branding_cache = updated
    return JSONResponse({"status": "ok", "data": updated})


def get_df():
    global _df_cache
    if _df_cache is None:
        _df_cache = load_data(str(DATA_PATH))
        try:
            app.state.DATAFRAME = _df_cache
        except Exception:
            pass
    return _df_cache


@app.post("/api/search")
def api_search(req: SearchReq):
    df = get_df()
    if req.ids:
        normalized_ids = [str(x).strip() for x in req.ids if str(x or "").strip()]
        if not normalized_ids:
            return JSONResponse({
                "message": "查詢條件不足。",
                "items": [],
                "page": 1,
                "page_size": 0,
                "has_next": False,
                "last_page": 1,
                "intent": {},
            })
        subset = df[df.get("GoodIden").astype(str).isin(normalized_ids)].copy() if "GoodIden" in df.columns else pd.DataFrame()
        records_by_id: Dict[str, Dict[str, Any]] = {}
        if not subset.empty:
            for _, row in subset.iterrows():
                gid = str(row.get("GoodIden") or "").strip()
                if gid:
                    records_by_id[gid] = row.to_dict()
        ordered_records: List[Dict[str, Any]] = []
        for gid in normalized_ids:
            record = records_by_id.get(gid)
            if record:
                ordered_records.append(record)
        items = format_for_chat(ordered_records)
        return JSONResponse({
            "message": f"為您找到 {len(items)} 項商品：",
            "items": items,
            "page": 1,
            "page_size": len(items),
            "has_next": False,
            "last_page": 1,
            "intent": {},
        })

    branding_prompt = (_branding_cache.get("nl_prompt") or "").strip() if isinstance(_branding_cache, dict) else ""
    custom_prompt = branding_prompt or None
    # optional: expand query via LLM stub
    try:
        intent = llm_analyze_query(req.query, system_prompt=custom_prompt)
        expanded = llm_expand_query(req.query, system_prompt=custom_prompt)
    except Exception:
        intent = {}
        expanded = req.query
    page_size = max(1, min(req.page_size or 30, 50))
    page = max(1, req.page or 1)
    base_topn = page_size * page
    candidate_topn = base_topn + page_size
    if USE_RERANK:
        candidate_topn = max(base_topn * 2, base_topn + page_size, base_topn + 20, 60)
    required_terms = intent.get("required_terms") if isinstance(intent, dict) else None
    category_terms = intent.get("category_terms") if isinstance(intent, dict) else None
    excluded_terms = intent.get("excluded_terms") if isinstance(intent, dict) else None
    all_records, _terms = search_products(
        df,
        expanded,
        topn=candidate_topn,
        sort_price=True,
        required_terms=required_terms,
        category_terms=category_terms,
        excluded_terms=excluded_terms,
    )
    total_available = len(all_records)
    if not all_records:
        return JSONResponse({
            "message": polite_fallback(req.query),
            "items": [],
            "page": page,
            "page_size": page_size,
            "has_next": False,
            "last_page": page,
            "intent": intent or {}
        })
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    has_next = total_available > end_idx
    last_page = max(1, (total_available + page_size - 1) // page_size)
    if USE_RERANK:
        reranked = llm_rerank_products(req.query, expanded, all_records, topn=end_idx, system_prompt=custom_prompt)
        records = reranked[start_idx:end_idx]
    else:
        records = all_records[start_idx:end_idx]
    items = format_for_chat(records)
    for it, raw in zip(items, records):
        original_desc = (
            raw.get("ShortDesc_20")
            or raw.get("ShortDesc")
            or raw.get("ShortDesc_10")
            or raw.get("DESCRIPTION")
            or raw.get("Description")
            or raw.get("REMARK")
            or raw.get("備註")
            or ""
        )
        if USE_PROMO:
            try:
                marketing = llm_generate_promo(it.get("商品名稱", ""), original_desc)
                if marketing:
                    it["商品描述"] = marketing
                elif not it.get("商品描述") and original_desc:
                    it["商品描述"] = original_desc
            except Exception:
                pass
        if not it.get("商品描述"):
            if original_desc:
                it["商品描述"] = original_desc
            else:
                try:
                    it["商品描述"] = llm_shorten_20(it.get("商品名稱", ""))
                except Exception:
                    it["商品描述"] = it.get("商品名稱", "")[:60]
    return JSONResponse({
        "message": f"為您找到 {len(items)} 項商品：",
        "items": items,
        "page": page,
        "page_size": page_size,
        "has_next": has_next,
        "last_page": last_page,
        "intent": intent or {}
    })


# -------------------- Chat API --------------------
class ChatReq(BaseModel):
    message: str
    history: List[Dict[str, Any]] = []
    topn: int = 8
    session_id: Optional[str] = None


class ChatResp(BaseModel):
    reply: str
    action: Optional[Dict[str, Any]] = None
    alignment: Optional[Dict[str, Any]] = None
    auto_suggest: Optional[Dict[str, Any]] = None
    items: Optional[List[Dict[str, Any]]] = None
    meta: Optional[Dict[str, Any]] = None


# 舊的 chat 端點已移除，功能已移至 chat_router_goods_action.py 以避免路由衝突


@app.post("/api/suggest")
def suggest_endpoint(req: SuggestReq):
    session_id = str(req.session_id or "default")
    suggestion_type = int(req.type or 1)
    now = int(time.time())
    _cleanup_session_cache(now)
    df = get_df()
    ids, rows = _build_suggestion(session_id, suggestion_type, df)
    if not rows:
        return {"mode": "chat", "items": []}
    return {
        "mode": "render",
        "items": format_for_chat(rows),
        "ids": ids,
        "message": f"為您準備 {len(rows)} 項商品建議",
    }


@app.get("/api/version")
def api_version():
    short_commit = BUILD_COMMIT[:7] if BUILD_COMMIT not in (None, "unknown") else BUILD_COMMIT
    return JSONResponse({
        "commit": BUILD_COMMIT,
        "short_commit": short_commit,
        "branch": BUILD_BRANCH,
        "built_at": BUILD_TIME,
    })


@app.get("/health")
def health():
    """Simple health-check endpoint for load balancers/containers."""
    return JSONResponse({"status": "ok"})


# --- Admin endpoints: protected by ADMIN_TOKEN env var (simple token auth)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
# allow bypass in development when ALLOW_DEV_ADMIN is set (1/true)
ALLOW_DEV_ADMIN = os.getenv("ALLOW_DEV_ADMIN", "false").lower() in ("1", "true", "yes")


def _check_admin(token: Optional[str]):
    # development bypass
    if ALLOW_DEV_ADMIN:
        return
    if not ADMIN_TOKEN:
        # no admin token configured -> disallow admin endpoints in production
        raise HTTPException(status_code=403, detail="admin endpoints disabled")
    if not token or token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


@app.post("/api/admin/clear-cache")
def admin_clear_cache(request: Request, x_admin_token: Optional[str] = Header(None)):
    """Clear the in-memory DataFrame cache so the next request reloads CSV."""
    _check_admin(x_admin_token)
    global _df_cache
    _df_cache = None
    SESSION_ALIGN_CACHE.clear()
    SUGGEST_CACHE.clear()
    try:
        app.state.DATAFRAME = get_df()
    except Exception:
        app.state.DATAFRAME = pd.DataFrame()
    client = getattr(request, "client", None)
    client_ip = client.host if client else "unknown"
    logger.info("cache cleared requested by %s", client_ip)
    return JSONResponse({"status": "ok", "message": "cache cleared"})


@app.post("/api/admin/upload-csv")
def admin_upload_csv(request: Request, file: UploadFile = File(...), x_admin_token: Optional[str] = Header(None)):
    """Upload a CSV file and atomically replace `DATA_PATH`. Requires ADMIN_TOKEN.

    The uploaded file is written to a temp file in the same directory as
    DATA_PATH and then moved into place using os.replace to ensure atomicity.
    After replace the in-memory cache `_df_cache` is cleared so new requests
    will reload the CSV.
    """
    _check_admin(x_admin_token)
    dst = DATA_PATH
    dst.parent.mkdir(parents=True, exist_ok=True)
    # write to temp file in same dir to guarantee os.replace atomicity
    with tempfile.NamedTemporaryFile(delete=False, dir=str(dst.parent)) as tmp:
        tmp_path = tmp.name
        shutil.copyfileobj(file.file, tmp)

    # basic validation: not empty
    if os.path.getsize(tmp_path) == 0:
        os.unlink(tmp_path)
        raise HTTPException(status_code=400, detail="uploaded file is empty")
    try:
        size = os.path.getsize(tmp_path)
        client = getattr(request, "client", None)
        client_ip = client.host if client else "unknown"
        logger.info("received upload from %s size=%d -> %s", client_ip, size, dst)
        os.replace(tmp_path, str(dst))
        # clear cache
        global _df_cache
        _df_cache = None
        logger.info("replaced data file at %s and cleared cache", dst)
        return JSONResponse({"status": "ok", "message": "uploaded and replaced csv"})
    except Exception as exc:
        logger.exception("error processing uploaded csv: %s", exc)
        # attempt cleanup
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="internal error processing upload")


# serve frontend static files (SPA fallback)
frontend_path = ROOT / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")

# Optional: fallback for unknown paths to serve index.html (helps SPA routing)
@app.middleware("http")
async def spa_fallback(request: Request, call_next):
    # let API routes pass through
    if request.url.path.startswith("/api") or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi.json"):
        return await call_next(request)
    # try to serve static file; StaticFiles with html=True already serves index.html for '/'
    resp = await call_next(request)
    # if StaticFiles returned 404 or similar, serve index.html for client-side routing
    if resp.status_code in (404, 405):
        index_path = frontend_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
    return resp

# ---- Hotfix K1+K2: chat router integration completed in main app ----
# The enhanced chat functionality from chat_router_k1_k2 has been integrated
# into the main chat_endpoint function above

# ---- Mount promo40 router (40字宣傳文) ----
from promo_router_40 import router as promo_router_40
app.include_router(promo_router_40)

# ---- goods_1024001: attach search router with promo ----
from search_router_goods_1024001 import router as search_router_goods_1024001
app.include_router(search_router_goods_1024001)

# ---- goods_1024001: 舊的 chat 路由器已移除以避免與 chat_router_goods_action 衝突 ----

# ---- goods_action: 直接在主 app 定義 chat 端點 ----
from chat_router_goods_action import chat_handler, ChatReq, ChatResponse, get_chat_result_by_session

@app.post("/api/chat")
def chat_endpoint(req: ChatReq):
    """Chat endpoint - 直接調用 chat_handler 並回傳原始結果"""
    try:
        result = chat_handler(req)
        # 如果是 dict，直接回傳，FastAPI 會自動序列化
        return result
    except Exception as e:
        return {
            "ok": False,
            "reply": "抱歉，目前聊天服務暫時無法回應，稍後再試。",
            "error": str(e)
        }

# ---- 新增會話結果檢索 endpoint ----
@app.get("/api/chat-session/{session_id}")
def get_chat_session(session_id: str):
    """根據會話 ID 獲取聊天結果"""
    result = get_chat_result_by_session(session_id)
    if result:
        return JSONResponse({"ok": True, "result": result})
    else:
        return JSONResponse({"ok": False, "error": "Session not found or expired"})
