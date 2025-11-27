# 聊天系統 LLM 處理流程詳解

## 📌 使用者查詢示例
```
【使用者輸入】女用包包價格在 3000~4000元之間
```

---

## 🔄 完整處理流程（時序圖）

### 第一層：API 端點
```
POST /api/chat
├─ 請求體：{
│   "message": "女用包包價格在 3000~4000元之間",
│   "user_message": "女用包包價格在 3000~4000元之間",
│   "history": [],
│   "session_id": "session123"
│ }
└─ 由 app.py line 1208 的 chat_endpoint() 接收
```

---

### 第二層：請求路由
```
chat_endpoint(req: ChatReq)
  ↓
  chat_handler(req)  [chat_router_goods_action.py line 1430]
    ↓
    ConversationInput 構建
    ├─ user_text: "女用包包價格在 3000~4000元之間"
    ├─ history: []
    ├─ session_id: "session123"
    └─ metadata: {"raw_request": ChatReq object}
    ↓
    _ORCHESTRATOR.handle(convo_input)
    ├─ 意圖檢測: _default_intent_detector() → "shopping_support"
    ├─ 路由：IntentRouter → ShoppingSupportHandler
    └─ 處理：ShoppingSupportHandler.handle()
      ↓
      _legacy_chat_flow(req)  [chat_router_goods_action.py line 1157]
```

---

### 第三層：智能檢測與路由（_legacy_chat_flow）

#### 【步驟 1】類目導覽檢測
```python
nav = _try_category_navigation_reply(user_text)
# 檢查是否為「L1→L2→L3」的分類導覽查詢
# 例如：「食品 > 零食」
# 目前使用者查詢 ❌ 不符合 → 繼續
```

#### 【步驟 2】概覽/銷售範圍檢測
```python
overview = _try_overview_scope_reply(user_text)
# 檢查是否為「你們賣什麼」、「有什麼分類」等
# 例如：「你們有什麼商品」
# 目前使用者查詢 ❌ 不符合 → 繼續
```

#### 【步驟 3】意圖檢測（使用 Planner）
```python
planner_intent = planner_detect_intent(user_text)
# 分析：「女用包包價格在 3000~4000元之間」
# 結果：
# {
#   "intent_type": "shopping_recommendation",
#   "category": "女用包包",
#   "filters": {
#     "price_range": [3000, 4000],
#     "gender": "female",
#     "product_type": "bag"
#   }
# }
```

#### 【步驟 4】聚會/派對上下文檢測
```python
party_context = need_fallback(user_text)
# 檢查是否含有「生日」、「派對」、「聚會」等關鍵詞
# 目前使用者查詢 ❌ 不符合 → party_context = False
```

---

### 【核心】第四層：LLM 聊天互動

#### **🚀 LLM 聊天模式啟動**

```
cat_reply(
    user_message="女用包包價格在 3000~4000元之間",
    history=[],
    catalog=[全產品列表],  # ~200 件商品快照
    topn=10
)
[llm_service.py line 2022]
```

**LLM 聊天流程內部：**

##### ① 聊天模式檢查
```python
chat_mode = os.getenv("USE_CHAT_MODE", "True")
# ✅ 預設啟用 → chat_mode = "True"
```

##### ② 上下文產品詢問檢測
```python
context_inquiry = _detect_context_product_inquiry(
    message="女用包包價格在 3000~4000元之間",
    history=[]
)
# 分析：
# - 是否在詢問前一條訊息提到的產品？❌ 否（首條訊息）
# - context_inquiry = None → 繼續
```

##### ③ 一般意圖檢測
```python
intent = _detect_conversation_intent("女用包包價格在 3000~4000元之間")
# 分析結果：
# ├─ 包含「包包」→ 產品搜尋
# ├─ 包含「3000~4000」→ 價格篩選
# ├─ 包含「女用」→ 性別篩選
# └─ intent = "product_search"
```

##### ④ 超出銷售範圍 (OOS) 守門
```python
oos_keywords = ("3c", "耳機", "手機", ...)
# 檢查是否為不販售品類
# 「女用包包」❌ 不在 OOS 清單 → 繼續
```

##### ⑤ 資訊/產品搜尋意圖確認
```python
if intent == "information":
    # 資訊類查詢 → 純聊天回覆
else:
    # 產品搜尋 → 進入下一階段
```

##### ⑥ 聊天上下文準備
```python
context = _prepare_chat_context(
    message="女用包包價格在 3000~4000元之間",
    catalog=[全產品列表]
)
# 結果：
# {
#   "structured_filters": {
#     "product_type": "包包",
#     "price_range": [3000, 4000],
#     "gender": "female"
#   },
#   "products": [
#     {product1}, {product2}, ...  ← 篩選後的產品
#   ],
#   "matches": [...],
#   "overview": {...}
# }
```

##### ⑦ 系統提示建構
```python
system_prompt = _build_system_prompt(prompt_items)
# 根據篩選後的產品建立 LLM 系統提示
```

##### ⑧ LLM 生成回覆

**LLM 調用方式：**
```python
reply_text = _mock_or_real_llm(
    system_prompt=<系統提示>,
    history=[],
    user_message="女用包包價格在 3000~4000元之間",
    catalog=<全產品列表>,
    context=<準備好的上下文>
)
```

**實際 LLM 呼叫：**
```python
def _mock_or_real_llm(...):
    if not _get_client():
        # Mock 模式（無 OpenAI 金鑰）
        reply = f"根據您的需求，我推薦以下{len(items)}款商品..."
    else:
        # 實際 LLM 模式
        client = _get_client()  # OpenAI 客戶端
        response = client.chat.completions.create(
            model=CHAT_OPENAI_MODEL,  # "gpt-4o-mini"
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "女用包包價格在 3000~4000元之間"}
            ],
            temperature=0.7,
            max_tokens=512
        )
        reply = response.choices[0].message.content
```

**LLM 的典型回覆：**
```
根據您的需求「女用包包價格在 3000~4000元之間」，
我為您找到了5款符合您預算的精選女用包包。

推薦商品包括：
1. 時尚真皮手提包 - $3,299
2. 職業公務包 - $3,899
3. 休閒側背包 - $3,500

這些包包都在您指定的預算範圍內，品質優良，
非常適合日常使用或上班搭配。
需要我顯示更詳細的商品信息與圖片嗎？
```

---

### 第五層：商品篩選與結構化

#### ① 結構化篩選解析
```python
structured_filters = {
    "price_range": [3000, 4000],      # 價格範圍
    "product_type": "包包",            # 商品類型
    "gender": "female",                # 性別標記
    "material": None,                  # 未指定
    "brand": None                      # 未指定
}
```

#### ② 商品搜尋與對齊
```python
products = context.get("products", [])
# 返回匹配的產品列表：
# [
#   {
#     "GoodIden": "G001234",
#     "商品名稱": "時尚真皮手提包",
#     "商品價格": 3299,
#     "分類": "女用包包",
#     "圖片": "...",
#     ...
#   },
#   {
#     "GoodIden": "G001235",
#     "商品名稱": "職業公務包",
#     "商品價格": 3899,
#     ...
#   },
#   ...
# ]
```

#### ③ 商品格式化處理
```python
formatting_result = format_product_recommendations(reply_text)
# 處理結果：
# {
#   "formatted_text": "LLM 回覆 + 格式化商品列表",
#   "product_count": 5,
#   "products": [
#     {
#       "name": "時尚真皮手提包",
#       "price": "3,299",
#       "category": "女用包包",
#       "id": "G001234"
#     },
#     ...
#   ]
# }
```

---

### 第六層：回應構建

#### 最終回應結構
```python
response = {
    "reply": "根據您的需求...（LLM 生成的完整文本）",
    "action": {
        "type": "switch_to_search",
        "items": [
            {"id": "G001234"},
            {"id": "G001235"},
            ...
        ]
    },
    "intent": "product_search",
    "overview": {
        "results": [5個產品],
        "total": 5,
        "query": "女用包包價格在 3000~4000元之間"
    },
    "structured_filters": {
        "price_range": [3000, 4000],
        "product_type": "包包",
        "gender": "female"
    },
    "alignment": {
        "intent": "product_search",
        "items": [
            {"id": "G001234", "name": "時尚真皮手提包"},
            {"id": "G001235", "name": "職業公務包"},
            ...
        ]
    },
    "structured_products": [
        {
            "name": "時尚真皮手提包",
            "price": "3,299",
            "category": "女用包包",
            "id": "G001234",
            "image_url": "..."
        },
        ...
    ]
}
```

---

### 第七層：會話快取與返回

#### ① 會話快取
```python
session_id = str(uuid.uuid4())[:8]  # 例如："a1b2c3d4"
CHAT_SESSION_CACHE[session_id] = (time.time(), shopping_resp)

# 同時快取到 Bundle Service
bundle_service.save_bundle(session_id, {
    "align_ids": ["G001234", "G001235", ...],
    "align_rows": [產品詳細資訊],
    "query_terms": ["女用包包價格在 3000~4000元之間"],
    "structured_items": [格式化後的商品],
    "structured_summary": "為您找到了 5 款相關商品",
    "structured_filters": {篩選條件}
})
```

#### ② ChatResponse 物件構建
```python
return ChatResponse(
    ok=True,
    reply="根據您的需求...（完整 LLM 回覆）",
    suggestion_ids=["G001234", "G001235", ...],
    meta={
        "has_budget_intent": True,
        "search_method": "llm_chat_mode"
    },
    action={"type": "switch_to_search", "items": [...]},
    structured_filters={...},
    structured_payload={...},
    structured_products=[...],
    chat_session_id="a1b2c3d4",
    status=None
)
```

#### ③ 最終 JSON 回應
```json
{
  "ok": true,
  "reply": "根據您的需求「女用包包價格在 3000~4000元之間」，我為您找到了5款符合您預算的精選女用包包。...",
  "suggestion_ids": ["G001234", "G001235", "G001236", "G001237", "G001238"],
  "meta": {
    "has_budget_intent": true,
    "search_method": "llm_chat_mode"
  },
  "action": {
    "type": "switch_to_search",
    "items": [
      {"id": "G001234"},
      {"id": "G001235"},
      ...
    ]
  },
  "structured_filters": {
    "price_range": [3000, 4000],
    "product_type": "包包",
    "gender": "female"
  },
  "structured_products": [
    {
      "name": "時尚真皮手提包",
      "price": "3,299",
      "category": "女用包包",
      "id": "G001234",
      "image_url": "https://..."
    },
    ...
  ],
  "session_id": "a1b2c3d4"
}
```

---

## 🎯 關鍵決策點

| 檢查項目 | 條件 | 動作 |
|---------|------|------|
| 類目導覽 | 是否為「L1→L2→L3」 | ✅ 是 → 返回導覽回覆 |
| 概覽查詢 | 是否問「你們賣什麼」 | ✅ 是 → 返回分類概覽 |
| 上下文產品 | 是否在詢問前一條商品 | ✅ 是 → 直接搜尋該商品 |
| 資訊查詢 | 是否為「怎麼用」、「好嗎」 | ✅ 是 → 純聊天模式 |
| OOS 品類 | 是否詢問「3C」、「手機」 | ✅ 是 → 告知不販售 |
| LLM 可用 | 是否有 OPENAI_API_KEY | ✅ 是 → 調用 GPT-4o-mini |
| LLM 失敗 | LLM 異常 | ❌ 是 → 使用 Mock 模式 |

---

## 💡 LLM 提示詞建構

### 系統提示詞示例（來自 _build_system_prompt）

```
你是一個精通商品推薦的智能客服。
用戶詢問：「女用包包價格在 3000~4000元之間」

根據以下相關商品進行推薦回覆：
1. 時尚真皮手提包 (G001234) - $3,299
   - 分類: 女用包包
   - 材質: 真皮
   - 風格: 時尚

2. 職業公務包 (G001235) - $3,899
   - 分類: 女用包包
   - 材質: PU皮革
   - 風格: 職業

[更多商品...]

請根據用戶需求，結合商品特點，提供友善、專業、個人化的推薦。
強調：
- 價格符合預算 ($3,000-$4,000)
- 商品特色與用途
- 推薦理由

回覆應該：
✓ 自然親切（中文繁體）
✓ 包含 2-3 個具體商品名稱
✓ 強調預算匹配
✓ 邀請用戶查看詳細信息或提問
```

---

## 🔄 LLM 環境變數控制

```bash
# 聊天模式啟用
USE_CHAT_MODE=True          # 啟用完整聊天互動

# CHAT 模型配置（聊天專用）
CHAT_OPENAI_MODEL=gpt-4o-mini
CHAT_USE_LLM_EXPAND=True    # 查詢擴展
CHAT_USE_LLM_INTENT=True    # 意圖分析
CHAT_USE_LLM_PROMO=False    # 行銷文案

# SEARCH 模型配置（搜尋專用）
SEARCH_OPENAI_MODEL=gpt-4o-mini
SEARCH_USE_LLM_EXPAND=True  # 查詢擴展
SEARCH_USE_LLM_INTENT=True  # 意圖分析
SEARCH_USE_LLM_RERANK=False # 結果重排
```

---

## 📊 流程時間複雜度

| 階段 | 耗時 | 主要操作 |
|------|------|--------|
| API 接收 | ~1ms | 請求驗證、序列化 |
| 意圖檢測 | ~10ms | 正規表達式、關鍵詞匹配 |
| 上下文準備 | ~50ms | 商品篩選、向量化 |
| LLM 調用 | ~1000-3000ms | 網路往返、GPT 推理 |
| 商品格式化 | ~20ms | JSON 構建、驗證 |
| 快取存儲 | ~10ms | Redis/記憶體寫入 |
| **總耗時** | **~1100-3100ms** | 主要受 LLM 限制 |

---

## 🛡️ 錯誤處理流程

```
LLM 聊天失敗
    ↓
├─ 嘗試 Fallback 系統（規則引擎）
│   ├─ 檢查是否為派對相關
│   └─ 執行規則匹配
│       ✅ 成功 → 返回規則結果
│       ❌ 失敗 → 繼續
│
├─ 嘗試基礎搜尋 (search_products_strict)
│   ✅ 成功 → 返回搜尋結果
│   ❌ 失敗 → 繼續
│
├─ 嘗試增強回退響應 (Mock 模式)
│   ✅ 成功 → 返回 Mock 回覆
│   ❌ 失敗 → 繼續
│
└─ 最終回退：系統繁忙提示
    "很抱歉，目前系統繁忙。請重新開始聊天..."
```

---

## 📝 總結

【使用者查詢】 → 【API 路由】 → 【意圖檢測】 → 【LLM 聊天】 → 【商品篩選】 → 【回應構建】 → 【快取保存】 → 【JSON 返回】

```
"女用包包價格在 3000~4000元之間"
    ↓
✅ 通過所有檢測
    ↓
💬 LLM 生成個性化回覆
    ↓
🎯 篩選 5 款符合條件的商品
    ↓
📦 構建結構化回應
    ↓
💾 快取會話資訊
    ↓
🚀 回傳給前端客戶端
```
