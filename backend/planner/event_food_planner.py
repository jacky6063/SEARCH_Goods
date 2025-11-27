# -*- coding: utf-8 -*-
"""
活動/情境導購專用 Planner。
根據活動型態、預算、人數等資訊，組合適合的商品列表。
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

from field_utils import FieldAccessor


@dataclass
class EventContext:
    activity_type: Optional[str] = None
    people_count: Optional[int] = None
    budget_total: Optional[int] = None
    audience: Optional[str] = None
    keywords: List[str] = None

    def is_complete(self) -> bool:
        return all(
            [
                self.activity_type,
                self.people_count and self.people_count > 0,
                self.budget_total and self.budget_total > 0,
            ]
        )


# 活動類型對應的分類關鍵字
EVENT_CATEGORY_RULES: List[Tuple[List[str], List[str]]] = [
    (["園遊", "市集", "攤"], ["零食", "餅乾", "飲料", "甜點"]),
    (["親子", "兒童", "小朋友"], ["餅乾", "零食", "果汁", "甜點"]),
    (["公司", "同事", "商務", "貴賓"], ["禮盒", "茶", "咖啡", "精緻點心"]),
    (["戶外", "夏", "熱"], ["飲料", "果汁", "清涼", "即飲"]),
    (["派對", "生日", "慶祝"], ["甜點", "餅乾", "飲料"]),
    (["健康", "養生", "無添加"], ["有機", "健康", "低糖"]),
]


def parse_event_context(text: str) -> EventContext:
    """
    從使用者自然語言中提取活動資訊。
    """
    context = EventContext(keywords=[])
    lowered = text.lower()

    # 活動類型
    for keywords, _ in EVENT_CATEGORY_RULES:
        if any(kw in lowered for kw in keywords):
            context.activity_type = keywords[0]
            context.keywords.extend(keywords)
            break

    # 參與人數
    people_match = re.search(r"(\d{1,4})\s*(?:人|位|家庭|組)", text)
    if people_match:
        context.people_count = int(people_match.group(1))

    # 預算（總額）
    budget_match = None
    budget_keywords_pattern = re.compile(
        r"(預算|金額|價位|花費|預估花費|budget)\s*[:：]?\s*([\d,\.]{3,})",
        re.IGNORECASE,
    )
    keyword_match = budget_keywords_pattern.search(text)
    if keyword_match:
        budget_match = keyword_match.group(2)

    if not budget_match:
        trailing_pattern = re.compile(r"([\d,\.]{3,})\s*(?:元|塊|nt|臺幣|台幣)", re.IGNORECASE)
        trailing_match = trailing_pattern.search(text)
        if trailing_match:
            budget_match = trailing_match.group(1)

    if budget_match:
        try:
            digits_only = re.sub(r"[^\d]", "", budget_match)
            if digits_only:
                context.budget_total = int(digits_only)
        except ValueError:
            pass

    # 受眾
    if any(kw in lowered for kw in ["親子", "兒童", "小朋友", "小孩"]):
        context.audience = "親子"
    elif any(kw in lowered for kw in ["同事", "員工", "公司"]):
        context.audience = "同事"
    elif any(kw in lowered for kw in ["顧客", "客人", "一般大眾"]):
        context.audience = "一般客人"

    return context


def generate_event_plan(context: EventContext, df) -> Optional[Dict[str, any]]:
    """
    根據活動資訊從商品資料中挑選推薦列表。
    """
    if not context or df is None or df.empty:
        return None

    # 估算每人預算，預留 10% 邊際
    per_person_budget = None
    if context.budget_total and context.people_count:
        per_person_budget = max(10, math.floor(context.budget_total / context.people_count * 0.9))

    candidates = _select_candidates(context, df, per_person_budget)
    if not candidates:
        return None

    total_cost = 0
    for item in candidates:
        effective = item.get("特價") or item.get("售價") or 0
        try:
            total_cost += int(effective)
        except (TypeError, ValueError):
            continue

    return {
        "summary": _build_summary(context, per_person_budget, len(candidates)),
        "items": candidates,
        "total_cost": total_cost,
        "slogan": _build_slogan(context),
        "cta": "需要我幫你整理成一鍵下單清單嗎？",
    }


def _select_candidates(context: EventContext, df, per_person_budget: Optional[int]) -> List[Dict[str, any]]:
    """
    依活動資料挑選商品。
    """
    selected: List[Dict[str, any]] = []

    matched_categories = []
    for keywords, categories in EVENT_CATEGORY_RULES:
        if context.activity_type and any(kw in context.activity_type for kw in keywords):
            matched_categories = categories
            break
    if not matched_categories:
        matched_categories = ["餅乾", "飲料", "零食"]

    for category_keyword in matched_categories:
        subset = df[df["CateName"].astype(str).str.contains(category_keyword, na=False)].copy()
        if per_person_budget:
            price_numbers = pd.to_numeric(
                subset["Price"].astype(str).str.extract(r"(\d+)")[0], errors="coerce"
            ).fillna(0)
            subset = subset[price_numbers <= per_person_budget]

        if subset.empty:
            continue

        # 優先有特價的商品
        price_values = pd.to_numeric(
            subset["Price"].astype(str).str.extract(r"(\d+)")[0], errors="coerce"
        ).fillna(0)
        special_values = pd.to_numeric(
            subset["SpecialOffer"].astype(str).str.extract(r"(\d+)")[0], errors="coerce"
        ).fillna(0)

        subset["PriceValue"] = price_values
        subset["SpecialValue"] = special_values
        subset["EffectivePrice"] = subset.apply(
            lambda row: row["SpecialValue"] if row["SpecialValue"] > 0 else row["PriceValue"], axis=1
        )
        subset = subset.sort_values(["SpecialValue", "EffectivePrice"])

        for _, row in subset.head(3).iterrows():
            item_dict = row.to_dict()
            formatted = _format_item(item_dict, category_keyword)
            if formatted:
                selected.append(formatted)

    return selected[:6]


def _format_item(row: Dict[str, any], category_keyword: str) -> Optional[Dict[str, any]]:
    """
    將 DataFrame 行轉為標準商品格式。
    """
    product_id = FieldAccessor.get_product_id(row)
    name = FieldAccessor.get_name(row)
    if not product_id or not name:
        return None

    price = FieldAccessor.get_price(row)
    special_price = FieldAccessor.get_special_price(row)
    description = FieldAccessor.get_description(row)

    highlight = _build_highlight(category_keyword, description)

    return {
        "商品編號": product_id,
        "商品名稱": name,
        "分類名稱": row.get("CateName") or "",
        "售價": price,
        "特價": special_price,
        "描述": description,
        "購物網址": row.get("Goods_Link1") or row.get("購物網址") or "",
        "商品圖片網址1": row.get("Goodspic_Link1") or row.get("商品圖片網址1") or "",
        "行銷亮點": highlight,
    }


def _build_highlight(category_keyword: str, description: Optional[str]) -> str:
    """
    依品類生成行銷亮點。
    """
    desc = description or ""
    if "餅" in category_keyword:
        return "一口即食、不沾手，攤位上最受歡迎的小點心。"
    if "飲料" in category_keyword:
        return "清涼即開即飲，適合戶外活動快速補水。"
    if "甜點" in category_keyword:
        return "視覺與味覺雙重療癒，拍照打卡吸睛。"
    if "禮盒" in category_keyword:
        return "外盒大方得體，最適合貴賓／抽獎贈品。"
    if "有機" in category_keyword or "健康" in category_keyword:
        return "主打自然無負擔，讓家長吃得安心。"
    if desc:
        return desc[:40]
    return "適合現場分享的小點，攤位人氣保證。"


def _build_summary(context: EventContext, per_person_budget: Optional[int], item_count: int) -> str:
    """
    活動摘要敘述。
    """
    parts = []
    if context.activity_type:
        parts.append(f"針對「{context.activity_type}」情境")
    if context.people_count:
        parts.append(f"預估 {context.people_count} 人")
    if per_person_budget:
        parts.append(f"控制人均預算約 {per_person_budget} 元")
    parts.append(f"精選 {item_count} 款商品打造現場亮點")
    return "，".join(parts)


def _build_slogan(context: EventContext) -> str:
    """
    生成簡短的行銷 slogan。
    """
    if context.audience == "親子":
        return "甜甜一口，笑容整路走！"
    if context.audience == "同事":
        return "讓每位同事邊享受邊聊出好氛圍。"
    if context.activity_type and "戶外" in context.activity_type:
        return "沁涼即飲，讓活動一路清爽。"
    return "現場人氣熱度加分，銷量自然跟著來！"
