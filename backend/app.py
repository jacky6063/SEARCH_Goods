# -*- coding: utf-8 -*-
"""
================================================================================
SEARCH_Goods 系統 - 主應用程式
================================================================================

檔案名稱: app.py
撰寫日期: 2025年11月5日
撰寫時間: 15:00-17:30
撰寫模型: GitHub Copilot (Claude 3.5 Sonnet)
最後更新: 2025年11月5日 17:30

功能描述:
    FastAPI 主應用程式，提供產品搜尋、聊天、推薦等 API 端點
    包含行政管理功能、會話管理、快取管理

核心功能:
    - 產品搜尋 API (/api/search)
    - 聊天介面 API (/api/chat)
    - 產品推薦 API (/api/suggest)
    - 行政管理端點 (/api/admin/*)
    - 靜態文件服務 (SPA 支援)

================================================================================
"""
from __future__ import annotations
import asyncio
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
from fastapi import UploadFile, File, Header, HTTPException, Form, Query
import ipaddress
import tempfile
import shutil
from datetime import datetime
import subprocess
from constants import (
    COLUMN_MAPPING,
    get_column_names,
    get_all_column_variants,
    get_hierarchy_columns,
    validate_hierarchy_levels,
)
from goods_search_service import (
    search_products,
    format_for_chat,
    polite_fallback,
    get_items_by_ids,
    suggest_original_ids,
    suggest_on_sale_related,
    suggest_complementary,
    find_product_by_name,
    load_goods_rows,
)
from field_utils import FieldAccessor
from llm_service import (
    llm_expand_query,
    llm_shorten_20,
    llm_generate_promo,
    llm_rerank_products,
    llm_analyze_query,
    llm_clarify_or_confirm,
    USE_RERANK,
    USE_INTENT,
    USE_PROMO,
    SEARCH_USE_EXPAND,
    SEARCH_USE_RERANK,
    SEARCH_USE_INTENT,
    SEARCH_USE_PROMO,
    chat_reply,
    classify_recommendation_type,
    llm_generate_plan,
)
import pandas as pd
import config_store
from config_store import load_branding_config, save_branding_config
from services import bundle_service, catalog_service
from services import categories_service
from services.search_service import (
    is_negative_query,
    filter_low_confidence_products,
    NEGATIVE_QUERY_MESSAGE,
    LOW_CONFIDENCE_MESSAGE,
    MIN_CONFIDENCE_SCORE,
)
from utils.logging_utils import configure_structured_logging, get_logger
from services.categories_service import get_diagnostics as get_categories_diag
from chat_logging_bridge import ChatLoggingBridge
from supabase_client import get_supabase_client, SupabaseConfigError

# 先載入環境變數（優先載入 .env.dev，其次 .env）
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env.dev")
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

ROOT = Path(__file__).resolve().parents[1]
__path__ = [str(Path(__file__).resolve().parent)]
if "__spec__" in globals() and __spec__ is not None:
    __spec__.submodule_search_locations = __path__
from app.services.content_engine import generate_content

# 🆕 維修服務導入（條件性啟用）
ENABLE_REPAIR_SERVICE = os.getenv("ENABLE_REPAIR_SERVICE", "False").lower() in ("1", "true", "yes")
import sys
sys.stderr.write(f"[DEBUG] ENABLE_REPAIR_SERVICE ENV = '{os.getenv('ENABLE_REPAIR_SERVICE')}'\n")
sys.stderr.write(f"[DEBUG] ENABLE_REPAIR_SERVICE = {ENABLE_REPAIR_SERVICE}\n")
sys.stderr.flush()
if ENABLE_REPAIR_SERVICE:
    try:
        from repair_search_service import (
            search_repairs,
            format_for_chat as format_repairs_for_chat,
            load_repair_data,
        )
        from repair_llm_service import (
            repair_chat_reply,
            repair_expand_query,
            repair_analyze_query,
            _get_repair_client,
            REPAIR_OPENAI_MODEL,
        )
        sys.stderr.write("[INFO] 維修服務模組載入成功 ✅\n")
        sys.stderr.flush()
    except ImportError as e:
        sys.stderr.write(f"[WARN] 維修服務模組載入失敗: {e}\n")
        sys.stderr.flush()
        ENABLE_REPAIR_SERVICE = False

# 使用集中式路徑管理器（替代重複的 _get_csv_path 邏輯）
from path_manager import GOODS_DATA_PATH as DATA_PATH


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

# ============================================================
# 分頁設定（從環境變數讀取）
# ============================================================
DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "30"))
HOT_CATEGORY_PAGE_SIZE = int(os.getenv("HOT_CATEGORY_PAGE_SIZE", "6"))

SESSION_CACHE_TTL = int(os.getenv("CHAT_ALIGNMENT_CACHE_TTL", "600"))
SESSION_ALIGN_CACHE: Dict[str, Dict[str, Any]] = defaultdict(dict)
bundle_service.set_ttl(SESSION_CACHE_TTL)
# 強制啟用 LLM 功能以確保一律透過 LLM 互動
USE_CHAT_MODE_FORCED = True  # 強制啟用聊天模式
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
    bundle_service.cleanup(now)


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

# ==================== 情緒分析（簡易版） ====================
EMOTION_THRESHOLDS = {"anxiety": 7, "urgency": 8, "anger": 6}
URGENCY_KEYWORDS = ["瓦斯", "洩漏", "緊急", "馬上", "立刻", "火災", "爆炸", "危險", "漏水"]
ANGER_KEYWORDS = ["太慢", "不滿", "抱怨", "投訴", "太差", "扯"]
ANXIETY_KEYWORDS = ["害怕", "擔心", "怎麼辦", "恐慌", "崩潰"]


def analyze_user_emotion(message: str) -> Optional[Dict[str, Any]]:
    """
    情緒分析：
    1) 優先使用 LLM (REPAIR_OPENAI_MODEL)，回傳 JSON。
    2) 若 LLM 不可用則使用關鍵字規則。
    達到閾值才回傳，否則回傳 None。
    """
    if not message:
        return None

    # --- 優先用 LLM ---
    try:
        client = _get_repair_client() if "_get_repair_client" in globals() else None
        if client:
            system_prompt = """你是一個住宅維修客服的情緒分析助手，請針對使用者訊息評分：
- anxiety_level: 0-10（不安/焦慮）
- urgency_level: 0-10（急迫/危險）
- anger_level: 0-10（生氣/不滿）
回傳 JSON，不要多餘文字。"""
            user_prompt = f"請分析以下訊息的情緒分數（0-10）：\n「{message}」"
            resp = client.chat.completions.create(
                model=REPAIR_OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content
            parsed = json.loads(raw) if raw else {}
            anxiety = int(parsed.get("anxiety_level", 0) or 0)
            urgency = int(parsed.get("urgency_level", 0) or 0)
            anger = int(parsed.get("anger_level", 0) or 0)
            keywords = parsed.get("keywords") or []
            reasoning = parsed.get("reasoning") or "LLM 判斷"

            if anxiety < EMOTION_THRESHOLDS["anxiety"] and urgency < EMOTION_THRESHOLDS["urgency"] and anger < EMOTION_THRESHOLDS["anger"]:
                return None

            analyzed_at = datetime.utcnow().isoformat() + "Z"
            return {
                "anxiety_level": anxiety,
                "urgency_level": urgency,
                "anger_level": anger,
                "keywords": keywords,
                "reasoning": reasoning,
                "analyzed_at": analyzed_at,
                "trigger_threshold": EMOTION_THRESHOLDS,
                "config_version": "llm-repair",
            }
    except Exception as exc:
        logger.warning(f"[Emotion] LLM analysis failed, fallback to rule-based: {exc}")

    # --- 後備：關鍵字規則 ---
    text = message.lower()
    anxiety = 0
    urgency = 0
    anger = 0
    keywords: List[str] = []

    for kw in URGENCY_KEYWORDS:
        if kw.lower() in text:
            urgency = max(urgency, 8)
            keywords.append(kw)
    for kw in ANXIETY_KEYWORDS:
        if kw.lower() in text:
            anxiety = max(anxiety, 7)
            keywords.append(kw)
    for kw in ANGER_KEYWORDS:
        if kw.lower() in text:
            anger = max(anger, 7)
            keywords.append(kw)

    if "!" in message or "！" in message:
        urgency = max(urgency, 9)
    if "??" in message or "？" in message:
        anxiety = max(anxiety, 7)

    if urgency == 0 and any(word in text for word in ["快", "立即", "現在"]):
        urgency = 6
    if anxiety == 0 and any(word in text for word in ["怕", "慌"]):
        anxiety = 6

    if anxiety < EMOTION_THRESHOLDS["anxiety"] and urgency < EMOTION_THRESHOLDS["urgency"] and anger < EMOTION_THRESHOLDS["anger"]:
        return None

    analyzed_at = datetime.utcnow().isoformat() + "Z"
    return {
        "anxiety_level": anxiety,
        "urgency_level": urgency,
        "anger_level": anger,
        "keywords": keywords,
        "reasoning": "關鍵字與語氣判斷",
        "analyzed_at": analyzed_at,
        "trigger_threshold": EMOTION_THRESHOLDS,
        "config_version": "rule-fallback",
    }


def persist_emotion_result(message_record: Optional[Dict[str, Any]], session_id: Optional[str], emotion_data: Dict[str, Any]) -> None:
    """將情緒結果寫回 chat_messages.emotion_data 並插入 emotion_analysis。"""
    if not emotion_data or not message_record:
        return
    message_id = message_record.get("message_id") or message_record.get("id")
    if not message_id:
        return
    try:
        client = get_supabase_client(prefer_service_role=True)
    except SupabaseConfigError as exc:
        logger.warning(f"[Emotion] Supabase config missing: {exc}")
        return
    try:
        # 先以 message_id 欄位更新，若 schema 為 id 則再嘗試一次
        updated = client.table("chat_messages").update({"emotion_data": emotion_data}).eq("message_id", message_id).execute()
        if not updated.data:
            client.table("chat_messages").update({"emotion_data": emotion_data}).eq("id", message_id).execute()
    except Exception as exc:
        logger.warning(f"[Emotion] Failed to update chat_messages.emotion_data: {exc}")
    try:
        client.table("emotion_analysis").insert({
            "message_id": message_id,
            "session_id": session_id,
            "anxiety_level": emotion_data.get("anxiety_level"),
            "urgency_level": emotion_data.get("urgency_level"),
            "anger_level": emotion_data.get("anger_level"),
            "keywords": emotion_data.get("keywords") or [],
            "reasoning": emotion_data.get("reasoning"),
            "analyzed_at": emotion_data.get("analyzed_at"),
            "config_version": emotion_data.get("config_version"),
        }).execute()
    except Exception as exc:
        logger.warning(f"[Emotion] Failed to insert emotion_analysis: {exc}")


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
            "name": FieldAccessor.get_name(row),
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
        bundle_service.save_bundle(session_id, {
            "align_ids": ids,
            "align_rows": rows,
            "query_terms": query_terms or [],
            "ts": now,
        })
    else:
        SESSION_ALIGN_CACHE.pop(session_id, None)
        bundle_service.delete_bundle(session_id)
    return sanitized


def _parse_price(row: Dict[str, Any]) -> float:
    price = FieldAccessor.get_price(row)
    return float(price) if price else 0.0


class SuggestReq(BaseModel):
    session_id: Optional[str] = None
    type: int = 1


def _extract_ids_from_items(items: List[Dict[str, Any]]) -> List[str]:
    ids: List[str] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        # 使用 FieldAccessor 優先取得商品編號
        if "商品編號" in item:
            val = item.get("商品編號")
        else:
            val = FieldAccessor.get_product_id(item)
        
        if not val:
            continue
        ident = str(val).strip()
        if ident:
            ids.append(ident)
    return ids


def _filter_on_sale(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        special = (
            item.get("商品特價")
            or item.get("SpecialOffer")
            or item.get("special")
            or item.get("特價")
        )
        if special in (None, "", 0, "0"):
            continue
        try:
            numeric = float(str(special).replace(",", "").strip())
            if numeric <= 0:
                continue
        except Exception:
            pass
        filtered.append(item)
    return filtered


def _build_suggestion(session_id: str, suggestion_type: int, df: pd.DataFrame):
    cache = bundle_service.get_bundle(session_id) or {}
    align_ids = cache.get("align_ids") or []
    align_rows = cache.get("align_rows") or []
    query_terms = cache.get("query_terms") or []
    structured_items = cache.get("structured_items") or []
    structured_summary = cache.get("structured_summary") or ""

    if suggestion_type == 1:
        if structured_items:
            ids = _extract_ids_from_items(structured_items) or align_ids
            rows = structured_items
            return ids, rows, structured_summary or f"為您準備 {len(rows)} 項商品建議"
        ids = suggest_original_ids(align_ids)
    elif suggestion_type == 2:
        sale_items = _filter_on_sale(structured_items)
        if sale_items:
            ids = _extract_ids_from_items(sale_items)
            rows = sale_items
            return ids, rows, f"為您準備 {len(rows)} 項特價商品推薦"
        ids = suggest_on_sale_related(df, query_terms)
    else:
        ids = suggest_complementary(df, align_rows)

    rows = get_items_by_ids(df, ids)
    if not rows and structured_items:
        rows = structured_items
        if not ids:
            ids = _extract_ids_from_items(structured_items)
    
    # 🔧 修正：當沒有任何商品資料時，提示用戶重新開始聊天
    if not rows and not ids:
        return [], [], "請重新開始聊天以獲得個人化的商品建議"
    
    summary = structured_summary or f"為您準備 {len(rows)} 項商品建議"
    return ids, rows, summary


SUGGESTION_VIEW_MAP = {
    "original": 1,
    "default": 1,
    "sale": 2,
    "onsale": 2,
    "on_sale": 2,
    "deal": 2,
    "complementary": 3,
    "bundle": 3,
    "mix": 3,
}

SUGGESTION_TYPE_LABEL = {
    1: "original",
    2: "sale",
    3: "complementary",
}


def _render_bundle_response(session_id: str, suggestion_type: int) -> Dict[str, Any]:
    now = int(time.time())
    bundle_service.cleanup(now)
    _cleanup_session_cache(now)
    df = get_df()

    ids, rows, summary = _build_suggestion(session_id, suggestion_type, df)
    if not rows:
        return {
            "status": "expired",
            "bundle_id": session_id,
            "suggestion_type": suggestion_type,
            "mode": "chat",
            "items": [],
            "products": [],
            "message": summary or "請先進行聊天以獲得個人化的商品建議",
            "assistant_reply": summary or "請先進行聊天以獲得個人化的商品建議",
        }

    items: List[Dict[str, Any]] = []
    products: List[Dict[str, Any]] = []

    for row in rows:
        if isinstance(row, dict):
            if "商品名稱" in row:
                # 已格式化的聊天回應格式
                items.append({
                    "商品編號": row.get("商品編號", ""),
                    "商品名稱": row.get("商品名稱", ""),
                    "商品描述": row.get("商品描述", ""),
                    "商品價格": row.get("商品價格", ""),
                    "商品特價": row.get("商品特價", ""),
                    "商品購物網址": row.get("商品購物網址", ""),
                    "商品圖片網址": row.get("商品圖片網址", ""),
                })
                products.append({
                    "id": row.get("商品編號", ""),
                    "name": row.get("商品名稱", ""),
                    "price": str(row.get("商品價格", "")),
                    "special_price": str(row.get("商品特價", "")),
                    "description": row.get("商品描述", ""),
                    "image_url": row.get("商品圖片網址", ""),
                    "shop_url": row.get("商品購物網址", ""),
                })
            else:
                # 原始 CSV 格式，使用 FieldAccessor 統一轉換
                desc = (
                    row.get("ShortDesc_20") or row.get("ShortDesc")
                    or row.get("ShortDesc_10") or FieldAccessor.get_description(row)
                    or row.get("REMARK") or row.get("備註") or ""
                )
                product_id = FieldAccessor.get_product_id(row)
                product_name = FieldAccessor.get_name(row)
                price = FieldAccessor.get_price(row)
                special_price = FieldAccessor.get_special_price(row)
                image_url = FieldAccessor.get_image_url(row)
                shop_url = FieldAccessor.get_shop_url(row)
                
                items.append({
                    "商品編號": product_id,
                    "商品名稱": product_name,
                    "商品描述": desc,
                    "商品價格": price or "",
                    "商品特價": special_price or "",
                    "商品購物網址": shop_url,
                    "商品圖片網址": image_url,
                })
                products.append({
                    "id": product_id,
                    "name": product_name,
                    "price": str(price or ""),
                    "special_price": str(special_price or ""),
                    "description": desc,
                    "image_url": image_url,
                    "shop_url": shop_url,
                })

    return {
        "status": "ok",
        "bundle_id": session_id,
        "mode": "render",
        "ids": ids,
        "items": items,
        "products": products,
        "message": summary or f"為您準備 {len(rows)} 項商品建議",
        "assistant_reply": summary or f"為您準備 {len(rows)} 項商品建議",
        "suggestion_type": suggestion_type,
    }

app = FastAPI(title="SEARCH_Goods API", version="0.1.0")

# 🆕 P0.3: TTL 快取層（分類查詢結果快取）
from collections import OrderedDict

class TTLCache:
    """簡易 TTL 快取實現，使用 LRU 淘汰策略"""
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 180):
        self.cache: OrderedDict = OrderedDict()
        self.ttl = ttl_seconds
        self.max_size = max_size
    
    def get(self, key: str):
        """取得快取值，若過期則刪除並返回 None"""
        if key in self.cache:
            value, expire_time = self.cache[key]
            if time.time() < expire_time:
                # 將項目移到最後（LRU）
                self.cache.move_to_end(key)
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value):
        """設定快取值，若超過上限則移除最舊項目"""
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)  # 移除最舊項目
        self.cache[key] = (value, time.time() + self.ttl)
    
    def clear(self):
        """清空所有快取"""
        self.cache.clear()

# 初始化分類快取
_category_cache = TTLCache(
    max_size=int(os.getenv("CATEGORY_CACHE_SIZE", "2000")),
    ttl_seconds=int(os.getenv("CATEGORY_CACHE_TTL", "180"))
)

# 🆕 P1.1: 分類索引預建（O(1) 快速查詢）
_category_index = {
    "L1": {},
    "L2": {},
    "L3": {}
}

def _build_category_index(df: pd.DataFrame):
    """構建分類索引：normalized 名稱 → 行索引集合
    
    用途：優化分類過濾速度，使用 O(1) 查找代替 O(n) 掃描
    """
    idx = {"L1": {}, "L2": {}, "L3": {}}
    
    for level, col_name in [
        ("L1", "CateName_L1"),
        ("L2", "CateName_L2"),
        ("L3", "CateName_L3")
    ]:
        if col_name not in df.columns:
            continue
        
        for row_idx, val in enumerate(df[col_name]):
            normalized = _record_text(val).lower().strip()
            if normalized:
                if normalized not in idx[level]:
                    idx[level][normalized] = set()
                idx[level][normalized].add(row_idx)
    
    return idx

# logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
configure_structured_logging(LOG_LEVEL)
logger = get_logger("search_goods")

REPAIR_LOGGING_BRIDGE = ChatLoggingBridge(
    module_type="repair",
    channel="repair_chat_api",
    logger=logger,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)


@app.on_event("startup")
def _warmup_dataframe():
    """程式啟動時初始化，記錄模型配置和功能狀態"""
    logger.info("=" * 80)
    logger.info("🚀 SEARCH_Goods 系統啟動")
    logger.info("=" * 80)
    
    # 記錄搜尋模型配置
    logger.info("📊 搜尋模型配置:")
    logger.info(f"  - 模型: {os.getenv('SEARCH_OPENAI_MODEL', os.getenv('OPENAI_MODEL', 'gpt-4o-mini'))}")
    logger.info(f"  - 查詢擴展 (LLM_EXPAND): {os.getenv('SEARCH_USE_LLM_EXPAND', os.getenv('USE_LLM_EXPAND', 'False'))}")
    logger.info(f"  - 意圖分析 (LLM_INTENT): {os.getenv('SEARCH_USE_LLM_INTENT', os.getenv('USE_LLM_INTENT', 'False'))}")
    logger.info(f"  - 結果重排 (LLM_RERANK): {os.getenv('SEARCH_USE_LLM_RERANK', os.getenv('USE_LLM_RERANK', 'False'))}")
    
    # 記錄聊天模型配置
    logger.info("💬 聊天模型配置:")
    logger.info(f"  - 模型: {os.getenv('CHAT_OPENAI_MODEL', os.getenv('CHAT_MODEL', os.getenv('OPENAI_MODEL', 'gpt-4o-mini')))}")
    logger.info(f"  - 查詢擴展 (LLM_EXPAND): {os.getenv('CHAT_USE_LLM_EXPAND', os.getenv('USE_LLM_EXPAND', 'True'))}")
    logger.info(f"  - 意圖分析 (LLM_INTENT): {os.getenv('CHAT_USE_LLM_INTENT', os.getenv('USE_LLM_INTENT', 'True'))}")
    logger.info(f"  - 行銷推廣 (LLM_PROMO): {os.getenv('CHAT_USE_LLM_PROMO', os.getenv('USE_LLM_PROMO', 'True'))}")
    
    # 🆕 P0.3: 記錄快取配置
    logger.info("💾 P0.3 快取配置:")
    logger.info(f"  - 分類快取 TTL: {os.getenv('CATEGORY_CACHE_TTL', '180')} 秒")
    logger.info(f"  - 分類快取大小: {os.getenv('CATEGORY_CACHE_SIZE', '2000')} 項")
    
    logger.info("=" * 80)
    
    try:
        app.state.DATAFRAME = get_df()
    except Exception:
        app.state.DATAFRAME = pd.DataFrame()
    
    # 🆕 P1.1: 構建分類索引（啟動時一次性構建）
    global _category_index
    try:
        df = app.state.DATAFRAME
        if not df.empty:
            _category_index = _build_category_index(df)
            idx_size_l1 = len(_category_index.get("L1", {}))
            idx_size_l2 = len(_category_index.get("L2", {}))
            idx_size_l3 = len(_category_index.get("L3", {}))
            logger.info("🔍 [P1.1] 分類索引已構建:")
            logger.info(f"  - L1 分類數: {idx_size_l1}")
            logger.info(f"  - L2 分類數: {idx_size_l2}")
            logger.info(f"  - L3 分類數: {idx_size_l3}")
    except Exception as e:
        logger.warning(f"  ⚠️ 分類索引構建失敗: {e}")
    
    # 🆕 載入公司簡介服務
    logger.info("🏢 載入公司簡介服務...")
    try:
        from company_profile_service import init_company_profile_service
        from pathlib import Path
        
        json_path = ROOT / "data" / "company_profiles" / "company_profile_chuanchi.jsonl"
        
        if json_path.exists():
            success = init_company_profile_service(json_path)
            if success:
                logger.info("  ✅ 公司簡介服務載入成功")
            else:
                logger.warning("  ⚠️ 公司簡介服務載入失敗")
        else:
            logger.warning(f"  ⚠️ 公司簡介檔案不存在: {json_path}")
    except ImportError:
        logger.warning("  ⚠️ 公司簡介模組未安裝")
    except Exception as e:
        logger.error(f"  ❌ 載入公司簡介服務時發生錯誤: {e}")


class SearchReq(BaseModel):
    query: str = ""
    topn: int = 10
    page: int = 1
    page_size: int = 10
    ids: Optional[List[str]] = None
    category_hierarchy: Optional[Dict[str, str]] = None
    prefer_special_first: Optional[bool] = False
    from_hot_category: Optional[bool] = False  # 🆕 標誌：來自熱門分類 UI (L3 直接過濾)
    disable_rerank: Optional[bool] = False     # 🆕 P0.2: 禁用 LLM 重排
    disable_promo: Optional[bool] = False      # 🆕 P0.2: 禁用宣傳文生成


# lazy load once
_branding_cache: Dict[str, str] = load_branding_config()


@app.get("/api/branding")
def get_branding():
    return JSONResponse(_branding_cache)


class BrandingReq(BaseModel):
    logo_url: str = ""
    youtube_url: str = ""
    nl_prompt: str = ""
    voice_mode_enabled: bool = False


@app.post("/api/branding")
def update_branding(req: BrandingReq):
    global _branding_cache
    updated = save_branding_config(
        req.logo_url.strip(),
        req.youtube_url.strip(),
        req.nl_prompt.strip(),
        bool(req.voice_mode_enabled),
    )
    _branding_cache = updated
    return JSONResponse({"status": "ok", "data": updated})


def get_df():
    df = catalog_service.get_dataframe()
    try:
        app.state.DATAFRAME = df
    except Exception:
        pass
    return df

# ---------- Hierarchy helpers (L1/L2/L3) ----------

def _record_text(val: Any) -> str:
    return str(val or "").strip()

def _annotate_hierarchy(record: Dict[str, Any], hierarchy: Dict[str, str]) -> Dict[str, Any]:
    """Annotate a single record with matched_levels and hierarchy_score based on CateName_L1/2/3 fields."""
    # 🆕 確保 record 是字典，不是 DataFrame 行
    if not isinstance(record, dict):
        try:
            record = dict(record)
        except Exception:
            record = {}
    
    if not hierarchy:
        record.setdefault("matched_levels", [])
        record.setdefault("hierarchy_score", 0)
        return record
    l1 = _record_text(hierarchy.get("L1"))
    l2 = _record_text(hierarchy.get("L2"))
    l3 = _record_text(hierarchy.get("L3"))
    matched: List[str] = []
    if l1:
        v = _record_text(record.get("CateName_L1") or record.get("大分類名稱"))
        if v and (l1 in v):
            matched.append("L1")
    if l2:
        v = _record_text(record.get("CateName_L2") or record.get("中分類名稱"))
        if v and (l2 in v):
            matched.append("L2")
    if l3:
        v = _record_text(record.get("CateName_L3") or record.get("小分類名稱"))
        if v and (l3 in v):
            matched.append("L3")
    record["matched_levels"] = matched
    record["hierarchy_score"] = len(matched) * 3
    return record

def _filter_by_hierarchy(records: List[Dict[str, Any]], hierarchy: Optional[Dict[str, str]], from_hot_category: bool = False) -> List[Dict[str, Any]]:
    """Filter records by hierarchy (L1/L2/L3) with optimization for direct L3 queries.
    
    混合策略：
    - 來自熱門分類 UI 的 L3 點擊：直接過濾 L3，無需驗證 L1、L2 (超快速路徑) ⚡⚡
    - 只指定 L3 (不指定 L1、L2)：直接查詢 L3 (快速路徑) ⚡
    - 否則逐層驗證 (完整路徑) 🔍
    """
    def _sanitize_record(rec: Dict[str, Any]) -> Dict[str, Any]:
        """清理記錄中的 NumPy/Pandas 類型"""
        if not isinstance(rec, dict):
            return {}
        sanitized = {}
        for k, v in rec.items():
            # 處理 None
            if v is None:
                sanitized[k] = None
            # 基本類型直接保留
            elif isinstance(v, (bool, int, float, str)):
                sanitized[k] = v
            # 列表遞迴
            elif isinstance(v, (list, tuple)):
                sanitized[k] = [_sanitize_record({"_": item}).get("_", str(item)) if isinstance(item, dict) else str(item) for item in v]
            # 字典遞迴
            elif isinstance(v, dict):
                sanitized[k] = _sanitize_record(v)
            # 其他類型轉為字串
            else:
                try:
                    sanitized[k] = str(v)
                except Exception:
                    sanitized[k] = None
        return sanitized
    
    if not hierarchy:
        return records
    l1 = _record_text(hierarchy.get("L1"))
    l2 = _record_text(hierarchy.get("L2"))
    l3 = _record_text(hierarchy.get("L3"))
    if not any([l1, l2, l3]):
        return records
    
    logger.info("  🏛️ _filter_by_hierarchy() 被呼叫")
    logger.info(f"    L1={l1}, L2={l2}, L3={l3}, from_hot_category={from_hot_category}")
    
    # ⚡⚡ 超快速路徑：熱門分類 UI 的 L3 直接過濾
    # 此場景：用戶已經在 UI 上依序選擇 L1 → L2 → L3
    # 前端已驗證層級，L1、L2、L3 都已明確指定
    # 直接過濾 L3 即可，信任前端的選擇
    if from_hot_category and l3 and l1 and l2:
        logger.info("    ⚡⚡ 執行超快速路徑（熱門分類 UI L3 直接過濾）")
        filtered: List[Dict[str, Any]] = [
            _sanitize_record(_annotate_hierarchy(rec, hierarchy))
            for rec in records 
            if rec.get("CateName_L3") == l3 or _record_text(rec.get("CateName_L3")) == l3
        ]
        logger.info(f"    ✅ 超快速路徑結果: {len(filtered)} 筆")
        return filtered or records
    
    # 🚀 快速路徑：如果只指定了 L3 (不指定 L1、L2)，直接查詢 L3
    # 此場景通常來自用戶在搜尋欄位輸入（如「米類」）
    if l3 and not l1 and not l2:
        logger.info("    ⚡ 執行快速路徑（L3 Only 直接過濾）")
        # 直接過濾 L3，避免不必要的 L1、L2 檢查
        filtered: List[Dict[str, Any]] = [
            _sanitize_record(_annotate_hierarchy(rec, hierarchy))
            for rec in records 
            if rec.get("CateName_L3") == l3 or _record_text(rec.get("CateName_L3")) == l3
        ]
        logger.info(f"    ✅ 快速路徑結果: {len(filtered)} 筆")
        return filtered or records
    
    # 🔍 完整路徑：逐層驗證 (保留原有邏輯)
    # 此場景支援部分層級查詢 (L1 only, L1+L2, L1+L2+L3)
    logger.info("    🔍 執行完整路徑（逐層驗證）")
    filtered: List[Dict[str, Any]] = []
    for rec in records:
        ok = True
        if l1:
            v = _record_text(rec.get("CateName_L1") or rec.get("大分類名稱"))
            ok = ok and (l1 in v if v else False)
        if ok and l2:
            v = _record_text(rec.get("CateName_L2") or rec.get("中分類名稱"))
            ok = ok and (l2 in v if v else False)
        if ok and l3:
            v = _record_text(rec.get("CateName_L3") or rec.get("小分類名稱"))
            ok = ok and (l3 in v if v else False)
        if ok:
            filtered.append(_sanitize_record(_annotate_hierarchy(rec, hierarchy)))
    logger.info(f"    ✅ 完整路徑結果: {len(filtered)} 筆")
    return filtered or records


@app.post("/api/search")
def api_search(req: SearchReq):
    """搜尋 API 端點，追蹤執行路徑"""
    logger.info("-" * 80)
    logger.info("🔍 /api/search 端點被觸發")
    logger.info(f"  查詢: '{req.query}'")
    logger.info(f"  分類階層: {req.category_hierarchy}")
    logger.info(f"  來自熱門分類 UI: {req.from_hot_category}")
    logger.info(f"  頁碼: {req.page}, 每頁筆數: {req.page_size}")
    
    df = get_df()
    
    if req.query and is_negative_query(req.query):
        return JSONResponse({
            "message": NEGATIVE_QUERY_MESSAGE,
            "items": [],
            "page": 1,
            "page_size": 0,
            "has_next": False,
            "last_page": 1,
            "intent": {},
            "clarify": True,
        })
    
    # 🆕 P0.3: 快取檢查（純分類查詢）
    cache_key = None
    if (not req.query or req.query.strip() == "") and (
        req.category_hierarchy and any(req.category_hierarchy.values())
    ):
        l1 = _record_text(req.category_hierarchy.get("L1", ""))
        l2 = _record_text(req.category_hierarchy.get("L2", ""))
        l3 = _record_text(req.category_hierarchy.get("L3", ""))
        cache_key = f"category:{l1}|{l2}|{l3}|{req.page}|{req.page_size}|{req.prefer_special_first}"
        
        cached_result = _category_cache.get(cache_key)
        if cached_result:
            logger.info(f"  📦 [P0.3] 快取命中: {cache_key}")
            return cached_result
    
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
    
    # 記錄 LLM 使用配置
    logger.info("📝 LLM 搜尋模型配置:")
    logger.info(f"  - 查詢擴展啟用: {SEARCH_USE_EXPAND}")
    logger.info(f"  - 意圖分析啟用: {SEARCH_USE_INTENT}")
    logger.info(f"  - 結果重排啟用: {SEARCH_USE_RERANK}")
    
    # 🆕 P0.1: 快速路徑偵測（分類查詢無需 LLM 展開）
    should_skip_llm = (
        (not req.query or req.query.strip() == "") and 
        (req.category_hierarchy and any(req.category_hierarchy.values()))
    )
    
    # optional: expand query via LLM stub - 使用搜索配置
    if should_skip_llm:
        logger.info("🚀 [P0.1] 觸發快速路徑：分類查詢無 query，跳過 LLM")
        intent = {}
        expanded = ""
    else:
        try:
            logger.info("  ➡️ 調用 llm_analyze_query() 進行意圖分析")
            intent = llm_analyze_query(req.query, system_prompt=custom_prompt, use_search_config=True)
            logger.info(f"  ✅ 意圖分析結果: {intent}")
            
            clarify_decision = llm_clarify_or_confirm(intent, req.query or "")
            if clarify_decision.get("type") == "clarify":
                return JSONResponse({
                    "message": clarify_decision["message"],
                    "items": [],
                    "page": 1,
                    "page_size": 0,
                    "has_next": False,
                    "last_page": 1,
                    "intent": intent,
                    "clarify": True,
                })
            
            logger.info("  ➡️ 調用 llm_expand_query() 進行查詢擴展")
            expanded = llm_expand_query(req.query, system_prompt=custom_prompt, use_search_config=True)
            logger.info(f"  ✅ 擴展查詢: '{expanded}'")
        except Exception as e:
            logger.warning(f"  ❌ LLM 調用失敗: {e}")
            intent = {}
            expanded = req.query
    
    # ============================================================
    # 🆕 分頁大小決策邏輯（支援環境變數設定）
    # ============================================================
    prefer_special_first = bool(getattr(req, 'prefer_special_first', False))
    from_hot_category = bool(getattr(req, 'from_hot_category', False))  # 🆕 熱門分類 UI 標誌
    
    if from_hot_category:
        # 來自熱門分類按鈕，強制使用專用設定（忽略前端 page_size）
        page_size = HOT_CATEGORY_PAGE_SIZE
        logger.info(f"📌 [熱門分類] 強制使用 HOT_CATEGORY_PAGE_SIZE={HOT_CATEGORY_PAGE_SIZE}（忽略前端參數 {req.page_size}）")
    else:
        # 一般搜尋，使用預設設定（允許前端覆蓋，最大 50）
        page_size = max(1, min(req.page_size or DEFAULT_PAGE_SIZE, 50))
        logger.info(f"📌 [一般搜尋] 使用 page_size={page_size}（DEFAULT={DEFAULT_PAGE_SIZE}, 前端={req.page_size}）")
    
    page = max(1, req.page or 1)
    base_topn = page_size * page
    candidate_topn = base_topn + page_size
    if SEARCH_USE_RERANK:
        candidate_topn = max(base_topn * 2, base_topn + page_size, base_topn + 20, 60)
    required_terms = intent.get("required_terms") if isinstance(intent, dict) else None
    category_terms = intent.get("category_terms") if isinstance(intent, dict) else None
    excluded_terms = intent.get("excluded_terms") if isinstance(intent, dict) else None
    # 允許前端直接指定 category_hierarchy
    category_hierarchy = (req.category_hierarchy or (intent.get("category_hierarchy") if isinstance(intent, dict) else None))
    
    logger.info("🔎 搜尋參數:")
    logger.info(f"  - 展開查詢: '{expanded}'")
    logger.info(f"  - 必需詞: {required_terms}")
    logger.info(f"  - 排除詞: {excluded_terms}")
    logger.info(f"  - 分類層級: {category_hierarchy}")
    
    # 🆕 P0.1 特殊處理：純分類查詢（query 為空）時返回所有商品
    # 因為層級過濾會在後面進行，無需評分過濾
    if should_skip_llm and (not expanded or expanded.strip() == ""):
        logger.info("📦 [P0.1] 純分類查詢路徑：返回全數商品（層級過濾由後端進行）")
        raw_records = df.to_dict(orient="records")
        all_records = []
        for rec in raw_records:
            if not isinstance(rec, dict):
                try:
                    rec = dict(rec)
                except Exception:
                    rec = {}
            # 為純分類查詢補上預設分數，避免被低信心過濾排除
            rec.setdefault("__score__", 1.0)
            all_records.append(rec)
        _terms = []
    else:
        logger.info("📦 調用 search_products() 進行基礎搜尋")
        all_records, _terms = search_products(
            df,
            expanded,
            topn=candidate_topn,
            sort_price=True,
            required_terms=required_terms,
            category_terms=category_terms,
            excluded_terms=excluded_terms,
        )
    logger.info(f"  ✅ 搜尋到 {len(all_records)} 筆記錄")
    
    # 🆕 若有層級分類（L1/L2/L3），優先套用過濾並標註匹配層級
    if category_hierarchy:
        logger.info("🎯 套用層級分類過濾")
        logger.info(f"  - 來自熱門分類 UI: {from_hot_category}")
        try:
            all_records = _filter_by_hierarchy(all_records, category_hierarchy, from_hot_category)
            logger.info(f"  ✅ 過濾後: {len(all_records)} 筆記錄")
        except Exception as e:
            logger.warning(f"  ❌ 層級過濾失敗: {e}")
    else:
        logger.info("  (無層級分類，跳過過濾)")
    all_records = filter_low_confidence_products(all_records, min_score=MIN_CONFIDENCE_SCORE)
    if not all_records:
        return JSONResponse({
            "message": LOW_CONFIDENCE_MESSAGE,
            "items": [],
            "page": page,
            "page_size": page_size,
            "has_next": False,
            "last_page": page,
            "intent": intent or {},
            "clarify": True,
        })
    total_available = len(all_records)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    has_next = total_available > end_idx
    last_page = max(1, (total_available + page_size - 1) // page_size)
    
    # 🆕 P0.2: 條件化重排（disable_rerank 標誌）
    disable_rerank = bool(getattr(req, 'disable_rerank', False))
    if SEARCH_USE_RERANK and not disable_rerank:
        reranked = llm_rerank_products(req.query, expanded, all_records, topn=end_idx, system_prompt=custom_prompt, use_search_config=True)
        records = reranked[start_idx:end_idx]
        # 🆕 融合排序：結合 LLM 重排順序與層級分數
        try:
            hw = float(os.getenv("HIER_SORT_WEIGHT", "1.0"))
            rw = float(os.getenv("RERANK_SORT_WEIGHT", "1.0"))
            if any((r or {}).get("hierarchy_score", 0) for r in records):
                base_len = len(records)
                base_scores = {i: (base_len - i) for i in range(base_len)}
                def _combined_score(idx: int, rec: Dict[str, Any]) -> float:
                    return hw * float(rec.get("hierarchy_score", 0) or 0.0) + rw * float(base_scores.get(idx, 0))
                records = sorted(
                    list(enumerate(records)),
                    key=lambda t: _combined_score(t[0], t[1]),
                    reverse=True,
                )
                records = [rec for _, rec in records]
        except Exception:
            pass
    else:
        if disable_rerank:
            logger.info("  ⚡ [P0.2] 禁用 LLM 重排")
        records = all_records[start_idx:end_idx]
        # 🆕 二階排序：若有層級匹配分數，優先顯示分數較高的項目（穩定排序）
        try:
            if any((r or {}).get("hierarchy_score", 0) for r in records):
                records = sorted(records, key=lambda r: r.get("hierarchy_score", 0), reverse=True)
        except Exception:
            pass

    # 🆕 特價優先：若帶入 prefer_special_first，將有特價者置頂（穩定排序維持原相對順序）
    try:
        if prefer_special_first:
            def _has_special(rec: Dict[str, Any]) -> bool:
                special = str(rec.get("SpecialOffer") or rec.get("特價") or rec.get("pric_special") or "").strip()
                if special:
                    return True
                # 比價：若存在價格與特價數字且特價更低
                try:
                    price = float(str(rec.get("Price") or rec.get("價格") or rec.get("pric") or 0).replace(',', ''))
                    sp = float(str(rec.get("SpecialOffer") or rec.get("特價") or 0).replace(',', ''))
                    return bool(sp and price and sp < price)
                except Exception:
                    return False
            # 穩定排序：有特價在前
            records = sorted(list(enumerate(records)), key=lambda t: (0 if _has_special(t[1]) else 1, t[0]))
            records = [rec for _, rec in records]
    except Exception:
        pass
    
    # 🆕 P1.2: 判斷是否使用瘦身模式（純分類查詢）
    use_slim_mode = (not req.query or req.query.strip() == "") and bool(req.category_hierarchy and any(req.category_hierarchy.values()))
    
    items = format_for_chat(records, slim_mode=use_slim_mode)
    if use_slim_mode:
        logger.info("  ⚡ [P1.2] 使用瘦身模式（减少回應大小）")
    
    # 🆕 P0.2: 條件化文案生成（disable_promo 標誌）
    disable_promo = bool(getattr(req, 'disable_promo', False))
    if disable_promo:
        logger.info("  ⚡ [P0.2] 禁用宣傳文生成")
    
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
        if SEARCH_USE_PROMO and not disable_promo:
            try:
                marketing = llm_generate_promo(it.get("商品名稱", ""), original_desc, use_search_config=True)
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
                    it["商品描述"] = llm_shorten_20(it.get("商品名稱", ""), use_search_config=True)
                except Exception:
                    it["商品描述"] = it.get("商品名稱", "")[:60]
    
    # 🆕 清理 JSON 序列化（確保所有值都是基本類型）
    def _sanitize_for_json(obj: Any) -> Any:
        """遞迴清理對象，確保可序列化為 JSON"""
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
        if isinstance(obj, (list, tuple)):
            return [_sanitize_for_json(x) for x in obj]
        if isinstance(obj, dict):
            return {str(k): _sanitize_for_json(v) for k, v in obj.items()}
        # 其他類型轉為字串
        return str(obj)
    
    try:
        items = _sanitize_for_json(items)
        intent = _sanitize_for_json(intent or {})
    except Exception as e:
        logger.warning(f"  ⚠️ JSON 清理失敗: {e}")
    
    # 構建回應
    response_data = {
        "message": f"為您找到 {len(items)} 項商品：",
        "items": items,
        "page": page,
        "page_size": page_size,
        "has_next": has_next,
        "last_page": last_page,
        "intent": intent or {}
    }
    
    # 🆕 P0.3: 快取存儲（純分類查詢）
    if cache_key:
        try:
            result_response = JSONResponse(response_data)
            _category_cache.set(cache_key, result_response)
            logger.info(f"  💾 [P0.3] 結果已快取: {cache_key}")
        except Exception as e:
            logger.warning(f"  ⚠️ 快取存儲失敗: {e}")
    
    try:
        return JSONResponse(response_data)
    except Exception as e:
        logger.error(f"  ❌ API 回應序列化失敗: {e}")
        # 備用簡化回應
        return JSONResponse({
            "message": f"為您找到 {len(items)} 項商品（部分字段可能無法顯示）",
            "items": [{"商品名稱": item.get("商品名稱", "未知商品")} for item in items],
            "page": page,
            "page_size": page_size,
            "has_next": has_next,
            "last_page": last_page,
            "intent": {}
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
    structured_products: Optional[List[Dict[str, Any]]] = None  # 🆕 新增結構化商品資料欄位


# 舊的 chat 端點已移除，功能已移至 chat_router_goods_action.py 以避免路由衝突


@app.post("/api/suggest")
def suggest_endpoint(req: SuggestReq):
    session_id = str(req.session_id or "default")
    suggestion_type = int(req.type or 1)
    return _render_bundle_response(session_id, suggestion_type)


@app.get("/api/recommendations/{bundle_id}")
def get_recommendation_bundle(bundle_id: str, view: Optional[str] = None, suggestion_type: Optional[int] = None):
    """
    新的推薦查詢端點，可透過 view 或 suggestion_type 指定不同的推薦清單。
    
    view 可選：
        original (預設) / sale / complementary
    """
    if suggestion_type is not None:
        try:
            suggestion_value = int(suggestion_type)
        except Exception:
            suggestion_value = 1
    else:
        view_key = (view or "original").lower()
        suggestion_value = SUGGESTION_VIEW_MAP.get(view_key, 1)
    payload = _render_bundle_response(bundle_id, suggestion_value)
    payload.setdefault("bundle_id", bundle_id)
    view_label = (view or "").lower()
    if view_label not in SUGGESTION_VIEW_MAP:
        view_label = SUGGESTION_TYPE_LABEL.get(suggestion_value, "original")
    payload.setdefault("view", view_label)
    payload.setdefault("suggestion_type", suggestion_value)
    return JSONResponse(payload)


@app.get("/api/version")
def api_version():
    short_commit = BUILD_COMMIT[:7] if BUILD_COMMIT not in (None, "unknown") else BUILD_COMMIT
    return JSONResponse({
        "commit": BUILD_COMMIT,
        "short_commit": short_commit,
        "branch": BUILD_BRANCH,
        "built_at": BUILD_TIME,
    })

@app.get("/version")
async def get_version():
    """簡化版本端點，回傳 JSON 格式"""
    short_commit = BUILD_COMMIT[:7] if BUILD_COMMIT not in (None, "unknown") else BUILD_COMMIT
    return JSONResponse({"version": f"main@{short_commit}"})


@app.get("/health")
def health():
    """Simple health-check endpoint for load balancers/containers."""
    return JSONResponse({"status": "ok"})

@app.get("/debug/paths")
def debug_paths():
    """診斷端點：檢查檔案路徑和存在性"""
    import os
    paths_info = {
        "current_working_dir": os.getcwd(),
        "data_path_env": os.getenv("DATA_PATH"),
        "computed_data_path": str(DATA_PATH),
        "data_path_exists": DATA_PATH.exists(),
        "render_path_exists": Path("/opt/render/project/src/data/VIEW_GOODS_enhanced.csv").exists(),
        "local_path_exists": (ROOT / "data" / "VIEW_GOODS_enhanced.csv").exists(),
        "root_path": str(ROOT)
    }
    return JSONResponse(paths_info)

@app.get("/debug/llm")
def debug_llm():
    """診斷端點：檢查 LLM 相關環境變數和配置"""
    import os
    from llm_service import _get_client, CHAT_USE_EXPAND, CHAT_USE_INTENT, SEARCH_USE_EXPAND, SEARCH_USE_INTENT
    
    api_key = os.getenv("OPENAI_API_KEY", "")
    api_key_status = "not_set"
    if api_key:
        if api_key == "your-openai-api-key":
            api_key_status = "placeholder"
        elif api_key.startswith("sk-"):
            api_key_status = f"valid_key_{api_key[:8]}...{api_key[-4:]}"
        else:
            api_key_status = "invalid_format"
    
    client = _get_client()
    
    llm_info = {
        "openai_api_key_status": api_key_status,
        "use_chat_mode": os.getenv("USE_CHAT_MODE", "True"),
        "chat_use_expand": CHAT_USE_EXPAND,
        "chat_use_intent": CHAT_USE_INTENT,
        "search_use_expand": SEARCH_USE_EXPAND,
        "search_use_intent": SEARCH_USE_INTENT,
        "client_available": client is not None,
        "chat_openai_model": os.getenv("CHAT_OPENAI_MODEL", "gpt-4o-mini"),
        "search_openai_model": os.getenv("SEARCH_OPENAI_MODEL", "gpt-4o-mini")
    }
    return JSONResponse(llm_info)


# --- Admin endpoints: protected by ADMIN_TOKEN env var (simple token auth)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
# allow bypass in development when ALLOW_DEV_ADMIN is set (1/true)
ALLOW_DEV_ADMIN = os.getenv("ALLOW_DEV_ADMIN", "false").lower() in ("1", "true", "yes")


# 允許內網/本機無 token 管理（可透過環境變數關閉）
ALLOW_LOCAL_ADMIN = os.getenv("ALLOW_LOCAL_ADMIN", "true").lower() in ("1", "true", "yes")


def _is_private_client(request: Request) -> bool:
    try:
        client = getattr(request, "client", None)
        host = client.host if client else ""
        if not host:
            return False
        if host in ("::1", "localhost"):
            return True
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except Exception:
        return False


def _check_admin(request: Request, token: Optional[str]):
    # development bypass
    if ALLOW_DEV_ADMIN:
        return
    # local/private allow
    if ALLOW_LOCAL_ADMIN and _is_private_client(request):
        return
    if not ADMIN_TOKEN:
        # no admin token configured -> disallow admin endpoints in production
        raise HTTPException(status_code=403, detail="admin endpoints disabled")
    if not token or token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/api/admin/info")
def admin_info(request: Request):
    """簡單的管理診斷：不暴露敏感資訊。"""
    try:
        client = getattr(request, "client", None)
        client_ip = client.host if client else "unknown"
    except Exception:
        client_ip = "unknown"
    cat_diag = {}
    try:
        cat_diag = get_categories_diag() or {}
    except Exception:
        cat_diag = {"error": "failed to read categories diagnostics"}
    info = {
        "client_ip": client_ip,
        "require_token": not (ALLOW_DEV_ADMIN or (ALLOW_LOCAL_ADMIN and _is_private_client(request))) and bool(ADMIN_TOKEN),
        "admin_token_set": bool(ADMIN_TOKEN),
        "allow_dev_admin": ALLOW_DEV_ADMIN,
        "allow_local_admin": ALLOW_LOCAL_ADMIN,
        "data_path": str(DATA_PATH),
        "data_path_exists": DATA_PATH.exists(),
        "data_dir_writable": os.access(str(DATA_PATH.parent), os.W_OK),
        # categories diagnostics
        "categories": cat_diag,
    }
    return JSONResponse(info)

@app.post("/api/admin/clear-cache")
def admin_clear_cache(request: Request, x_admin_token: Optional[str] = Header(None)):
    """Clear the in-memory DataFrame cache so the next request reloads CSV."""
    _check_admin(request, x_admin_token)
    catalog_service.reset()
    SESSION_ALIGN_CACHE.clear()
    bundle_service.clear()
    
    # 🆕 P0.3: 清除分類快取
    global _category_cache
    _category_cache.clear()
    logger.info("  🗑️ [P0.3] 分類快取已清除")
    
    try:
        load_goods_rows(refresh=True)
    except Exception as exc:
        logger.warning("failed refreshing goods rows cache during clear-cache: %s", exc)
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
    After replace the in-memory catalog cache is cleared so new requests
    will reload the CSV.
    """
    _check_admin(request, x_admin_token)
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
        # 若目標目錄不可寫，降級到 /tmp
        target_path = str(dst)
        if not os.access(str(dst.parent), os.W_OK):
            alt = Path("/tmp/VIEW_GOODS_enhanced.csv")
            logger.warning("DATA_PATH directory not writable, falling back to %s", alt)
            target_path = str(alt)
            alt.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp_path, target_path)
        # clear cache & refresh
        catalog_service.set_data_path(target_path)
        catalog_service.reset()
        try:
            load_goods_rows(refresh=True)
        except Exception as refresh_exc:
            logger.warning("failed refreshing goods rows cache after upload: %s", refresh_exc)
        logger.info("replaced data file at %s and cleared cache", target_path)
        return JSONResponse({"status": "ok", "message": "uploaded and replaced csv", "path": target_path})
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
# Support both development (../frontend) and Docker (./static) paths
frontend_path = ROOT / "frontend"
if not frontend_path.exists():
    # In Docker, frontend files are at /app/backend/static/
    frontend_path = Path(__file__).parent / "static"

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
            response = FileResponse(index_path)
            # Force no cache for HTML to ensure latest version is loaded
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
    # Also add no-cache for successful HTML responses
    if resp.headers.get("content-type", "").startswith("text/html"):
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
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

# ---- 統一聊天 API JSON 格式 ----
from chat_router_goods_action import chat_handler, ChatReq, get_chat_result_by_session
from typing import List

# 統一回應模型定義
class ChatResp(BaseModel):
    reply: str
    suggestion_ids: List[str] = []
    session_id: Optional[str] = None
    chat_session_id: Optional[str] = None
    action: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    items: Optional[List[Dict[str, Any]]] = None
    auto_suggest: Optional[Dict[str, Any]] = None
    alignment: Optional[Dict[str, Any]] = None
    structured_payload: Optional[Dict[str, Any]] = None
    structured_products: Optional[List[Dict[str, Any]]] = None  # 🆕 新增結構化商品資料欄位
    display_mode: Optional[str] = None
    # 🎙️ 語音模式相關欄位
    voice_summary: Optional[str] = None
    voice_mode_active: Optional[bool] = None
    voice_session_end: Optional[bool] = None

class ChatSessionResp(BaseModel):
    session_id: str
    history: List[Dict] = []


_CONTENT_ENGINE_NAME_KEYS = (
    "name",
    "商品名稱",
    "Name",
    "title",
    "product_name",
)

_CONTENT_ENGINE_DESC_KEYS = (
    "description",
    "商品描述",
    "Description",
    "ShortDesc",
    "ShortDesc_20",
    "short_desc",
    "summary",
    "desc",
)


def _build_content_engine_payload(product: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """從商品資料中提取 Content Engine 需要的 name/description。"""
    name = None
    for key in _CONTENT_ENGINE_NAME_KEYS:
        value = product.get(key)
        if value:
            name = str(value).strip()
            if name:
                break
    if not name:
        return None

    description = None
    for key in _CONTENT_ENGINE_DESC_KEYS:
        value = product.get(key)
        if value:
            description = str(value).strip()
            if description:
                break
    if not description:
        return None

    return {"name": name, "description": description}


async def _enrich_structured_products(products: List[Dict[str, Any]]) -> None:
    """批次呼叫 Content Engine，為 structured_products 生成內容欄位。"""
    tasks = []
    target_products: List[Dict[str, Any]] = []
    for product in products or []:
        payload = _build_content_engine_payload(product)
        if not payload:
            continue
        tasks.append(generate_content(payload))
        target_products.append(product)

    if not tasks:
        return

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for product, response in zip(target_products, results):
        if isinstance(response, Exception):
            logger.warning("Content engine failed for product %s: %s", product.get("name") or product.get("商品名稱"), response)
            continue
        if isinstance(response, dict) and response:
            product.update(response)

@app.post("/api/chat", response_model=ChatResp)
async def chat_endpoint(req: ChatReq):
    """
    處理使用者聊天請求，回傳標準 JSON 格式：
    {
      "reply": "AI 回覆內容",
      "suggestion_ids": ["123", "456"],
      "session_id": "abcd1234",
      "voice_summary": "語音摘要"  # 🎙️ 語音模式
    }
    """
    try:
        result = chat_handler(req)
        
        if hasattr(result, "model_dump"):
            payload: Dict[str, Any] = result.model_dump()  # type: ignore[attr-defined]
        elif hasattr(result, "dict"):
            payload = result.dict()  # type: ignore[attr-defined]
        elif isinstance(result, dict):
            payload = dict(result)
        else:
            payload = {"reply": str(result or "")}

        session_id = payload.get("chat_session_id") or payload.get("session_id") or req.session_id
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())[:8]
        payload["session_id"] = session_id
        payload["chat_session_id"] = session_id

        structured_payload = payload.get("structured_payload") or {}
        structured_products = payload.get("structured_products") or structured_payload.get("items") or []
        payload["structured_products"] = structured_products
        suggestion_ids = payload.get("suggestion_ids") or []
        meta = payload.get("meta") or {}
        if meta.get("oos_category"):
            structured_payload = {}
            structured_products = []
            payload["structured_payload"] = None
            payload["structured_products"] = []
            payload["items"] = []
            suggestion_ids = []
            payload["suggestion_ids"] = []
        elif structured_products:
            try:
                await _enrich_structured_products(structured_products)
            except Exception as exc:
                logger.warning("Content engine enrichment skipped due to error: %s", exc)

        # 🎙️ 語音模式處理
        if req.voice_mode:
            from voice_service import (
                is_intent_allowed,
                build_intent_reject_payload,
                build_voice_directives,
            )

            detected_intent = (payload.get("detected_intent") or "goods_search").strip()
            if not is_intent_allowed(detected_intent):
                payload.update(build_intent_reject_payload())
            else:
                query_type = "company_profile" if detected_intent == "company_profile" else "goods_search"
                results = structured_products or payload.get("items") or []
                total_count = (payload.get("meta") or {}).get("total") or len(results)
                payload.update(build_voice_directives(results, query_type, total_count))

        should_cache = not (meta.get("search_fallback") or meta.get("oos_category"))
        try:
            if should_cache and (suggestion_ids or structured_products):
                align_rows = catalog_service.get_items_by_ids(suggestion_ids) if suggestion_ids else []
                bundle_service.save_bundle(session_id, {
                    "align_ids": suggestion_ids,
                    "align_rows": align_rows,
                    "query_terms": [getattr(req, 'user_message', None) or req.message],
                    "structured_items": structured_products,
                    "structured_summary": structured_payload.get("summary", f"為您找到了 {len(structured_products)} 款相關商品") if structured_payload else "",
                    "structured_filters": payload.get("structured_filters"),
                })
        except Exception as e:
            logger.warning(f"Failed to sync recommendation bundle: {e}")

        # 只挑選 ChatResp 定義內的欄位，保持回傳結構穩定
        filtered_payload = {k: v for k, v in payload.items() if k in ChatResp.model_fields}
        # 確保 reply 與 suggestion_ids 至少有預設值
        filtered_payload.setdefault("reply", "")
        filtered_payload.setdefault("suggestion_ids", suggestion_ids or [])
        return ChatResp(**filtered_payload)
    except Exception as e:
        return ChatResp(
            reply="抱歉，目前聊天服務暫時無法回應，稍後再試。",
            suggestion_ids=[],
            session_id=req.session_id
        )

# ---- 🔧 維修服務 API 端點 ----

if ENABLE_REPAIR_SERVICE:
    class RepairChatReq(BaseModel):
        """維修聊天請求模型"""
        message: str
        history: List[Dict[str, str]] = []
        session_id: Optional[str] = None
        topn: int = 5
        
    class RepairChatResp(BaseModel):
        """維修聊天回應模型"""
        reply: str
        repairs: List[Dict[str, Any]] = []
        session_id: Optional[str] = None
        meta: Optional[Dict[str, Any]] = None
    
    @app.post("/api/repair/chat", response_model=RepairChatResp)
    def repair_chat_endpoint(req: RepairChatReq):
        """
        住宅維修聊天端點
        
        處理維修相關查詢，返回維修項目建議和處理指引
        
        Args:
            req: 維修聊天請求
        
        Returns:
            RepairChatResp: 維修聊天回應
        """
        try:
            # 生成或使用會話 ID
            session_id = req.session_id
            if not session_id:
                import uuid
                session_id = str(uuid.uuid4())
            
            logger.info(f"[Repair] POST /api/repair/chat received session_id={session_id}")
            
            # 🔧 先檢查該 session 是否處於真人客服模式
            manual_mode = False
            
            # 先嘗試從記憶體中取得
            existing_supabase_session_id = REPAIR_LOGGING_BRIDGE.get_supabase_session(session_id)
            logger.info(f"[Repair] Memory lookup: ui_session={session_id} -> supabase_session={existing_supabase_session_id}")
            
            # 如果記憶體中沒有（例如重啟後），從資料庫查詢
            if not existing_supabase_session_id and session_id:
                logger.info(f"[Repair] Not in memory, querying session_events for ui_session={session_id}")
                try:
                    from supabase_client import get_supabase_client
                    client = get_supabase_client(prefer_service_role=True)
                    
                    # 從 session_events 查詢對應的 supabase_session_id
                    events_response = client.table('session_events')\
                        .select('session_id, details')\
                        .eq('event_type', 'status_change')\
                        .order('created_at', desc=True)\
                        .execute()
                    
                    logger.info(f"[Repair] Found {len(events_response.data)} session_events")
                    
                    # 找到對應的 ui_session_id
                    for event in events_response.data:
                        details = event.get('details', {})
                        event_ui_session = details.get('ui_session_id')
                        logger.debug(f"[Repair] Checking event: supabase_session={event.get('session_id')}, ui_session={event_ui_session}")
                        if event_ui_session == session_id:
                            existing_supabase_session_id = event.get('session_id')
                            # 恢復記憶體 mapping
                            REPAIR_LOGGING_BRIDGE.bind_ui_session(session_id, existing_supabase_session_id)
                            logger.info(f"[Repair] ✅ Restored session mapping: UI={session_id} -> Supabase={existing_supabase_session_id}")
                            break
                    
                    if not existing_supabase_session_id:
                        logger.warning(f"[Repair] ❌ No matching ui_session_id found in session_events for UI session: {session_id}")
                        logger.warning(f"[Repair] 提示：請確認第一次查詢時是否正確傳入此 UI session_id")
                except Exception as e:
                    logger.warning(f"[Repair] Failed to query session_events: {e}")
            
            # 如果找到了 existing session，查詢 manual_mode
            if existing_supabase_session_id:
                try:
                    from supabase_client import get_supabase_client
                    client = get_supabase_client(prefer_service_role=True)
                    
                    repair_response = client.table('repair_sessions')\
                        .select('manual_mode')\
                        .eq('session_id', existing_supabase_session_id)\
                        .execute()
                    
                    if repair_response.data:
                        manual_mode = repair_response.data[0].get('manual_mode', False)
                        logger.info(f"[Repair] Session {existing_supabase_session_id} manual_mode={manual_mode}")
                except Exception as e:
                    logger.warning(f"[Repair] Failed to check manual_mode: {e}")
            
            # 記錄用戶訊息到 chat_messages 並取得 record（便於情緒分析寫回）
            supabase_session_id, user_msg_record = REPAIR_LOGGING_BRIDGE.log_user_message_with_record(
                session_id,
                req.message,
                {
                    "history_length": len(req.history or []),
                    "topn": req.topn,
                },
                supabase_session_id=existing_supabase_session_id,
            )

            # 情緒分析（達標才寫入 chat_messages.emotion_data 與 emotion_analysis）
            try:
                emotion_result = analyze_user_emotion(req.message)
                if emotion_result:
                    persist_emotion_result(user_msg_record, supabase_session_id or session_id, emotion_result)
            except Exception as exc:
                logger.warning(f"[Emotion] Analyze/persist failed: {exc}")
            
            # 🔧 如果是真人客服模式，只記錄訊息不生成 LLM 回覆
            if manual_mode:
                logger.info(f"[Repair] Manual mode active, skipping LLM reply for session: {supabase_session_id}")
                REPAIR_LOGGING_BRIDGE.bind_ui_session(session_id, supabase_session_id)
                return RepairChatResp(
                    reply="",  # 空回覆，等待客服人員回覆
                    repairs=[],
                    session_id=supabase_session_id or session_id,
                    meta={"manual_mode": True, "message": "waiting_for_operator"}
                )
            
            # 確保 repair_sessions 表中有此 session 記錄
            # ⚠️ 關鍵：使用 supabase_session_id（來自 session_events）而非前端的 session_id
            
            if supabase_session_id:
                try:
                    from supabase_client import get_supabase_client
                    from datetime import datetime
                    
                    client = get_supabase_client(prefer_service_role=True)
                    
                    # 檢查 session 是否存在（使用 supabase_session_id）
                    check_response = client.table('repair_sessions')\
                        .select('session_id')\
                        .eq('session_id', supabase_session_id)\
                        .execute()
                    
                    if not check_response.data:
                        # Session 不存在，建立新的
                        session_data = {
                            'session_id': supabase_session_id,  # 使用 supabase_session_id
                            'manual_mode': False,  # 預設 AI 自動回覆
                            'status': 'ongoing',
                            'started_at': datetime.utcnow().isoformat()
                        }
                        client.table('repair_sessions').insert(session_data).execute()
                        logger.info(f"[Repair] Created new session: {supabase_session_id}")
                        
                except Exception as e:
                    logger.warning(f"[Repair] Failed to create session record: {e}")
                    # 不影響主流程，繼續處理
            
            # 🔧 如果是真人客服模式，只記錄訊息不生成 LLM 回覆
            if manual_mode:
                logger.info(f"[Repair] Manual mode active, skipping LLM reply for session: {supabase_session_id}")
                REPAIR_LOGGING_BRIDGE.bind_ui_session(session_id, supabase_session_id)
                return RepairChatResp(
                    reply="",  # 空回覆，等待客服人員回覆
                    repairs=[],
                    session_id=supabase_session_id or session_id,
                    meta={"manual_mode": True, "message": "waiting_for_operator"}
                )
            
            # 載入維修資料
            repair_df = load_repair_data()
            
            if repair_df.empty:
                payload = {
                    "reply": "抱歉，目前維修資料庫暫時無法使用，請稍後再試。🛠️",
                    "meta": {"error": "data_unavailable"},
                    "items": [],
                }
                REPAIR_LOGGING_BRIDGE.bind_ui_session(session_id, supabase_session_id)
                REPAIR_LOGGING_BRIDGE.log_assistant_message(
                    session_id,
                    payload["reply"],
                    payload,
                    supabase_session_id=supabase_session_id,
                )
                return RepairChatResp(
                    reply=payload["reply"],
                    repairs=[],
                    session_id=supabase_session_id or session_id,  # 返回 supabase_session_id
                    meta=payload["meta"],
                )
            
            # 搜尋維修項目
            query = req.message.strip()
            
            # 使用 LLM 擴展查詢（如果啟用）
            expanded_query = query
            try:
                expanded_query = repair_expand_query(query)
                logger.info(f"[Repair] Query expanded: '{query}' -> '{expanded_query}'")
            except Exception as e:
                logger.warning(f"[Repair] Query expansion failed: {e}")
            
            # 執行搜尋
            results, terms = search_repairs(
                df=repair_df,
                query=expanded_query,
                topn=req.topn,
                min_score=1.0
            )
            
            # 格式化結果
            formatted_repairs = format_repairs_for_chat(results, slim_mode=False)
            
            # 生成對話回覆
            reply = ""
            try:
                reply = repair_chat_reply(
                    query=query,
                    history=req.history,
                    results=formatted_repairs
                )
            except Exception as e:
                logger.warning(f"[Repair] Chat reply generation failed: {e}")
                # 降級：使用簡單範本
                if formatted_repairs:
                    reply = f"找到 {len(formatted_repairs)} 個相關的維修項目，請查看以下建議："
                else:
                    reply = "很抱歉，目前沒有找到相關的維修項目。請嘗試其他關鍵字，或直接聯絡物業管理處。"
            
            # 返回結果
            response_meta = {
                "query": query,
                "expanded_query": expanded_query if expanded_query != query else None,
                "terms": terms,
                "result_count": len(formatted_repairs),
            }
            response_payload = {
                "reply": reply,
                "items": formatted_repairs,
                "meta": response_meta,
            }

            REPAIR_LOGGING_BRIDGE.bind_ui_session(session_id, supabase_session_id)
            REPAIR_LOGGING_BRIDGE.log_assistant_message(
                session_id,
                reply,
                response_payload,
                supabase_session_id=supabase_session_id,
            )

            return RepairChatResp(
                reply=reply,
                repairs=formatted_repairs,
                session_id=supabase_session_id or session_id,  # 返回 supabase_session_id
                meta=response_meta,
            )
            
        except Exception as e:
            logger.error(f"[Repair] Endpoint error: {e}", exc_info=True)
            return RepairChatResp(
                reply="抱歉，維修服務暫時無法回應，請稍後再試。🛠️",
                repairs=[],
                session_id=req.session_id or "error",
                meta={"error": str(e)}
            )
    
    @app.get("/api/repair/categories")
    def repair_categories_endpoint():
        """
        取得所有維修類別
        
        Returns:
            維修類別列表
        """
        try:
            from repair_search_service import get_repair_categories
            repair_df = load_repair_data()
            categories = get_repair_categories(repair_df)
            return {"categories": categories}
        except Exception as e:
            logger.error(f"[Repair] Categories endpoint error: {e}")
            return {"categories": []}
    
    @app.post("/api/repair/search")
    def repair_search_endpoint(req: Dict[str, Any]):
        """
        維修項目搜尋端點（不含對話功能）
        
        Args:
            req: 搜尋請求 {"query": str, "topn": int, "category": str}
        
        Returns:
            搜尋結果列表
        """
        try:
            query = req.get("query", "").strip()
            topn = req.get("topn", 5)
            category_filter = req.get("category")
            
            repair_df = load_repair_data()
            results, terms = search_repairs(
                df=repair_df,
                query=query,
                topn=topn,
                category_filter=category_filter
            )
            
            formatted = format_repairs_for_chat(results, slim_mode=True)
            
            return {
                "results": formatted,
                "meta": {
                    "query": query,
                    "terms": terms,
                    "count": len(formatted)
                }
            }
        except Exception as e:
            logger.error(f"[Repair] Search endpoint error: {e}")
            return {"results": [], "meta": {"error": str(e)}}

    @app.get("/api/repair/chat_logs")
    def get_repair_chat_logs(date: str = Query(..., description="查詢日期 YYYY-MM-DD")):
        """
        查詢指定日期的住宅維修對話記錄
        
        Args:
            date: 查詢日期，格式 YYYY-MM-DD (例如: 2025-11-21)
        
        Returns:
            {
                "date": "2025-11-21",
                "total_count": 16,
                "user_count": 8,
                "llm_count": 8,
                "session_count": 4,
                "messages": [
                    {
                        "message_id": 662,
                        "session_id": "uuid...",
                        "role": "llm",
                        "content": "訊息內容...",
                        "created_at": "2025-11-21T07:38:55+00:00"
                    },
                    ...
                ]
            }
        """
        from datetime import datetime, timedelta
        
        try:
            # 驗證日期格式
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="日期格式錯誤，請使用 YYYY-MM-DD 格式 (例如: 2025-11-21)"
                )
            
            # 檢查是否配置 Supabase
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                # 返回模擬資料（開發模式）
                logger.info(f"[Repair] Supabase 未配置，返回模擬資料 (date={date})")
                return {
                    "date": date,
                    "total_count": 0,
                    "user_count": 0,
                    "llm_count": 0,
                    "session_count": 0,
                    "messages": [],
                    "mode": "demo",
                    "note": "Supabase 未配置，請在 .env 設定 SUPABASE_URL 和 SUPABASE_KEY"
                }
            
            # 建立時間範圍（當天 00:00:00 到 23:59:59）
            start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
            
            # 使用 service role 連線查詢
            from supabase_client import get_supabase_client
            client = get_supabase_client(prefer_service_role=True)
            
            # 查詢資料（按時間降序排列，最新訊息在前）
            response = client.table('chat_messages')\
                .select('message_id, session_id, role, content, created_at, emotion_data')\
                .eq('source_module', 'repair')\
                .gte('created_at', start_time.isoformat())\
                .lt('created_at', end_time.isoformat())\
                .order('created_at', desc=True)\
                .execute()
            
            messages = response.data or []
            
            # 計算統計資訊
            user_count = len([m for m in messages if m.get('role') == 'user'])
            llm_count = len([m for m in messages if m.get('role') == 'llm'])
            session_ids = set(m.get('session_id') for m in messages if m.get('session_id'))
            
            return {
                "date": date,
                "total_count": len(messages),
                "user_count": user_count,
                "llm_count": llm_count,
                "session_count": len(session_ids),
                "messages": messages
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[Repair] Chat logs query error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"查詢失敗: {str(e)}"
            )

    # ---- 🤖 AI 優化客服回覆端點 ----
    
    class OptimizeReplyRequest(BaseModel):
        original_text: str
        context: str = "repair_customer_service"
    
    class OptimizeReplyResponse(BaseModel):
        optimized_text: str
        original_text: str
    
    @app.post("/api/repair/optimize_reply", response_model=OptimizeReplyResponse)
    def optimize_repair_reply(req: OptimizeReplyRequest):
        """
        使用 AI 優化客服回覆內容
        
        將客服人員輸入的原始文字優化為更專業、友善的客服用語
        
        Args:
            req: {
                "original_text": "原始回覆內容",
                "context": "repair_customer_service"
            }
        
        Returns:
            {
                "optimized_text": "優化後的內容",
                "original_text": "原始內容"
            }
        """
        if not ENABLE_REPAIR_SERVICE:
            raise HTTPException(
                status_code=503,
                detail="維修服務未啟用"
            )
        
        original_text = req.original_text.strip()
        if not original_text:
            raise HTTPException(
                status_code=400,
                detail="原始文字不可為空"
            )
        
        try:
            from repair_llm_service import optimize_customer_service_reply
            
            optimized = optimize_customer_service_reply(original_text, context=req.context)
            
            return OptimizeReplyResponse(
                optimized_text=optimized,
                original_text=original_text
            )
            
        except Exception as e:
            logger.error(f"[Repair] AI optimize reply error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"AI 優化失敗: {str(e)}"
            )

    # ---- 👤 真人接手對話端點 ----
    
    class ManualModeRequest(BaseModel):
        session_id: str
        manual_mode: bool
        operator_id: Optional[str] = None
        operator_name: Optional[str] = None
    
    class ManualModeResponse(BaseModel):
        success: bool
        session_id: str
        manual_mode: bool
        operator_id: Optional[str] = None
        message: str
    
    # ---- 🔍 會話狀態查詢端點 ----
    
    class SessionStatusResponse(BaseModel):
        session_id: str
        manual_mode: bool
        operator_id: Optional[str] = None
        operator_name: Optional[str] = None
        operator_avatar: Optional[str] = None
        status: str
        started_at: Optional[str] = None
        mode_updated_at: Optional[str] = None
    
    @app.get("/api/repair/session/{session_id}/status", response_model=SessionStatusResponse)
    async def get_session_status(session_id: str):
        """
        查詢指定 session 的狀態
        
        用於前端輪詢檢測真人客服是否接手對話
        
        Args:
            session_id: 對話 session ID
        
        Returns:
            {
                "session_id": "session ID",
                "manual_mode": true/false,
                "operator_id": "客服人員 ID",
                "operator_name": "客服人員姓名",
                "operator_avatar": "客服人員頭像 URL",
                "status": "ongoing/completed/expired/cancelled",
                "started_at": "ISO 時間戳",
                "mode_updated_at": "ISO 時間戳"
            }
        """
        if not ENABLE_REPAIR_SERVICE:
            raise HTTPException(
                status_code=503,
                detail="維修服務未啟用"
            )
        
        try:
            from supabase_client import get_supabase_client
            client = get_supabase_client(prefer_service_role=True)
            
            # 查詢 repair_sessions 表
            response = client.table('repair_sessions')\
                .select('session_id, manual_mode, operator_id, operator_name, operator_avatar, status, started_at, mode_updated_at')\
                .eq('session_id', session_id)\
                .single()\
                .execute()
            
            if not response.data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {session_id} 不存在"
                )
            
            data = response.data
            
            return SessionStatusResponse(
                session_id=data.get('session_id'),
                manual_mode=data.get('manual_mode', False),
                operator_id=data.get('operator_id'),
                operator_name=data.get('operator_name'),
                operator_avatar=data.get('operator_avatar'),
                status=data.get('status', 'ongoing'),
                started_at=data.get('started_at'),
                mode_updated_at=data.get('mode_updated_at')
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[Repair] Get session status error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"查詢會話狀態失敗: {str(e)}"
            )
    
    @app.post("/api/repair/manual_mode", response_model=ManualModeResponse)
    async def toggle_manual_mode(req: ManualModeRequest):
        """
        切換對話模式（AI 自動 ⇄ 真人接手）
        
        當 manual_mode=True 時，表示客服人員接手對話
        當 manual_mode=False 時，表示恢復 AI 自動回覆
        
        Args:
            req: {
                "session_id": "對話 session ID",
                "manual_mode": true/false,
                "operator_id": "客服人員 ID（接手時需提供）",
                "operator_name": "客服人員名稱（接手時需提供）"
            }
        
        Returns:
            {
                "success": true,
                "session_id": "session ID",
                "manual_mode": true/false,
                "operator_id": "客服人員 ID",
                "message": "狀態訊息"
            }
        """
        if not ENABLE_REPAIR_SERVICE:
            raise HTTPException(
                status_code=503,
                detail="維修服務未啟用"
            )
        
        try:
            # 驗證 session_id
            if not req.session_id:
                raise HTTPException(
                    status_code=400,
                    detail="session_id 不可為空"
                )
            
            # 如果要切換為人工模式，需要 operator 資訊
            if req.manual_mode and not req.operator_id:
                raise HTTPException(
                    status_code=400,
                    detail="接手對話需提供 operator_id"
                )
            
            # 更新資料庫中的 session 狀態
            from supabase_client import get_supabase_client
            from datetime import datetime
            
            client = get_supabase_client(prefer_service_role=True)
            
            # 準備更新資料
            update_data = {
                'manual_mode': req.manual_mode,
                'mode_updated_at': datetime.utcnow().isoformat()
            }
            
            if req.manual_mode:
                # 切換為真人接手模式
                update_data['operator_id'] = req.operator_id
                update_data['operator_name'] = req.operator_name
            else:
                # 恢復 AI 自動模式，清除 operator 資訊
                update_data['operator_id'] = None
                update_data['operator_name'] = None
                update_data['operator_avatar'] = None
            
            # 更新 repair_sessions 表
            response = client.table('repair_sessions')\
                .update(update_data)\
                .eq('session_id', req.session_id)\
                .execute()
            
            if not response.data:
                # 如果 session 不存在，嘗試建立新的
                logger.warning(f"[Repair] Session {req.session_id} 不存在，嘗試建立")
                insert_data = {
                    'session_id': req.session_id,
                    'manual_mode': req.manual_mode,
                    'operator_id': req.operator_id if req.manual_mode else None,
                    'operator_name': req.operator_name if req.manual_mode else None,
                    'status': 'ongoing',
                    'started_at': datetime.utcnow().isoformat(),
                    'mode_updated_at': datetime.utcnow().isoformat()
                }
                client.table('repair_sessions').insert(insert_data).execute()
            
            mode_text = "真人接手" if req.manual_mode else "AI 自動回覆"
            operator_info = f"（{req.operator_name}）" if req.operator_name else ""
            
            logger.info(
                f"[Repair] Session {req.session_id} 切換模式: {mode_text} {operator_info}"
            )
            
            return ManualModeResponse(
                success=True,
                session_id=req.session_id,
                manual_mode=req.manual_mode,
                operator_id=req.operator_id,
                message=f"✅ 已切換為{mode_text}"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[Repair] Toggle manual mode error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"切換模式失敗: {str(e)}"
            )
    
    # ---- 💬 對話訊息查詢端點 ----
    
    class MessageItem(BaseModel):
        message_id: int
        session_id: str
        role: str  # 'user', 'llm', 'operator', 'system'
        content: str
        created_at: str
        emotion_data: Optional[Dict[str, Any]] = None

    class SessionMessagesResponse(BaseModel):
        session_id: str
        total_count: int
        messages: List[MessageItem]
    
    @app.get("/api/repair/session/{session_id}/messages", response_model=SessionMessagesResponse)
    def get_session_messages(
        session_id: str,
        limit: int = Query(100, ge=1, le=500, description="訊息數量限制")
    ):
        """
        查詢指定 session 的對話訊息
        
        Args:
            session_id: 對話 session ID
            limit: 返回訊息數量上限（預設 100，最多 500）
        
        Returns:
            {
                "session_id": "session ID",
                "total_count": 訊息總數,
                "messages": [
                    {
                        "message_id": 訊息 ID,
                        "session_id": "session ID",
                        "role": "user/llm/operator/system",
                        "content": "訊息內容",
                        "created_at": "ISO 時間戳"
                    },
                    ...
                ]
            }
        """
        if not ENABLE_REPAIR_SERVICE:
            raise HTTPException(
                status_code=503,
                detail="維修服務未啟用"
            )
        
        try:
            from supabase_client import get_supabase_client
            
            # 使用 service role 查詢
            client = get_supabase_client(prefer_service_role=True)
            
            # 查詢訊息（按時間升序排列，最早的在前）
            response = client.table('chat_messages')\
                .select('message_id, session_id, role, content, created_at, emotion_data')\
                .eq('session_id', session_id)\
                .eq('source_module', 'repair')\
                .order('created_at', desc=False)\
                .limit(limit)\
                .execute()
            
            messages = response.data or []
            
            return SessionMessagesResponse(
                session_id=session_id,
                total_count=len(messages),
                messages=[MessageItem(**msg) for msg in messages]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[Repair] Get session messages error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"查詢訊息失敗: {str(e)}"
            )
    
    # ---- 📤 發送客服回覆端點 ----
    
    class SendReplyResponse(BaseModel):
        success: bool
        message_id: Optional[int] = None
        session_id: str
        message: str
    
    @app.post("/api/repair/session/{session_id}/reply", response_model=SendReplyResponse)
    async def send_operator_reply(
        session_id: str,
        reply: str = Form(...),
        operator_id: str = Form(...),
        operator_name: str = Form(None)
    ):
        """
        發送客服人員回覆訊息
        
        Args:
            session_id: 對話 session ID
            reply: 回覆內容
            operator_id: 客服人員 ID
            operator_name: 客服人員名稱（選填）
        
        Returns:
            {
                "success": true,
                "message_id": 訊息 ID,
                "session_id": "session ID",
                "message": "狀態訊息"
            }
        """
        if not ENABLE_REPAIR_SERVICE:
            raise HTTPException(
                status_code=503,
                detail="維修服務未啟用"
            )
        
        reply_content = reply.strip()
        if not reply_content:
            raise HTTPException(
                status_code=400,
                detail="回覆內容不可為空"
            )
        
        try:
            from supabase_client import get_supabase_client
            
            # 使用 service role 插入訊息
            client = get_supabase_client(prefer_service_role=True)
            
            # 檢查資料庫是否支援 'Humans' role
            # 嘗試使用 Humans，如果失敗則降級到 llm + 前綴標記
            use_humans_role = os.getenv('USE_HUMANS_ROLE', 'True').lower() == 'true'
            
            if use_humans_role:
                # 新格式：直接使用 Humans role，不需要前綴
                insert_data = {
                    'session_id': session_id,
                    'role': 'Humans',  # ✅ 直接使用 Humans role（需要先執行 migration）
                    'content': reply_content,
                    'source_module': 'repair'
                }
            else:
                # 舊格式（向下相容）：使用 llm + 前綴標記
                operator_marker = f"[OPERATOR:{operator_name or operator_id}]"
                content_with_marker = f"{operator_marker}{reply_content}"
                insert_data = {
                    'session_id': session_id,
                    'role': 'llm',
                    'content': content_with_marker,
                    'source_module': 'repair'
                }
            
            response = client.table('chat_messages')\
                .insert(insert_data)\
                .execute()
            
            if not response.data:
                raise Exception("插入訊息失敗")
            
            message_id = response.data[0].get('message_id') if response.data else None
            
            # 🆕 自動設定 manual_mode = True（如果還沒接手）
            # 確保客服回覆時，客戶端能收到真人接手通知
            try:
                from datetime import datetime
                
                # 檢查 session 是否已接手
                session_check = client.table('repair_sessions')\
                    .select('manual_mode')\
                    .eq('session_id', session_id)\
                    .single()\
                    .execute()
                
                if session_check.data and not session_check.data.get('manual_mode'):
                    # 尚未接手，自動設為接手狀態
                    client.table('repair_sessions').update({
                        'manual_mode': True,
                        'operator_id': operator_id,
                        'operator_name': operator_name or operator_id,
                        'mode_updated_at': datetime.utcnow().isoformat()
                    }).eq('session_id', session_id).execute()
                    
                    logger.info(f"[Repair] Auto-set manual_mode for session {session_id}")
                    
            except Exception as e:
                # 不影響主流程
                logger.warning(f"[Repair] Failed to auto-set manual_mode: {e}")
            
            logger.info(
                f"[Repair] Operator {operator_id} sent reply to session {session_id}"
            )
            
            return SendReplyResponse(
                success=True,
                message_id=message_id,
                session_id=session_id,
                message="✅ 回覆已送出"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[Repair] Send operator reply error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"發送回覆失敗: {str(e)}"
            )

# ---- 🎙️ 語音模式 API 端點 ----

VOICE_ALLOWED_CONTENT_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/mpeg",
    "audio/mp4",
    "audio/x-m4a",
}
VOICE_MAX_AUDIO_BYTES = 5 * 1024 * 1024  # 約 30 秒 webm


def _ensure_voice_enabled() -> Dict[str, Any]:
    branding = config_store.load_branding_config()
    if not branding.get("voice_mode_enabled"):
        raise HTTPException(status_code=403, detail="語音模式未啟用")
    return branding


async def _read_audio_bytes(upload: UploadFile) -> bytes:
    if upload.content_type and upload.content_type not in VOICE_ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="音訊格式不支援，請使用 webm/wav/mp3")
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail="音訊資料為空")
    if len(data) > VOICE_MAX_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="音訊長度超過可允許範圍（最多 30 秒）")
    return data


@app.post("/api/voice/transcribe")
async def voice_transcribe(audio: UploadFile):
    """Whisper-only transcription endpoint used by the new voice mode."""
    from voice_service import transcribe_audio, VoiceServiceError

    _ensure_voice_enabled()
    audio_data = await _read_audio_bytes(audio)
    try:
        return await transcribe_audio(audio_data)
    except VoiceServiceError as exc:
        logger.error(f"語音轉文字失敗: {exc}")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/voice/chat")
async def voice_chat(
    audio: UploadFile,
    session_id: Optional[str] = Form(None),
    history: Optional[str] = Form(None),
):
    """
    One-shot voice flow: audio → Whisper → chat → voice directives.
    """
    from voice_service import transcribe_audio, VoiceServiceError

    _ensure_voice_enabled()
    audio_data = await _read_audio_bytes(audio)
    try:
        transcription = await transcribe_audio(audio_data)
    except VoiceServiceError as exc:
        logger.error(f"語音聊天失敗 (STT): {exc}")
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    recognized_text = (transcription.get("text") or "").strip()
    if not recognized_text:
        raise HTTPException(status_code=400, detail="無法辨識音訊內容")

    history_list: List[Dict[str, Any]] = []
    if history:
        import json

        try:
            parsed = json.loads(history)
            if isinstance(parsed, list):
                history_list = parsed
        except Exception:
            logger.warning("語音模式 history 解析失敗，已忽略。")

    chat_req = ChatReq(
        message=recognized_text,
        session_id=session_id,
        history=history_list,
        voice_mode=True,
    )

    chat_response = chat_endpoint(chat_req)
    if isinstance(chat_response, ChatResp):
        payload = chat_response.model_dump()
    elif isinstance(chat_response, JSONResponse):
        return chat_response
    elif isinstance(chat_response, dict):
        payload = dict(chat_response)
    else:
        payload = {"reply": str(chat_response)}

    payload["recognized_text"] = recognized_text
    return payload

# ---- Catalog taxonomy endpoint ----
@app.get("/api/catalog/taxonomy")
def get_catalog_taxonomy():
    """
    返回產品分類樹狀結構 (三層級: L1 > L2 > L3)
    
    使用 constants.py 中的欄位對應定義，支援多種欄位名稱格式
    
    Returns:
        {
          "levels": ["L1", "L2", "L3"],
          "count": 953,
          "tree": {
            "常溫食品": {
              "count": 514,
              "children": {...}
            }
          }
        }
    """
    df = get_df()
    if df is None or df.empty:
        return JSONResponse({"levels": [], "count": 0, "tree": {}})
    
    # 🔄 使用 constants 取得欄位對應
    hierarchy_cols = get_hierarchy_columns()
    
    # 自動偵測可用的欄位
    l1_col = None
    l2_col = None
    l3_col = None
    
    for level, col in hierarchy_cols.items():
        variants = get_all_column_variants(level)
        for variant in variants:
            if variant in df.columns:
                if level == "L1":
                    l1_col = variant
                elif level == "L2":
                    l2_col = variant
                elif level == "L3":
                    l3_col = variant
                break
    
    tree: Dict[str, Any] = {}
    total = int(len(df.index))
    
    if l1_col:
        for l1_val, grp1 in df.groupby(l1_col):
            l1_name = str(l1_val or "未分類").strip() or "未分類"
            node1 = tree.setdefault(l1_name, {"count": 0, "children": {}})
            node1["count"] += int(len(grp1.index))
            if l2_col:
                for l2_val, grp2 in grp1.groupby(l2_col):
                    l2_name = str(l2_val or "").strip() or "—"
                    node2 = node1["children"].setdefault(l2_name, {"count": 0, "children": {}})
                    node2["count"] += int(len(grp2.index))
                    if l3_col:
                        for l3_val, grp3 in grp2.groupby(l3_col):
                            l3_name = str(l3_val or "").strip() or "—"
                            node3 = node2["children"].setdefault(l3_name, {"count": 0})
                            node3["count"] += int(len(grp3.index))
    else:
        # fallback to single-level CateName
        base = "CateName" if "CateName" in df.columns else ("分類名稱" if "分類名稱" in df.columns else None)
        if base:
            for val, grp in df.groupby(base):
                name = str(val or "未分類").strip() or "未分類"
                tree[name] = {"count": int(len(grp.index))}
    
    levels = [c for c in [l1_col and "L1", l2_col and "L2", l3_col and "L3"] if c]
    return JSONResponse({"levels": levels, "count": total, "tree": tree})

# ---- Flat scope endpoint (L1/L2/L3) ----
@app.get("/api/catalog/scope")
def get_catalog_scope(level: str = "L1", top_k: Optional[int] = None, parent_l1: Optional[str] = None, parent_l2: Optional[str] = None):
    """
    返回扁平的分類清單，來源：goods_categories.csv（權威分類）
    - 不再從商品 CSV 推導
    - 不返回 count（簡化）
    - 支援全量（top_k<=0 或未傳）
    - 提供 context（level/parent 與標題 label），避免前端出現（null）
    """
    try:
        data = categories_service.get_scope(level=level, parent_l1=parent_l1, parent_l2=parent_l2, top_k=top_k)
        return JSONResponse(data)
    except Exception as e:
        # CSV 壞檔或缺失時，回傳空清單而非 500
        logging.getLogger("search_goods").warning("categories scope error: %s", e)
        context = {"level": (level or "L1").upper(), "parent_l1": parent_l1, "parent_l2": parent_l2, "label": "熱門分類" if (level or "L1").upper()=="L1" else "熱門中分類"}
        return JSONResponse({"level": (level or "L1").upper(), "total": 0, "top_k": int(top_k or 0), "more_count": 0, "items": [], "context": context})

# ---- 新增會話結果檢索 endpoint ----
@app.get("/api/chat-session/{session_id}", response_model=ChatSessionResp)
def get_chat_session_endpoint(session_id: str):
    """
    取得指定會話內容，統一回傳 JSON：
    {
      "session_id": "xxxx",
      "history": [ { "role":"user","content":"..." }, ... ]
    }
    """
    try:
        session_data = get_chat_result_by_session(session_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found or expired")
            
        # 格式化歷史記錄
        history = []
        if isinstance(session_data, dict):
            # 將會話數據轉換為標準對話歷史格式
            if "category_suggestions" in session_data:
                history.append({
                    "role": "assistant", 
                    "content": f"建議分類: {session_data.get('category_suggestions', {})}"
                })
        
        return ChatSessionResp(
            session_id=session_id,
            history=history
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---- Mount frontend static files after all API routes so they don't intercept /api/* ----
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
