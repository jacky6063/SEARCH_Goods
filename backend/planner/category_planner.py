# -*- coding: utf-8 -*-
"""
通用購物情境規劃器

目標：
- 從使用者輸入中偵測可能的購物情境（品類、預算、急迫性）
- 在 LLM 無法提供足夠商品時，以資料庫補齊建議
- 產出與聊天流程可直接整合的結構化 payload

設計原則：
- 儘量重用既有的欄位抽取工具（FieldAccessor 等），避免破壞穩定邏輯
- 新增功能採「增量」方式，不影響既有 fallback 行為
- 任何額外假設都以 metadata 記錄，便於後續評估
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from field_utils import FieldAccessor
from utils.simple_extract import extract_budget_and_cats

# -- 品類關鍵字設定 ---------------------------------------------------------
# 為了避免破壞既有邏輯，沿用 multi_category_party 的分類，並加入常見類別
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "餅乾類": [
        "餅乾",
        "點心",
        "零食",
        "脆餅",
        "洋芋片",
    ],
    "飲料類": [
        "飲料",
        "飲品",
        "茶",
        "咖啡",
        "果汁",
        "汽水",
        "奶茶",
    ],
    "廚房用品": [
        "鍋具",
        "餐具",
        "廚房用具",
        "廚具",
        "煮鍋",
        "炒鍋",
        "湯鍋",
        "平底鍋",
        "不銹鋼鍋",
        "陶瓷鍋",
        "砧板",
        "菜刀",
        "料理器具",
        "廚房器械",
    ],
    "健康保健": [
        "保健",
        "健康",
        "維他命",
        "營養",
        "補充",
        "養生",
    ],
    "派對用品": [
        "派對",
        "聚會",
        "生日",
        "裝飾",
        "氣球",
        "一次性餐具",
    ],
}

# 負面關鍵字 - 用於排除不相關的商品
NEGATIVE_KEYWORDS: Dict[str, List[str]] = {
    "廚房用品": [
        "鍋粑", "鍋巴", "鍋巴餅", "鹹酥鍋粑", "火鍋", "麻辣鍋", "火鍋料",
        "泡麵", "零食", "餅乾", "點心", "小食", "休閒食品", "膨化食品",
        "米果", "米餅", "薯條", "薯片", "爆米花", "仙貝"
    ],
    "健康保健": [
        "保健餅乾", "健康零食", "營養餅乾", "養生茶點", "保健食品餅",
        "維他命糖果", "健康小食", "營養棒"
    ],
    "飲料類": [
        "飲料杯", "茶杯", "咖啡杯", "水壺", "保溫杯", "茶具", "咖啡機"
    ],
    "餅乾類": [
        "餅乾盒", "餅乾罐", "點心盒"
    ]
}

# 商品分類欄位參考 - 用於交叉驗證
CATEGORY_FIELD_MAPPING: Dict[str, List[str]] = {
    "廚房用品": [
        "廚具", "鍋具", "餐具", "廚房用品", "烹飪器具", "料理用具",
        "kitchen", "cookware", "kitchenware", "utensils"
    ],
    "健康保健": [
        "保健食品", "營養補充", "健康食品", "維他命", "保健品", 
        "health", "supplement", "vitamin", "nutrition"
    ],
    "飲料類": [
        "飲料", "飲品", "茶類", "咖啡", "果汁", "飲用",
        "beverage", "drink", "tea", "coffee", "juice"
    ],
    "餅乾類": [
        "餅乾", "點心", "零食", "休閒食品", "小食",
        "snack", "cookie", "biscuit", "cracker"
    ]
}

# 紧急需求關鍵字
URGENCY_KEYWORDS = ["快點", "趕時間", "來不及", "急", "馬上", "立刻", "盡快", "儘快", "越快"]

# ---------------------------------------------------------------------------


@dataclass
class DetectedIntent:
    """偵測到的使用者需求"""

    categories: List[str] = field(default_factory=list)
    budget: Optional[int] = None
    urgency: bool = False
    confidence: float = 0.0
    raw_query: str = ""
    matched_keywords: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class CategoryPlan:
    """單一品類的預算與商品建議"""

    category: str
    allocated_budget: Optional[int]
    picked_items: List[Dict[str, Any]]
    subtotal: int
    available_items: int


@dataclass
class PlannerResult:
    """整體規劃輸出"""

    plans: List[CategoryPlan]
    total_budget: Optional[int]
    total_cost: int
    suggestions: List[str]
    notes: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 偵測與意圖解析
# ---------------------------------------------------------------------------


def detect_intent(user_text: str) -> DetectedIntent:
    """
    從使用者文字中偵測可能的購物情境。
    只新增訊息，不影響既有聊天行為。
    """
    text = user_text or ""
    lowered = text.lower()

    # 預算偵測：沿用 simple_extract 的邏輯確保一致
    budget_info = extract_budget_and_cats(text)
    budget = None
    if budget_info.get("budget_info"):
        budget_data = budget_info["budget_info"]
        budget = budget_data.get("max_price")
    elif isinstance(budget_info.get("budget"), (int, float)):
        budget = int(budget_info["budget"])

    matched_categories: Dict[str, List[str]] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in lowered]
        if hits:
            matched_categories[category] = hits

    urgency = any(word in lowered for word in URGENCY_KEYWORDS)

    # 計算信心：有品類 + 預算 + 文字長度
    confidence = 0.0
    if matched_categories:
        confidence += 0.4
        confidence += min(0.3, 0.1 * len(matched_categories))
    if budget:
        confidence += 0.2
    if len(lowered) > 30:
        confidence += 0.1
    confidence = min(1.0, round(confidence, 2))

    return DetectedIntent(
        categories=list(matched_categories.keys()),
        budget=budget,
        urgency=urgency,
        confidence=confidence,
        raw_query=text,
        matched_keywords=matched_categories,
    )


# ---------------------------------------------------------------------------
# 規劃與選品
# ---------------------------------------------------------------------------


def build_plan(
    intent: DetectedIntent,
    catalog_df: Optional[pd.DataFrame],
    max_items_per_category: int = 5,
) -> PlannerResult:
    """
    依據偵測到的品類/預算，從商品目錄中挑選建議。
    """
    if catalog_df is None or catalog_df.empty:
        return PlannerResult(
            plans=[],
            total_budget=intent.budget,
            total_cost=0,
            suggestions=["查無商品資料，請稍後再試。"],
            notes={"reason": "empty_catalog"},
        )

    categories = intent.categories or _guess_categories_from_catalog(catalog_df, intent)
    if not categories:
        return PlannerResult(
            plans=[],
            total_budget=intent.budget,
            total_cost=0,
            suggestions=["尚未找出明確品類，建議先與使用者進一步確認需求。"],
            notes={"reason": "no_detected_category"},
        )

    category_candidates: Dict[str, List[Dict[str, Any]]] = {}
    for category in categories:
        category_candidates[category] = _gather_candidates_for_category(catalog_df, category)

    allocated_budgets = _allocate_budget(intent.budget, category_candidates)

    plans: List[CategoryPlan] = []
    total_cost = 0
    for category, candidates in category_candidates.items():
        budget_for_category = allocated_budgets.get(category)
        picked, subtotal = _pick_items(candidates, budget_for_category, max_items_per_category)
        total_cost += subtotal
        plans.append(
            CategoryPlan(
                category=category,
                allocated_budget=budget_for_category,
                picked_items=picked,
                subtotal=subtotal,
                available_items=len(candidates),
            )
        )

    suggestions = _compose_suggestions(intent, plans)
    notes: Dict[str, Any] = {
        "detected_categories": categories,
        "budget_split": allocated_budgets,
        "urgency": intent.urgency,
        "confidence": intent.confidence,
    }

    return PlannerResult(
        plans=plans,
        total_budget=intent.budget,
        total_cost=total_cost,
        suggestions=suggestions,
        notes=notes,
    )


def compose_plan_payload(result: PlannerResult) -> Dict[str, Any]:
    """
    將規劃結果轉換為聊天流程可直接使用的 structured payload。
    """
    category_payload = {}
    suggestion_ids: List[str] = []
    for plan in result.plans:
        items_payload = []
        for item in plan.picked_items:
            product_id = FieldAccessor.get_product_id(item) if not isinstance(item, dict) else (
                item.get("id") or item.get("GoodIden") or item.get("商品編號")
            )
            name = FieldAccessor.get_name(item)
            price = FieldAccessor.get_price(item)
            items_payload.append(
                {
                    "id": product_id,
                    "name": name,
                    "price": price,
                    "category": plan.category,
                }
            )
            if product_id:
                suggestion_ids.append(str(product_id))

        category_payload[plan.category] = {
            "items": items_payload,
            "subtotal": plan.subtotal,
            "allocated_budget": plan.allocated_budget,
            "available_items": plan.available_items,
        }

    return {
        "structured_payload": {
            "summary": {
                "total_budget": result.total_budget,
                "total_cost": result.total_cost,
                "categories": list(category_payload.keys()),
            },
            "categories": category_payload,
        },
        "suggestion_ids": suggestion_ids,
        "suggestions": result.suggestions,
        "notes": result.notes,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _guess_categories_from_catalog(df: pd.DataFrame, intent: DetectedIntent) -> List[str]:
    """
    當無明確品類時，試著根據商品目錄與使用者文字推估可能類別。
    現階段保持簡單，避免過度影響既有流程。
    """
    text = intent.raw_query.lower()
    inferred: List[str] = []

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            inferred.append(category)

    return inferred[:3]  # 避免一次選太多類別


def _gather_candidates_for_category(df: pd.DataFrame, category: str) -> List[Dict[str, Any]]:
    """
    從資料表擷取與品類相關的商品，使用增強的過濾邏輯避免誤分類。
    """
    records = df.to_dict(orient="records")
    category_lower = category.lower()
    keywords = CATEGORY_KEYWORDS.get(category, [])
    negative_keywords = NEGATIVE_KEYWORDS.get(category, [])
    category_fields = CATEGORY_FIELD_MAPPING.get(category, [])

    candidates: List[Dict[str, Any]] = []
    for row in records:
        if _validate_category_match(row, category, keywords, negative_keywords, category_fields):
            candidates.append(row)

    return candidates


def _validate_category_match(
    item: Dict[str, Any], 
    category: str, 
    keywords: List[str], 
    negative_keywords: List[str],
    category_fields: List[str]
) -> bool:
    """
    驗證商品是否真正屬於指定分類，使用多層次驗證邏輯。
    """
    # 獲取商品基本資訊
    row_category = str(
        item.get("CateName") or item.get("分類名稱") or FieldAccessor.get_category(item) or ""
    ).lower()
    row_name = FieldAccessor.get_name(item).lower()
    row_desc = str(
        item.get("ShortDesc") or item.get("Description") or item.get("商品描述") or ""
    ).lower()
    
    # 組合搜索文本
    haystack = f"{row_category} {row_name} {row_desc}"
    
    # 第一步：負面關鍵字排除 - 如果包含負面關鍵字，直接排除
    for neg_kw in negative_keywords:
        if neg_kw in haystack:
            return False
    
    # 第二步：商品分類欄位優先判斷
    for cat_field in category_fields:
        if cat_field in row_category:
            return True
    
    # 第三步：正面關鍵字匹配，但需要更嚴格的規則
    positive_matches = 0
    for keyword in keywords:
        if keyword in haystack:
            positive_matches += 1
    
    # 第四步：特殊規則處理
    if category == "廚房用品":
        # 廚房用品需要更嚴格的驗證
        # 如果只匹配到"鍋"字，需要確認不是食品
        if "鍋" in haystack and positive_matches == 1:
            # 檢查是否為真正的鍋具
            genuine_cookware = any(term in haystack for term in [
                "不銹鋼", "陶瓷", "鑄鐵", "平底", "炒鍋", "湯鍋", "煮鍋", 
                "鍋具", "廚具", "cm", "公分", "直徑", "容量", "ml", "公升"
            ])
            return genuine_cookware
        
        # 其他廚房用品關鍵字需要至少匹配一個
        return positive_matches > 0
    
    elif category == "健康保健":
        # 健康保健品需要確認不是一般食品
        if positive_matches > 0:
            # 排除一般食品標籤
            food_indicators = any(term in haystack for term in [
                "餅乾", "零食", "點心", "糖果", "巧克力", "蛋糕"
            ])
            return not food_indicators
    
    # 其他分類使用標準匹配
    return positive_matches > 0


def _allocate_budget(
    total_budget: Optional[int],
    category_candidates: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Optional[int]]:
    """
    依據平均價格與候選數量，計算各品類的預算分配。
    """
    categories = list(category_candidates.keys())
    if total_budget is None:
        return {category: None for category in categories}

    if total_budget <= 0:
        return {category: 0 for category in categories}

    if len(categories) == 1:
        return {categories[0]: total_budget}

    avg_prices: Dict[str, float] = {}
    weights: Dict[str, float] = {}
    for category, candidates in category_candidates.items():
        prices = [
            FieldAccessor.get_price(item) or 0
            for item in candidates[:20]
            if FieldAccessor.get_price(item)
        ]
        avg = sum(prices) / len(prices) if prices else 0
        avg_prices[category] = avg
        weights[category] = max(1.0, avg) * max(1, len(candidates))

    total_weight = sum(weights.values()) or len(categories)
    allocated: Dict[str, Optional[int]] = {}
    distributed = 0
    for idx, category in enumerate(categories):
        if idx == len(categories) - 1:
            share = total_budget - distributed
        else:
            ratio = weights[category] / total_weight if total_weight else (1 / len(categories))
            share = math.floor(total_budget * ratio)
            distributed += share
        allocated[category] = max(0, share)

    return allocated


def _pick_items(
    candidates: List[Dict[str, Any]],
    budget: Optional[int],
    max_items: int,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    採用貪婪策略，在預算內挑選價格較低的商品。
    """
    if not candidates:
        return [], 0

    sortable: List[Tuple[int, Dict[str, Any]]] = []
    for row in candidates:
        price = FieldAccessor.get_price(row) or 0
        sortable.append((price, row))

    sortable.sort(key=lambda x: (x[0] <= 0, x[0]))

    picked: List[Dict[str, Any]] = []
    subtotal = 0
    for price, row in sortable:
        if budget is not None and budget >= 0:
            if price <= 0:
                if len(picked) < max_items:
                    picked.append(row)
                continue
            if subtotal + price > budget:
                continue
        picked.append(row)
        subtotal += max(price, 0)
        if len(picked) >= max_items:
            break

    return picked, subtotal


def _compose_suggestions(intent: DetectedIntent, plans: List[CategoryPlan]) -> List[str]:
    """
    基於規劃結果產出簡易建議文字，避免破壞既有顯示。
    """
    if not plans:
        return []

    suggestions: List[str] = []
    if intent.budget:
        unused = intent.budget - sum(plan.subtotal for plan in plans)
        if unused > 50:
            suggestions.append(f"預算尚餘約 {unused} 元，可再挑選喜歡的商品。")
        elif unused < -50:
            suggestions.append(f"目前超出預算約 {-unused} 元，可調整品項或改選特價商品。")

    for plan in plans:
        if plan.available_items == 0:
            suggestions.append(f"{plan.category} 目前沒有找到合適的商品，建議向使用者確認是否要改變需求。")
        elif plan.allocated_budget and plan.subtotal > plan.allocated_budget * 1.2:
            suggestions.append(f"{plan.category} 的選項超出分配預算，建議詢問是否提高預算或換其他商品。")

    if intent.urgency:
        suggestions.append("使用者看起來很急迫，建議先提供精簡清單，之後再補充細節。")

    return suggestions
