# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple
import json
import re
import time

from planner.event_food_planner import (
    EventContext,
    generate_event_plan,
    parse_event_context,
)


SUFFIX_JSON_RE = re.compile(r'(\{[\s\S]*\})\s*$')


def _strip_structured_suffix(reply_text: str) -> str:
    """移除 LLM 在文字回覆尾端附帶的 JSON 結構"""

    if not isinstance(reply_text, str):
        return reply_text

    candidate = reply_text.rstrip()
    if not candidate.endswith('}'):
        return reply_text

    match = SUFFIX_JSON_RE.search(candidate)
    if not match:
        return reply_text

    try:
        json.loads(match.group(1))
    except json.JSONDecodeError:
        return reply_text

    return candidate[: match.start()].rstrip()


EVENT_SESSION_STATE: Dict[str, Dict[str, Any]] = {}
EVENT_STATE_TTL_SECONDS = 1800


def _get_event_state(session_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not session_id:
        return None
    state = EVENT_SESSION_STATE.get(session_id)
    now = time.time()
    if state and now - state.get("updated_at", now) > EVENT_STATE_TTL_SECONDS:
        EVENT_SESSION_STATE.pop(session_id, None)
        state = None
    if not state:
        state = {
            "context": None,
            "preferences": {},
            "pending_fields": [],
            "pending_preferences": [],
            "updated_at": now,
        }
        EVENT_SESSION_STATE[session_id] = state
    state["updated_at"] = now
    return state


def _clear_event_state(session_id: Optional[str]) -> None:
    if session_id and session_id in EVENT_SESSION_STATE:
        EVENT_SESSION_STATE.pop(session_id, None)


def prepare_information_response(
    llm_result: Dict[str, Any],
    user_text: str,
    structured_filters: Dict[str, Any],
    fetch_items_for_reply: Callable[[Optional[List[Dict[str, Any]]], List[str]], List[Dict[str, Any]]],
    session_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[str], Optional[Dict[str, Any]]]:
    """
    活動建議／資訊導購模式的回應組裝：
    - 若提醒使用者補資料則回傳追問
    - 若有完整資訊，呼叫活動 planner 建議商品組
    - 否則維持原本資訊回覆
    """
    suggestion_ids: List[str] = []
    intent = llm_result.get("intent")
    structured_payload = llm_result.get("structured_payload")
    info_preview: Optional[Dict[str, Any]] = None

    if structured_payload and intent == "event_food_planning":
        suggestion_ids = [
            str(item.get("商品編號") or item.get("GoodIden") or "").strip()
            for item in structured_payload.get("items", [])
            if str(item.get("商品編號") or item.get("GoodIden") or "").strip()
        ]
    elif structured_payload:
        # 一般資訊意圖僅回傳文字，不帶商品卡；保留預覽於 meta 供除錯
        info_preview = structured_payload
        structured_payload = None

    resp: Dict[str, Any] = {
        "ok": True,
        "reply": llm_result.get("reply", ""),
        "suggestion_ids": suggestion_ids,
        "meta": {
            "has_budget_intent": False,
            "intent": intent,
            "intent_subtype": llm_result.get("intent_subtype"),
        },
        "action": {"type": "none"},
    }

    if info_preview:
        resp["meta"]["info_preview"] = info_preview
        resp["reply"] = _strip_structured_suffix(resp["reply"])

    if structured_payload:
        resp["structured_payload"] = structured_payload
    if structured_filters:
        resp["structured_filters"] = structured_filters
    status_hint = llm_result.get("status")
    if status_hint:
        resp["status"] = status_hint

    if intent == "event_food_planning":
        return _handle_event_mode(resp, llm_result, user_text, session_id)

    return resp, suggestion_ids, structured_payload


def _handle_event_mode(
    resp: Dict[str, Any],
    llm_result: Dict[str, Any],
    user_text: str,
    session_id: Optional[str],
) -> Tuple[Dict[str, Any], List[str], Optional[Dict[str, Any]]]:
    """
    處理活動導購模式：追問或推活動方案。
    """
    state = _get_event_state(session_id)
    existing_context: Optional[EventContext] = None
    if state and isinstance(state.get("context"), EventContext):
        existing_context = state["context"]

    event_context = _extract_event_context(llm_result, user_text, existing_context)
    missing = _missing_fields(event_context)
    if missing:
        resp["reply"] = _build_followup_question(event_context, missing)
        resp["meta"]["pending_fields"] = missing
        resp["meta"]["mode"] = "event_food_planning"
        resp["suggestion_ids"] = []
        resp["action"] = {"type": "none"}
        if state:
            state["context"] = event_context
            state["pending_fields"] = missing
            state["meta_snapshot"] = resp["meta"]
        return resp, [], None

    if state:
        state["context"] = event_context
        state["pending_fields"] = []

    preferences = state.get("preferences", {}) if state else {}
    detected_prefs = _extract_event_preferences(user_text)
    if detected_prefs:
        preferences.update(detected_prefs)
        if state:
            state["preferences"] = preferences

    pending_preferences = [
        key for key in ("heat_option", "beverage_style") if key not in preferences
    ]
    if pending_preferences:
        question = _build_preference_followup(pending_preferences)
        resp["reply"] = question
        resp["meta"]["mode"] = "event_food_planning"
        resp["meta"]["pending_preferences"] = pending_preferences
        resp["suggestion_ids"] = []
        resp["action"] = {"type": "none"}
        if state:
            state["pending_preferences"] = pending_preferences
        return resp, [], None

    plan = _build_event_plan(event_context)
    if not plan:
        resp["reply"] = "我暫時找不到適合的搭配，先確認資料或換個方向試試？"
        resp["meta"]["mode"] = "event_food_planning"
        resp["action"] = {"type": "none"}
        return resp, [], None

    formatted_reply, plan_payload, plan_ids = _format_event_plan(
        plan, event_context, preferences
    )
    resp["reply"] = formatted_reply
    resp["structured_payload"] = plan_payload
    resp["meta"]["mode"] = "event_food_planning"
    resp["meta"]["event_context"] = event_context.__dict__
    resp["meta"]["planner_used"] = True
    resp["meta"]["event_preferences"] = preferences
    resp["meta"]["directional_products"] = True
    if event_context.budget_total:
        resp["meta"]["has_budget_intent"] = True
    resp["suggestion_ids"] = plan_ids
    structured_products = plan_payload.get("items", []) if plan_payload else []
    if structured_products:
        resp["structured_products"] = structured_products
        resp["items"] = structured_products
    if plan_ids:
        resp["action"] = {
            "type": "switch_to_search",
            "items": [{"id": sid} for sid in plan_ids],
        }
    else:
        resp["action"] = {"type": "none"}
    if state:
        _clear_event_state(session_id)
    return resp, plan_ids, plan_payload


def _extract_event_context(
    llm_result: Dict[str, Any],
    user_text: str,
    base_context: Optional[EventContext] = None,
) -> EventContext:
    meta_context = llm_result.get("meta", {}).get("event_context") or {}
    if base_context:
        context = EventContext(
            activity_type=base_context.activity_type,
            people_count=base_context.people_count,
            budget_total=base_context.budget_total,
            audience=base_context.audience,
            keywords=list(base_context.keywords or []),
        )
    else:
        context = EventContext(
            activity_type=meta_context.get("activity_type"),
            people_count=meta_context.get("people_count"),
            budget_total=meta_context.get("budget_total"),
            audience=meta_context.get("audience"),
            keywords=[],
        )

    parsed = parse_event_context(user_text)
    context.activity_type = context.activity_type or parsed.activity_type
    context.people_count = context.people_count or parsed.people_count
    context.budget_total = context.budget_total or parsed.budget_total
    context.audience = context.audience or parsed.audience
    if parsed.keywords:
        context.keywords = parsed.keywords
    return context


def _missing_fields(context: EventContext) -> List[str]:
    missing = []
    if not context.activity_type:
        missing.append("activity_type")
    if not context.people_count:
        missing.append("people_count")
    if not context.budget_total:
        missing.append("budget_total")
    return missing


def _build_followup_question(context: EventContext, missing: List[str]) -> str:
    prompts = []
    if "activity_type" in missing:
        prompts.append("這場活動大概是什麼性質呢？（親子園遊會 / 公司活動 / 生日派對…）")
    if "people_count" in missing:
        prompts.append("預估會有多少人參加？")
    if "budget_total" in missing:
        prompts.append("整體準備的預算大概抓多少？")

    prefix = "了解，你正在規劃活動餐飲，我可以幫你搭配最受歡迎的組合！"
    return prefix + "\n\n" + "\n".join(f"• {question}" for question in prompts)


def _build_preference_followup(pending_preferences: List[str]) -> str:
    lines: List[str] = []
    if "heat_option" in pending_preferences:
        lines.append(
            "A. 🍴 **即食型派對**（免加熱、拆封即食）\n"
            "B. 🔥 **可加熱派對**（有烤箱或微波爐，可提供熱食）"
        )
    if "beverage_style" in pending_preferences:
        lines.append(
            "C. 🫘 **豆奶／穀飲系列**（暖心健康）\n"
            "D. 🍹 **果汁／氣泡飲系列**（清爽解膩）\n"
            "E. ☕ **兩種都要**（滿足不同口味）"
        )

    prompt_intro = (
        "為了幫你排出最適合的採購清單，再確認一下派對設定：\n"
        "👉 回覆時請輸入對應的英文字母（例如 A、B、C…）。"
    )
    return prompt_intro + "\n\n" + "\n\n".join(lines)


def _build_event_plan(context: EventContext) -> Optional[Dict[str, Any]]:
    try:
        from app import get_df

        df = get_df()
        if df is None or df.empty:
            return None
        return generate_event_plan(context, df)
    except Exception as exc:
        print(f"[WARNING] Failed to generate event plan: {exc}")
        return None


def _format_event_plan(
    plan: Dict[str, Any],
    context: EventContext,
    preferences: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any], List[str]]:
    reply_lines: List[str] = []
    if preferences:
        heat = preferences.get("heat_option")
        beverage = preferences.get("beverage_style")
        pref_desc = []
        if heat == "no_heat":
            pref_desc.append("即食派對")
        elif heat == "needs_heat":
            pref_desc.append("可加熱派對")
        if beverage == "grain":
            pref_desc.append("豆奶穀飲飲品")
        elif beverage == "juice":
            pref_desc.append("果汁氣泡飲品")
        elif beverage == "both":
            pref_desc.append("雙飲品路線")
        if pref_desc:
            reply_lines.append(f"🎉 生日派對採購建議（{' + '.join(pref_desc)}）")
            reply_lines.append("")

    if context.people_count:
        reply_lines.append(f"服務人數：{context.people_count} 位")
    if context.budget_total:
        reply_lines.append(f"目標預算：約 {context.budget_total} 元")
    if context.activity_type:
        reply_lines.append(f"活動情境：{context.activity_type}")
    if reply_lines:
        reply_lines.append("")

    if plan.get("summary"):
        reply_lines.append(plan["summary"])
        reply_lines.append("")

    items = plan.get("items", [])
    suggestion_ids: List[str] = []
    for idx, item in enumerate(items, 1):
        product_id = item.get("商品編號")
        name = item.get("商品名稱")
        price = item.get("售價")
        special = item.get("特價")
        highlight = item.get("行銷亮點", "")
        link = item.get("購物網址", "")

        lines = [
            f"{idx}. {name}",
            f"   • 建議價：{price} 元" if price else "",
            f"   • 特價：{special} 元" if special else "",
            f"   • 亮點：{highlight}" if highlight else "",
            f"   • 購買連結：{link}" if link else "",
        ]
        reply_lines.append("\n".join([segment for segment in lines if segment]))

        if product_id:
            suggestion_ids.append(str(product_id))

    if plan.get("total_cost"):
        reply_lines.append("")
        reply_lines.append(f"預估總金額：約 {plan['total_cost']} 元（實際金額以下單時為準）")

    if plan.get("slogan"):
        reply_lines.append(plan["slogan"])
    if plan.get("cta"):
        reply_lines.append(plan["cta"])

    structured_items: List[Dict[str, Any]] = []
    for item in items:
        product_id = item.get("商品編號")
        name = item.get("商品名稱")
        category = item.get("分類名稱") or ""
        unit_price = _safe_int(item.get("特價") or item.get("售價"))
        quantity = _estimate_quantity(context)
        subtotal = unit_price * quantity if unit_price else None
        structured_items.append(
            {
                "product_id": product_id,
                "name": name,
                "category": category,
                "unit_price": unit_price,
                "quantity": quantity,
                "subtotal": subtotal,
                "notes": item.get("行銷亮點"),
                "link": item.get("購物網址"),
            }
        )

    structured_payload = {
        "summary": plan.get("summary"),
        "items": structured_items,
        "estimated_total": plan.get("total_cost"),
        "slogan": plan.get("slogan"),
        "cta": plan.get("cta"),
        "preferences": preferences or {},
        "people_count": context.people_count,
    }

    return "\n".join(reply_lines), structured_payload, suggestion_ids


def _safe_int(value: Any) -> Optional[int]:
    if value in (None, "", 0):
        return None
    try:
        return int(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _estimate_quantity(context: EventContext) -> int:
    people = context.people_count or 0
    if people <= 0:
        return 1
    return max(1, round(people / 10))


def _extract_event_preferences(user_text: str) -> Dict[str, str]:
    normalized = re.sub(r"\s+", "", user_text.lower())
    prefs: Dict[str, str] = {}

    heat_map = {
        "a": "no_heat",
        "即食": "no_heat",
        "免加熱": "no_heat",
        "b": "needs_heat",
        "加熱": "needs_heat",
        "烤箱": "needs_heat",
        "微波": "needs_heat",
    }
    for keyword, value in heat_map.items():
        if keyword and keyword in normalized:
            prefs["heat_option"] = value
            break

    beverage_letter_map = {
        "c": "grain",
        "豆奶": "grain",
        "穀飲": "grain",
        "d": "juice",
        "果汁": "juice",
        "氣泡": "juice",
        "e": "both",
        "都要": "both",
        "雙": "both",
    }
    for keyword, value in beverage_letter_map.items():
        if keyword and keyword in normalized:
            prefs["beverage_style"] = value
            break

    beverage_numeric_patterns = [
        (r"(?<!\d)3(?!\d)", "both"),
        (r"(?<!\d)2(?!\d)", "juice"),
        (r"(?<!\d)1(?!\d)", "grain"),
    ]
    if "beverage_style" not in prefs:
        for pattern, value in beverage_numeric_patterns:
            if re.search(pattern, normalized):
                prefs["beverage_style"] = value
                break

    return prefs
