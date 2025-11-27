# -*- coding: utf-8 -*-
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from services import catalog_service
from field_utils import FieldAccessor

LOGGER = logging.getLogger(__name__)


def prepare_shopping_response(
    llm_result: Dict[str, Any],
    user_text: str,
    structured_filters: Dict[str, Any],
    planner_intent: Optional[Any],
    party_context: bool,
    has_budget_intent: Callable[[str], bool],
    fetch_items_for_reply: Callable[[Optional[List[Dict[str, Any]]], List[str]], List[Dict[str, Any]]],
    compose_structured_reply: Callable[[List[Dict[str, Any]], bool, str], Tuple[str, Dict[str, Any]]],
    invoke_category_planner: Callable[[Optional[Any]], Optional[Dict[str, Any]]],
    merge_planner_reply: Callable[[str, Dict[str, Any], List[str]], str],
) -> Tuple[Dict[str, Any], List[str], Optional[Dict[str, Any]]]:
    """
    商品導購模式：負責決定是否使用 Planner、組裝回應與結構化 payload。
    """
    suggestion_ids: List[str] = []
    alignment = llm_result.get("alignment")
    if alignment and alignment.get("items"):
        suggestion_ids = [item.get("id") for item in alignment["items"] if item.get("id")]

    suggestion_ids = _filter_suggestion_ids_by_hierarchy(suggestion_ids, structured_filters)

    llm_meta = llm_result.get("meta") or {}
    planner_payload: Optional[Dict[str, Any]] = None
    planner_used = False
    has_llm_suggestions = bool(suggestion_ids)

    planner_triggered = (
        (not has_llm_suggestions and planner_intent and getattr(planner_intent, "confidence", 0) >= 0.3)
        or llm_meta.get("needs_planner")
    )
    if planner_triggered:
        planner_payload = invoke_category_planner(planner_intent)
        if planner_payload and not has_llm_suggestions:
            planner_used = True
            if planner_payload.get("suggestion_ids"):
                suggestion_ids = _filter_suggestion_ids_by_hierarchy(
                    planner_payload["suggestion_ids"],
                    structured_filters,
                )
                has_llm_suggestions = bool(suggestion_ids)

    # 僅在 product_search 時才允許切換到商品模式
    action_payload = llm_result.get("action")
    llm_intent = (llm_result.get("intent") or "").lower()
    if llm_intent == "product_search" and suggestion_ids and (not action_payload or action_payload.get("type") in (None, "", "none")):
        action_payload = {
            "type": "switch_to_search",
            "items": [{"id": sid} for sid in suggestion_ids],
        }
    else:
        # 資訊/概覽/OOS 模式下統一保持聊天模式
        if not action_payload:
            action_payload = {"type": "none"}

    resp_meta: Dict[str, Any] = {
        "has_budget_intent": has_budget_intent(user_text),
        "planner_used": planner_used,
        "planner_triggered": planner_triggered,
        "party_context": party_context,
    }
    if planner_intent:
        resp_meta["detected_intent"] = {
            "categories": getattr(planner_intent, "categories", []),
            "budget": getattr(planner_intent, "budget", None),
            "urgency": getattr(planner_intent, "urgency", False),
            "confidence": getattr(planner_intent, "confidence", 0.0),
            "matched_keywords": getattr(planner_intent, "matched_keywords", {}),
        }

    resp: Dict[str, Any] = {
        "ok": True,
        "reply": llm_result.get("reply", ""),
        "suggestion_ids": suggestion_ids,
        "meta": resp_meta,
        "action": action_payload,
    }
    if structured_filters:
        resp["structured_filters"] = structured_filters
    status_hint = llm_result.get("status")
    if status_hint:
        resp["status"] = status_hint

    structured_payload: Optional[Dict[str, Any]] = None
    if planner_used and planner_payload:
        structured_payload = planner_payload.get("structured_payload")
        if structured_payload:
            resp["structured_payload"] = structured_payload
            # 🔧 確保 Planner 商品資料也傳遞到 structured_products 欄位
            if structured_payload.get("items"):
                resp["structured_products"] = structured_payload["items"]
        suggestions = planner_payload.get("suggestions") or []
        resp["reply"] = merge_planner_reply(resp["reply"], planner_payload, suggestions)
        planner_notes = planner_payload.get("notes") or {}
        if planner_notes:
            resp["meta"]["planner_notes"] = planner_notes
        if suggestions:
            resp["meta"]["planner_suggestions"] = suggestions
    elif suggestion_ids:
        detailed_items = fetch_items_for_reply(None, suggestion_ids)
        if not detailed_items:
            try:
                from goods_search_service import load_goods_rows

                raw_rows = load_goods_rows()
                if raw_rows:
                    row_map = {
                        str(row.get("GoodIden") or row.get("商品編號") or "").strip(): row
                        for row in raw_rows
                    }
                    detailed_items = [
                        row_map[sid] for sid in suggestion_ids if row_map.get(sid)
                    ]
            except Exception:
                detailed_items = []
        if detailed_items:
            detailed_items = _filter_items_by_primary_l3(detailed_items)
            formatted_reply, structured_payload = compose_structured_reply(detailed_items, True, user_text)
            resp["reply"] = formatted_reply
            resp["structured_payload"] = structured_payload
            # 🔧 確保商品資料也傳遞到 structured_products 欄位
            if structured_payload and structured_payload.get("items"):
                resp["structured_products"] = structured_payload["items"]

    return resp, suggestion_ids, structured_payload


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _extract_hierarchy_filters(structured_filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    if not structured_filters or not isinstance(structured_filters, dict):
        return None
    raw = structured_filters.get("category_hierarchy") or structured_filters.get("hierarchy")
    if not isinstance(raw, dict):
        return None
    hierarchy: Dict[str, str] = {}
    for level in ("L1", "L2", "L3"):
        val = raw.get(level) or raw.get(level.lower())
        norm = _normalize_text(val)
        if norm:
            hierarchy[level] = norm
    return hierarchy or None


def _match_record_hierarchy(record: Dict[str, Any], hierarchy: Dict[str, str]) -> bool:
    if not hierarchy:
        return True

    def pick_value(keys: List[str]) -> str:
        for key in keys:
            val = record.get(key)
            if val:
                norm = _normalize_text(val)
                if norm:
                    return norm
        return ""

    level_map = {
        "L1": pick_value(["CateName_L1", "大分類名稱", "L1"]),
        "L2": pick_value(["CateName_L2", "中分類名稱", "L2"]),
        "L3": pick_value(["CateName_L3", "小分類名稱", "L3"]),
    }
    for level, target in hierarchy.items():
        if not target:
            continue
        if level_map.get(level) != target:
            return False
    return True


def _filter_suggestion_ids_by_hierarchy(
    suggestion_ids: Optional[List[str]], structured_filters: Optional[Dict[str, Any]]
) -> List[str]:
    hierarchy = _extract_hierarchy_filters(structured_filters)
    if not suggestion_ids or not hierarchy:
        return suggestion_ids or []

    normalized_ids = [str(sid or "").strip() for sid in suggestion_ids if str(sid or "").strip()]
    if not normalized_ids:
        return []
    try:
        rows = catalog_service.get_items_by_ids(normalized_ids)
    except Exception as exc:  # pragma: no cover - 防護
        LOGGER.warning("Failed to load catalog rows for hierarchy filter: %s", exc)
        return normalized_ids

    allowed: List[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        product_id = _normalize_text(row.get("GoodIden") or row.get("商品編號"))
        if not product_id:
            continue
        if _match_record_hierarchy(row, hierarchy):
            allowed.append(product_id)

    if not allowed:
        LOGGER.info(
            "Hierarchy filter removed all suggestion ids (L1=%s, L2=%s, L3=%s) — falling back to original order",
            hierarchy.get("L1"),
            hierarchy.get("L2"),
            hierarchy.get("L3"),
        )
        return normalized_ids

    allowed_set = set(allowed)
    filtered = [sid for sid in normalized_ids if sid in allowed_set]
    if len(filtered) != len(normalized_ids):
        LOGGER.info(
            "Hierarchy filter removed %d suggestion ids (kept %d)",
            len(normalized_ids) - len(filtered),
            len(filtered),
        )
    return filtered


def _filter_items_by_primary_l3(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """依主要 L3 小分類過濾推薦商品，避免不同類別混入。"""
    l3_labels = [
        FieldAccessor.get_category_l3(item).strip()
        for item in items
        if FieldAccessor.get_category_l3(item)
    ]
    if not l3_labels:
        return items
    # 取出第一個非空 L3，若不存在則使用出現最多的 L3
    primary_l3 = next((label for label in l3_labels if label), None)
    if not primary_l3:
        primary_l3 = max(set(l3_labels), key=l3_labels.count)
    filtered = [
        item for item in items if FieldAccessor.get_category_l3(item).strip() == primary_l3
    ]
    return filtered or items
