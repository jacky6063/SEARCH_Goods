import os, re
from typing import List, Dict, Optional, Tuple
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    import pandas as pd
except Exception:
    pd = None

try:
    from field_utils import FieldAccessor
except ImportError:
    # 如果無法導入，提供基本的欄位存取功能
    class FieldAccessor:
        @classmethod
        def get_field(cls, item, field_type, default=None):
            field_maps = {
                "product_id": ["商品編號", "GoodIden", "id"],
                "name": ["商品名稱", "Name", "name"],
                "price": ["售價", "Price", "price"]
            }
            if field_type in field_maps:
                for field in field_maps[field_type]:
                    if field in item:
                        return item[field]
            return default
        
        @classmethod
        def get_product_id(cls, item):
            return str(cls.get_field(item, "product_id", ""))
        
        @classmethod
        def get_name(cls, item):
            return str(cls.get_field(item, "name", ""))
        
        @classmethod
        def get_price(cls, item):
            price_str = cls.get_field(item, "price", "0")
            try:
                import re
                numbers = re.findall(r'\d+', str(price_str))
                return int(numbers[0]) if numbers else None
            except:
                return None

# 類別關鍵字（根據實際資料庫內容調整）
CAT_KEYWORDS = {
    "餅乾類": ["餅乾", "餅乾類", "蘇打餅", "洋芋片", "餅乾點心", "脆餅", "餅", "點心", "零食"],
    "飲料類": ["飲料", "飲料類", "果汁", "茶飲", "烏梅汁", "茶", "飲品", "汽水", "豆漿", "奶茶"],
    "米類": ["米", "米類", "糙米", "白米", "香米", "小米", "五穀", "十穀"],
    "麵條類": ["麵", "麵條", "麵線", "冬粉", "蕎麥麵", "燕麥麵"],
    "烹調類": ["咖哩", "醬", "調味", "燒烤醬", "燉包"],
    "穀物類": ["燕麥", "五穀", "玉米", "奇亞籽", "黑豆", "黃豆", "綠豆", "藜麥"],
}

NUMBER_RE = re.compile(r'(\d{2,6})\s*元?')

# ===== 基本工具 =====
def parse_budget(text: str) -> Optional[int]:
    if not text:
        return None
    m = NUMBER_RE.search(text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None

def need_fallback(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    
    # 擴大生日聚會關鍵字檢測
    party_keywords = ["生日", "聚會", "派對", "party", "慶祝", "活動", "宴會", "開會", "聚餐", "聚集"]
    has_party = any(k in t for k in party_keywords)
    
    # 檢查是否提到餅乾和飲料類別
    cookie_keywords = ["餅乾", "餅乾類", "蘇打餅", "洋芋片", "餅乾點心", "脆餅", "餅", "點心", "零食", "餅干"]
    drink_keywords = ["飲料", "飲料類", "果汁", "茶飲", "烏梅汁", "茶", "飲品", "汽水", "豆漿", "奶茶", "飲"]
    
    has_cookie = any(k in t for k in cookie_keywords)
    has_drink = any(k in t for k in drink_keywords)
    
    # 檢查是否提到預算
    has_budget = any(k in t for k in ["預算", "元", "錢", "金額", "價格", "多少"])
    
    # 強化觸發條件：
    # 1. 有聚會關鍵字 OR
    # 2. 同時提到餅乾和飲料 OR  
    # 3. 提到餅乾/飲料其中之一且有預算且查詢夠具體
    return bool(
        has_party or 
        (has_cookie and has_drink) or 
        ((has_cookie or has_drink) and has_budget and len(t) > 8)  # 查詢夠長且有預算意圖
    )

def _possible_paths() -> List[str]:
    cands = [
        "data/VIEW_GOODS_enhanced.csv",
        "../data/VIEW_GOODS_enhanced.csv",
        "backend/data/VIEW_GOODS_enhanced.csv",
        "/Users/huangchangchi/Documents/SEARCH_Goods/data/VIEW_GOODS_enhanced.csv",
        os.path.join(os.getcwd(), "data/VIEW_GOODS_enhanced.csv"),
        os.path.join(os.getcwd(), "../data/VIEW_GOODS_enhanced.csv"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/VIEW_GOODS_enhanced.csv"),
        "data/goods.csv",
        "backend/data/goods.csv",
        os.path.join(os.getcwd(), "data/goods.csv"),
        os.path.join(os.getcwd(), "backend/data/goods.csv"),
    ]
    return [p for p in cands if os.path.isfile(p)]

def load_catalog():
    if pd is None:
        return None
    for path in _possible_paths():
        try:
            return pd.read_csv(path, dtype=str, encoding="utf-8")
        except Exception:
            continue
    return None

def _col(df, *names):
    lowers = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lowers:
            return lowers[n.lower()]
    return None

def to_price_int(s: str) -> Optional[int]:
    if s is None:
        return None
    m = re.search(r'\d+', str(s))
    return int(m.group(0)) if m else None

def filter_real_beverages(products: List[Dict]) -> List[Dict]:
    """過濾出真正的飲料商品，排除中藥包等非飲料商品"""
    exclude_keywords = ["燉包", "藥膳", "中藥", "調味包", "湯包", "燉湯", "補品", "藥材", "養生包"]
    include_keywords = ["果汁", "茶", "咖啡", "豆漿", "汽水", "飲料", "奶茶", "可樂", "汽泡", "氣泡"]
    
    filtered = []
    for product in products:
        name = product.get("name", "").lower()
        
        # 強排除邏輯 - 如果包含排除關鍵字，一定不是飲料
        if any(exc in name for exc in exclude_keywords):
            continue
            
        # 包含邏輯 - 包含飲料關鍵字或原本就符合飲料類別
        original_matched = any(w in name for w in CAT_KEYWORDS["飲料類"])
        specific_matched = any(inc in name for inc in include_keywords)
        
        if original_matched or specific_matched:
            filtered.append(product)
    
    return filtered

# ===== 類別挑選 =====
def select_all_by_keywords(df, keywords: List[str]) -> List[Dict]:
    """取出命中該類別關鍵字的所有商品（含 name/price/id）"""
    name_col = _col(df, "商品名稱", "商品名", "name", "title")
    price_col = _col(df, "售價", "價格", "price", "特價")
    id_col = _col(df, "商品編號", "GoodIden", "goodiden", "id", "barcode", "條碼", "sku")
    if not (name_col and price_col and id_col):
        return []
    rows: List[Dict] = []
    for _, row in df.iterrows():
        # 轉換為標準字典格式以便使用 FieldAccessor
        row_dict = row.to_dict()
        
        name = FieldAccessor.get_name(row_dict)
        price = FieldAccessor.get_price(row_dict) 
        product_id = FieldAccessor.get_product_id(row_dict)
        
        if not product_id or not name or name == "未知商品":
            continue
            
        if any(w in name for w in keywords):
            rows.append({
                "id": product_id, 
                "name": name, 
                "price": price,
                # 保留原始欄位名稱以相容現有程式碼
                "商品名稱": name,
                "售價": price
            })
    
    # 特殊處理：如果是飲料類，套用真實飲料過濾
    if keywords == CAT_KEYWORDS["飲料類"]:
        rows = filter_real_beverages(rows)
    
    return rows

def avg_price(items: List[Dict]) -> Optional[float]:
    vals = [it["price"] for it in items if isinstance(it.get("price"), int)]
    if not vals:
        return None
    return sum(vals) / len(vals)

# ===== 混合式分配 =====
def count_terms(text: str, words: List[str]) -> int:
    t = text or ""
    return sum(t.count(w) for w in words)

def smart_budget_allocation(budget: int, cookie_items: List[Dict], drink_items: List[Dict], user_text: str) -> Tuple[int, int]:
    """
    智能預算分配：考慮商品種類、價格區間、聚會需求
    回傳 (餅乾預算, 飲料預算)
    """
    # 基礎分配：餅乾60%，飲料40% (聚會通常餅乾消耗較多)
    base_cookie_ratio = 0.6
    
    # 1. 語意分析調整
    c_cnt = count_terms(user_text, CAT_KEYWORDS["餅乾類"])
    d_cnt = count_terms(user_text, CAT_KEYWORDS["飲料類"])
    if c_cnt > d_cnt:
        base_cookie_ratio += 0.1
    elif d_cnt > c_cnt:
        base_cookie_ratio -= 0.1
    
    # 2. 價格分析調整
    cookie_avg = avg_price(cookie_items) or 50
    drink_avg = avg_price(drink_items) or 80
    
    # 如果飲料明顯較貴，增加飲料預算比例
    if drink_avg > cookie_avg * 1.5:
        base_cookie_ratio -= 0.1
    elif cookie_avg > drink_avg * 1.5:
        base_cookie_ratio += 0.1
    
    # 3. 商品數量調整：如果某類選擇較少，降低其預算比例
    if len(cookie_items) < 3:
        base_cookie_ratio -= 0.15
    if len(drink_items) < 3:
        base_cookie_ratio += 0.15
    
    # 4. 預算規模調整：小預算偏向便宜類別，大預算可平衡分配
    if budget < 500:
        # 小預算偏向便宜的類別
        if cookie_avg < drink_avg:
            base_cookie_ratio += 0.1
        else:
            base_cookie_ratio -= 0.1
    elif budget > 1500:
        # 大預算可以更平衡
        base_cookie_ratio = 0.5
    
    # 限制在合理範圍 [0.2, 0.8]
    base_cookie_ratio = max(0.2, min(0.8, base_cookie_ratio))
    
    cookie_budget = int(budget * base_cookie_ratio)
    drink_budget = budget - cookie_budget
    
    return cookie_budget, drink_budget

def mixed_ratio(user_text: str, cookie_items: List[Dict], drink_items: List[Dict]) -> float:
    """
    回傳餅乾比例 (0.2 ~ 0.8) - 保持向後相容性
    內部呼叫新的 smart_budget_allocation 函數
    """
    # 假設預算 1000 來計算比例 
    cookie_budget, drink_budget = smart_budget_allocation(1000, cookie_items, drink_items, user_text)
    return cookie_budget / 1000

# ===== 在各自預算內裝配商品（貪婪，低價優先，避免超支）=====
def pack_under_budget(items: List[Dict], budget: int, max_items: int = 999) -> Tuple[List[Dict], int]:
    """依價格升冪裝配，回傳(入選清單, 小計)"""
    items_sorted = sorted(items, key=lambda x: (x["price"] is None, x["price"] if x["price"] is not None else 10**9))
    picked: List[Dict] = []
    total = 0
    for it in items_sorted:
        p = it["price"] or 0
        if p <= 0 and len(picked) < max_items:
            picked.append(it)
            continue
        if p > 0 and total + p <= budget and len(picked) < max_items:
            picked.append(it)
            total += p
    return picked, total

def generate_party_suggestions(cookie_picked: List[Dict], drink_picked: List[Dict], 
                             total: int, budget: Optional[int]) -> List[str]:
    """生成聚會購物建議"""
    suggestions = []
    
    if budget is None:
        return suggestions
    
    remaining = budget - total
    
    # 預算剩餘建議
    if remaining > 100:
        suggestions.append(f"💡 **預算還剩 {remaining} 元，建議您可以**：")
        suggestions.append("   • 增加一些小包裝零食做為備用")
        suggestions.append("   • 考慮購買紙杯、餐具等聚會用品")
        suggestions.append("   • 採購新鮮水果搭配飲料")
    elif remaining > 50:
        suggestions.append(f"💰 預算還剩 {remaining} 元，可考慮加購小零食")
    elif remaining < -50:
        suggestions.append(f"⚠️  超出預算 {-remaining} 元，建議調整商品選擇")
    
    # 商品組合平衡建議
    cookie_count = len(cookie_picked)
    drink_count = len(drink_picked)
    
    if cookie_count > drink_count * 2:
        suggestions.append("⚖️  餅乾種類較多，建議平衡一下飲料選擇")
    elif drink_count > cookie_count * 2:
        suggestions.append("⚖️  飲料種類較多，可增加一些餅乾點心")
    
    # 預算利用率分析
    utilization = total / budget if budget > 0 else 0
    if utilization < 0.7:
        suggestions.append(f"📊 預算利用率 {utilization:.1%}，可考慮升級商品或增加數量")
    elif utilization > 1.1:
        suggestions.append("💸 超出預算較多，建議優先選擇必需商品")
    
    # 性價比提示
    if cookie_picked and drink_picked:
        cookie_avg = avg_price(cookie_picked) or 0
        drink_avg = avg_price(drink_picked) or 0
        if cookie_avg > 0 and drink_avg > 0:
            if cookie_avg > drink_avg * 1.5:
                suggestions.append("💭 餅乾均價較高，可考慮選擇更經濟的選項")
            elif drink_avg > cookie_avg * 1.5:
                suggestions.append("💭 飲料均價較高，可考慮選擇更經濟的選項")
    
    return suggestions

def build_enhanced_category_data(cookie_picked: List[Dict], drink_picked: List[Dict], 
                               cookie_budget: Optional[int], drink_budget: Optional[int],
                               total_budget: Optional[int]) -> Dict:
    """建立增強的分類數據，支援前端更好的顯示"""
    
    cookie_subtotal = sum(item.get("price", 0) for item in cookie_picked)
    drink_subtotal = sum(item.get("price", 0) for item in drink_picked)
    
    result = {
        "categories": {},
        "summary": {
            "total_amount": cookie_subtotal + drink_subtotal,
            "total_items": len(cookie_picked) + len(drink_picked),
            "budget_utilization": 0.0,
            "remaining_budget": 0
        }
    }
    
    if total_budget:
        result["summary"]["budget_utilization"] = (cookie_subtotal + drink_subtotal) / total_budget
        result["summary"]["remaining_budget"] = total_budget - (cookie_subtotal + drink_subtotal)
    
    if cookie_picked:
        result["categories"]["餅乾類"] = {
            "items": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "price": item["price"],
                    "category": "餅乾類"
                }
                for item in cookie_picked
            ],
            "subtotal": cookie_subtotal,
            "count": len(cookie_picked),
            "icon": "🍪",
            "budget_allocated": cookie_budget,
            "budget_used": cookie_subtotal,
            "avg_price": cookie_subtotal / len(cookie_picked) if cookie_picked else 0
        }
    
    if drink_picked:
        result["categories"]["飲料類"] = {
            "items": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "price": item["price"],
                    "category": "飲料類"
                }
                for item in drink_picked
            ],
            "subtotal": drink_subtotal,
            "count": len(drink_picked),
            "icon": "🥤", 
            "budget_allocated": drink_budget,
            "budget_used": drink_subtotal,
            "avg_price": drink_subtotal / len(drink_picked) if drink_picked else 0
        }
    
    return result

# ===== 組合回覆 =====
def compose_reply(cookie_picked: List[Dict], drink_picked: List[Dict],
                  cookie_budget: Optional[int], drink_budget: Optional[int],
                  grand_budget: Optional[int]) -> Tuple[str, List[str]]:
    ids: List[str] = []
    total = 0
    lines = ["🎉 **生日聚會商品推薦組合**"]

    # 餅乾類
    if cookie_picked:
        lines.append("\n🍪 **餅乾類商品**：")
        cookie_total = 0
        for it in cookie_picked:
            ids.append(it["id"])
            pr = f"{it['price']}元" if it.get("price") is not None else "—"
            lines.append(f"   • {it['name']} - {pr}")
            if it.get("price"): 
                total += it["price"]
                cookie_total += it["price"]
        if cookie_budget is not None:
            lines.append(f"   ▶ 餅乾類小計：{cookie_total}元 (預算：{cookie_budget}元)")

    # 飲料類
    if drink_picked:
        lines.append("\n🥤 **飲料類商品**：")
        drink_total = 0
        for it in drink_picked:
            ids.append(it["id"])
            pr = f"{it['price']}元" if it.get("price") is not None else "—"
            lines.append(f"   • {it['name']} - {pr}")
            if it.get("price"): 
                total += it["price"]
                drink_total += it["price"]
        if drink_budget is not None:
            lines.append(f"   ▶ 飲料類小計：{drink_total}元 (預算：{drink_budget}元)")

    # 總計與建議
    if grand_budget is not None:
        remain = grand_budget - total
        utilization = (total / grand_budget * 100) if grand_budget > 0 else 0
        lines.append(f"\n💰 **費用總計**：{total}元 / {grand_budget}元 (預算利用率：{utilization:.1f}%)")
        if remain > 0:
            lines.append(f"💳 剩餘預算：{remain}元")
        elif remain < 0:
            lines.append(f"⚠️  超出預算：{-remain}元")
    else:
        lines.append(f"\n💰 **預估總金額**：{total}元")

    # 新增購物建議
    if grand_budget is not None:
        suggestions = generate_party_suggestions(cookie_picked, drink_picked, total, grand_budget)
        if suggestions:
            lines.append("\n📝 **購物建議**：")
            lines.extend(suggestions)

    return ("\n".join(lines), ids)

# ===== 替代建議 =====
def create_party_alternatives(df, user_text: str, budget: Optional[int]) -> Dict:
    """當沒有餅乾飲料時，提供健康替代方案"""
    
    # 選擇適合聚會的商品類別
    alternatives = []
    
    # 1. 米類商品 - 可做飯糰、壽司
    rice_items = select_all_by_keywords(df, CAT_KEYWORDS["米類"])
    if rice_items:
        alternatives.extend(rice_items[:3])
    
    # 2. 麵條類 - 可做涼麵、湯麵
    noodle_items = select_all_by_keywords(df, CAT_KEYWORDS["麵條類"])  
    if noodle_items:
        alternatives.extend(noodle_items[:3])
        
    # 3. 穀物類 - 健康零食替代
    grain_items = select_all_by_keywords(df, CAT_KEYWORDS["穀物類"])
    if grain_items:
        alternatives.extend(grain_items[:3])
        
    # 4. 烹調類 - 調味用品
    seasoning_items = select_all_by_keywords(df, CAT_KEYWORDS["烹調類"])
    if seasoning_items:
        alternatives.extend(seasoning_items[:2])
    
    # 依預算篩選
    if budget:
        picked_items, total = pack_under_budget(alternatives, budget, max_items=8)
    else:
        picked_items = alternatives[:10]
        total = sum(item.get("price", 0) for item in picked_items)
    
    # 生成回覆
    reply_lines = [
        "抱歉，目前資料庫中沒有餅乾類和飲料類商品 😅",
        "不過我為您的生日聚會推薦一些健康美味的替代方案：",
        "",
        "🍚 **主食類商品**（可製作飯糰、壽司等聚會小點）："
    ]
    
    rice_count = 0
    noodle_count = 0
    for item in picked_items:
        name = item.get("name", "")
        price = item.get("price", 0)
        price_str = f"{price}元" if price else "價格洽詢"
        
        if any(k in name for k in ["米", "糙米", "白米"]) and rice_count < 2:
            reply_lines.append(f"   • {name} - {price_str}")
            rice_count += 1
        elif any(k in name for k in ["麵", "麵線"]) and noodle_count < 2:
            reply_lines.append(f"   • {name} - {price_str}")
            noodle_count += 1
    
    reply_lines.extend([
        "",
        "🌾 **健康穀物**（可當零食或製作能量球）："
    ])
    
    grain_count = 0
    for item in picked_items:
        name = item.get("name", "")
        price = item.get("price", 0)
        price_str = f"{price}元" if price else "價格洽詢"
        
        if any(k in name for k in ["燕麥", "奇亞", "豆"]) and grain_count < 3:
            reply_lines.append(f"   • {name} - {price_str}")
            grain_count += 1
    
    if budget:
        reply_lines.extend([
            "",
            f"💰 預估總金額約 {total}元（預算 {budget}元內）",
            "",
            "💡 **聚會小提示**：",
            "• 可用有機米製作精美飯糰或壽司",
            "• 燕麥和穀物可製作健康能量球",
            "• 搭配新鮮水果和自製果汁更棒！"
        ])
    else:
        reply_lines.extend([
            "",
            f"💰 預估總金額約 {total}元",
            "",
            "💡 建議您也可考慮到其他通路採購餅乾和飲料，",
            "搭配這些健康主食，讓聚會更豐富！"
        ])
    
    ids = [item["id"] for item in picked_items]
    
    return {
        "ok": True,
        "reply": "\n".join(reply_lines),
        "suggestion_ids": ids,
        "action": {"type": "switch_to_search", "items": [{"id": i} for i in ids]},
        "meta": {"source": "fallback_party_alternatives", "budget": budget},
    }

# ===== 主入口 =====
def run_fallback(user_text: str) -> Optional[Dict]:
    if not need_fallback(user_text):
        return None

    df = load_catalog()
    if df is None:
        return None

    budget = parse_budget(user_text)

    # 檢查是否有餅乾和飲料類商品
    cookie_all = select_all_by_keywords(df, CAT_KEYWORDS["餅乾類"])
    drink_all  = select_all_by_keywords(df, CAT_KEYWORDS["飲料類"])
    
    # 如果沒有餅乾飲料，提供替代建議
    if not cookie_all and not drink_all:
        return create_party_alternatives(df, user_text, budget)

    # --- 沒提供預算：沿用舊邏輯（各取多筆） ---
    if budget is None:
        # 取前 8 筆做展示
        cookie_picked = sorted(cookie_all, key=lambda x: (x["price"] is None, x["price"] if x["price"] else 10**9))[:8]
        drink_picked  = sorted(drink_all,  key=lambda x: (x["price"] is None, x["price"] if x["price"] else 10**9))[:8]
        reply, ids = compose_reply(cookie_picked, drink_picked, None, None, None)
        
        # 建立增強的分類商品資訊，支援豐富的前端顯示
        category_suggestions = build_enhanced_category_data(cookie_picked, drink_picked, None, None, None)
        action_items = []
        action_items.extend([{"id": item["id"]} for item in cookie_picked])
        action_items.extend([{"id": item["id"]} for item in drink_picked])
        
        return {
            "ok": True,
            "reply": reply,
            "suggestion_ids": ids,
            "category_suggestions": category_suggestions,  # 新增分類資訊
            "action": {"type": "switch_to_search", "items": action_items},
            "meta": {"source": "fallback_multi_category_no_budget"},
        }

    # --- 有預算：啟用智能分配 ---
    cookie_budget, drink_budget = smart_budget_allocation(budget, cookie_all, drink_all, user_text)
    cookie_ratio = cookie_budget / budget

    cookie_picked, cookie_sum = pack_under_budget(cookie_all, cookie_budget)
    drink_picked,  drink_sum  = pack_under_budget(drink_all,  drink_budget)

    # 若某類完全挑不到，嘗試從另一類補滿（保守，不超過總預算）
    used = cookie_sum + drink_sum
    if not cookie_picked and drink_picked and (budget - used) > 0:
        extra_cookie, add_sum = pack_under_budget(cookie_all, budget - used)
        cookie_picked.extend(extra_cookie); used += add_sum
    if not drink_picked and cookie_picked and (budget - used) > 0:
        extra_drink, add_sum = pack_under_budget(drink_all, budget - used)
        drink_picked.extend(extra_drink); used += add_sum

    reply, ids = compose_reply(cookie_picked, drink_picked, cookie_budget, drink_budget, budget)
    
    # 建立增強的分類商品資訊，支援豐富的前端顯示
    category_suggestions = build_enhanced_category_data(cookie_picked, drink_picked, cookie_budget, drink_budget, budget)
    action_items = []
    action_items.extend([{"id": item["id"]} for item in cookie_picked])
    action_items.extend([{"id": item["id"]} for item in drink_picked])
    
    return {
        "ok": True,
        "reply": reply,
        "suggestion_ids": ids,
        "category_suggestions": category_suggestions,  # 新增分類資訊
        "action": {"type": "switch_to_search", "items": action_items},
        "meta": {
            "source": "fallback_multi_category_mixed_ratio",
            "ratio_cookie": cookie_ratio,
            "budget_split": {"cookie": cookie_budget, "drink": drink_budget}
        },
    }
