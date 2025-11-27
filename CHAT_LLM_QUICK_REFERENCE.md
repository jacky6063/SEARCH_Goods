# 聊天系統 LLM 處理流程 - 快速查看卡片

## 🎯 查詢示例追蹤

### 使用者輸入
```
"我要購買女用包包價格在 3000~4000元之間"
```

### 處理流程（簡化版）

```
POST /api/chat
    ↓
ChatReq 解析
    ↓ user_message = "我要購買女用包包價格在 3000~4000元之間"
chat_handler() [chat_router_goods_action.py:1430]
    ↓
ShoppingSupportHandler.handle()
    ↓
_legacy_chat_flow() [chat_router_goods_action.py:1157]
    ↓
┌─ 類目導覽檢測 ❌ (非導覽查詢)
├─ 概覽查詢檢測 ❌ (非概覽查詢)
├─ 派對上下文 ❌ (無派對關鍵詞)
└─ Planner 意圖分析
    category: "女用包包"
    price_range: [3000, 4000]
    ↓
chat_reply() [llm_service.py:2022]
    ├─ 聊天模式驗證 ✅
    ├─ 意圖檢測 → "product_search"
    ├─ OOS 守門 ✅ (非 3C)
    ├─ 上下文準備 → 篩選 5 件商品
    ├─ 系統提示建構
    └─ LLM 調用 (GPT-4o-mini)
        ↓ 模型模式: 0.7 溫度, 512 tokens
        ↓
        生成回覆: "根據您的需求...我為您找到了 5 款..."
        ↓
        格式化商品
        ↓
會話快取 (session_id="a1b2c3d4")
    ├─ align_ids: [G001234, G001235, ...]
    ├─ query_terms: ["女用包包價格在 3000~4000元之間"]
    └─ structured_filters: {price_range, product_type}
    ↓
返回 ChatResponse JSON
```

---

## 📦 返回 JSON 結構

```json
{
  "ok": true,
  "reply": "根據您的需求「女用包包價格在 3000~4000元之間」，我為您找到了 5 款符合您預算的精選女用包包。推薦商品包括：時尚真皮手提包、職業公務包、休閒側背包。...",
  "suggestion_ids": ["G001234", "G001235", "G001236", "G001237", "G001238"],
  "meta": {
    "has_budget_intent": true,
    "search_method": "llm_chat_mode"
  },
  "action": {
    "type": "switch_to_search",
    "items": [
      {"id": "G001234"},
      {"id": "G001235"}
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
      "id": "G001234"
    },
    {
      "name": "職業公務包",
      "price": "3,899",
      "category": "女用包包",
      "id": "G001235"
    }
  ],
  "session_id": "a1b2c3d4"
}
```

---

## 🔀 決策樹（關鍵檢查點）

```
輸入: "我要購買女用包包價格在 3000~4000元之間"
  ↓
1. 是否為類目導覽（L1→L2→L3）?
   └─ ❌ NO → 繼續
  ↓
2. 是否為概覽/銷售範圍查詢?
   └─ ❌ NO → 繼續
  ↓
3. 是否為上下文產品詢問?
   └─ ❌ NO（首條訊息）→ 繼續
  ↓
4. 是否為資訊/諮詢類?
   └─ ❌ NO → 繼續
  ↓
5. 是否為 OOS 品類（3C、手機等）?
   └─ ❌ NO → 繼續
  ↓
6. LLM 可用?
   └─ ✅ YES → 進入 LLM 聊天
  ↓
【LLM 聊天流程】
  ├─ 結構化篩選: price_range=[3000,4000], type="包包"
  ├─ 商品搜尋: 找到 5 件符合條件的商品
  ├─ 系統提示: 基於 5 件商品生成 GPT 提示
  ├─ LLM 推理: 調用 gpt-4o-mini 生成回覆
  ├─ 格式化: 添加商品結構化信息
  └─ 快取: 保存會話信息
  ↓
返回結果
```

---

## ⚙️ 環境變數

### 聊天啟用
```bash
USE_CHAT_MODE=True
```

### LLM 配置
```bash
# 聊天模型
CHAT_OPENAI_MODEL=gpt-4o-mini

# 搜尋模型
SEARCH_OPENAI_MODEL=gpt-4o-mini

# 功能開關
CHAT_USE_LLM_EXPAND=True      # 查詢擴展
CHAT_USE_LLM_INTENT=True      # 意圖分析
SEARCH_USE_LLM_EXPAND=True
SEARCH_USE_LLM_INTENT=True
```

---

## 🚀 核心函數調用鏈

| 函數 | 位置 | 功能 |
|------|------|------|
| `chat_endpoint()` | app.py:1208 | API 入口點 |
| `chat_handler()` | chat_router_goods_action.py:1430 | 路由分發 |
| `_legacy_chat_flow()` | chat_router_goods_action.py:1157 | 主流程 |
| `chat_reply()` | llm_service.py:2022 | **LLM 核心** |
| `_prepare_chat_context()` | llm_service.py | 上下文準備 |
| `_detect_conversation_intent()` | llm_service.py | 意圖檢測 |
| `_build_system_prompt()` | llm_service.py | 提示建構 |
| `_mock_or_real_llm()` | llm_service.py | **LLM 調用** |

---

## ⏱️ 效能數據

| 階段 | 耗時 | 說明 |
|------|------|------|
| API 接收 | ~1ms | 請求解析 |
| 意圖檢測 | ~10ms | 正規表達式匹配 |
| 上下文準備 | ~50ms | 商品篩選 |
| **LLM 調用** | **~1-3s** | 🔴 主要瓶頸 |
| 格式化 | ~20ms | JSON 構建 |
| 快取 | ~10ms | 存儲 |
| **總計** | **~1.1-3.1s** |  |

---

## 🛡️ 錯誤降級流程

```
LLM 聊天失敗
    ↓
1️⃣  嘗試 Fallback 系統 (規則匹配)
    ✅ 成功 → 返回規則結果
    ❌ 失敗 ↓
2️⃣  嘗試基礎搜尋 (search_products_strict)
    ✅ 成功 → 返回搜尋結果
    ❌ 失敗 ↓
3️⃣  嘗試增強 Mock 模式
    ✅ 成功 → 返回 Mock 回覆
    ❌ 失敗 ↓
4️⃣  最終回退
    "很抱歉，目前系統繁忙。請重新開始聊天..."
```

---

## 📝 結構化篩選解析示例

```python
# 輸入: "女用包包價格在 3000~4000元之間"

結果:
{
    "price_range": [3000, 4000],
    "product_type": "包包",
    "gender": "female",
    "material": None,           # 未提及
    "brand": None,              # 未提及
    "occasion": None            # 未提及
}

搜尋結果: 5 件商品
- G001234: 時尚真皮手提包 ($3,299) ✅
- G001235: 職業公務包 ($3,899) ✅
- G001236: 休閒側背包 ($3,599) ✅
- G001237: 專業通勤包 ($3,450) ✅
- G001238: 精緻手拿包 ($3,750) ✅

排除:
- G009001: 女用包包 ($2,899) ❌ (低於預算)
- G009002: 女用包包 ($4,299) ❌ (超過預算)
```

---

## 💬 LLM 提示詞結構

### 系統角色定義
```
你是一個精通商品推薦的智能客服，
代表哈通友善生活館與客戶互動。
你的目標是根據用戶需求推薦最合適的商品。
```

### 上下文（5 件相關商品）
```
用戶詢問: "女用包包價格在 3000~4000元之間"
相關商品:
1. 時尚真皮手提包 (G001234) - $3,299
2. 職業公務包 (G001235) - $3,899
...
```

### 回應要求
```
✓ 中文繁體、自然親切
✓ 包含 2-3 個具體商品名稱
✓ 強調預算匹配（3000-4000元）
✓ 邀請用戶查看詳細信息或提問
```

---

## 📊 LLM 調用參數

```python
client.chat.completions.create(
    model="gpt-4o-mini",           # 聊天模型
    messages=[
        {"role": "system", "content": "系統提示..."},
        {"role": "user", "content": "女用包包價格在..."}
    ],
    temperature=0.7,               # 創意度
    max_tokens=512,                # 最大長度
    top_p=1.0                      # 多樣性
)
```

---

## 🎯 常見查詢示例

### 1. 價格篩選（本例）
```
輸入: "女用包包價格在 3000~4000元之間"
流程: → 結構化篩選 → LLM 聊天 → 商品推薦
結果: 5 件符合商品
```

### 2. 類目導覽
```
輸入: "食品 > 零食 > 餅乾"
流程: → 類目檢測 → 直接返回導覽
結果: 導覽回覆（不進入 LLM）
```

### 3. 概覽查詢
```
輸入: "你們有什麼商品"
流程: → 概覽檢測 → 返回分類列表
結果: 分類概覽（不進入 LLM）
```

### 4. 資訊諮詢
```
輸入: "這款包包怎麼清潔"
流程: → 資訊檢測 → 純聊天模式（不搜尋商品）
結果: 專業建議（不返回商品 IDs）
```

### 5. OOS 品類
```
輸入: "有沒有 iPhone 手機"
流程: → OOS 守門 → 告知不販售
結果: "暫不販售 3C 品類" + 可售分類
```

---

## 📄 相關文檔

- **完整版**: `CHAT_LLM_PROCESSING_FLOW.md` (536 行)
  - 7 層完整架構
  - 時序圖與決策樹
  - 提示詞指南
  - 效能分析
  - 錯誤處理流程

- **快速版**: `CHAT_LLM_QUICK_REFERENCE.md` (本文)
  - 簡化流程圖
  - 決策樹
  - 核心函數列表
  - 常見示例

---

## 🔗 代碼跳轉

```
查詢 /api/chat
    ↓ 見 app.py:1208
chat_handler()
    ↓ 見 chat_router_goods_action.py:1430
ShoppingSupportHandler
    ↓ 見 chat_router_goods_action.py:642
_legacy_chat_flow()
    ↓ 見 chat_router_goods_action.py:1157
chat_reply()
    ↓ 見 llm_service.py:2022 🔴 核心 LLM 邏輯
```

---

**最後更新**: 2025年11月7日  
**提交**: f5c1370  
**相關完整文檔**: CHAT_LLM_PROCESSING_FLOW.md
