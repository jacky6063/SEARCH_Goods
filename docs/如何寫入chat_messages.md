# 如何把交談資料寫入 chat_messages

本文件說明在 SEARCH_Goods 專案中如何將對話資料寫入 Supabase 的 `chat_messages` 表格。

---

## 🎯 快速開始

### 方法一：使用 ChatLoggingBridge（推薦）

這是最簡單的方式，適合在 FastAPI 端點中使用。

#### 1️⃣ 初始化 Bridge

```python
from chat_logging_bridge import ChatLoggingBridge
import logging

logger = logging.getLogger(__name__)

# 建立 bridge 實例（通常在應用啟動時建立一次）
chat_bridge = ChatLoggingBridge(
    module_type="goods",      # 模組類型: "goods", "company", "repair"
    channel="web",            # 渠道: "web", "app", "api" 等
    logger=logger
)
```

#### 2️⃣ 記錄使用者訊息

```python
# 記錄使用者輸入
supabase_session_id = chat_bridge.log_user_message(
    ui_session_id="session-123",     # UI 會話 ID（前端傳來的）
    content="我想找便宜的冷氣",      # 使用者訊息內容
    payload={                         # 額外資訊（選填）
        "query_type": "product_search",
        "voice_input": False
    }
)
```

#### 3️⃣ 記錄助理回覆

```python
# 記錄 LLM/系統回覆
chat_bridge.log_assistant_message(
    ui_session_id="session-123",
    reply="為您找到以下商品...",    # 回覆內容
    payload={                         # 回覆相關資訊
        "items": product_list,
        "meta": {"result_count": 10}
    },
    supabase_session_id=supabase_session_id  # 可選：使用之前的 session ID
)
```

---

## 📝 完整範例：在 FastAPI 端點中使用

### 範例 1：商品搜尋端點

```python
from fastapi import FastAPI, Request
from chat_logging_bridge import ChatLoggingBridge
import logging

app = FastAPI()
logger = logging.getLogger("search_goods")

# 在應用啟動時初始化
GOODS_LOGGING_BRIDGE = ChatLoggingBridge(
    module_type="goods",
    channel="search_api",
    logger=logger,
)

class SearchRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    topn: int = 10

@app.post("/api/search")
async def search_products_api(req: SearchRequest):
    # 1. 記錄使用者查詢
    supabase_session_id = GOODS_LOGGING_BRIDGE.log_user_message(
        ui_session_id=req.session_id,
        content=req.query,
        payload={
            "topn": req.topn,
            "search_type": "product"
        }
    )
    
    # 2. 執行搜尋邏輯
    results = perform_search(req.query, req.topn)
    
    # 3. 記錄系統回覆
    response_text = f"找到 {len(results)} 個商品"
    GOODS_LOGGING_BRIDGE.log_assistant_message(
        ui_session_id=req.session_id,
        reply=response_text,
        payload={
            "items": results,
            "meta": {"result_count": len(results)}
        },
        supabase_session_id=supabase_session_id
    )
    
    return {"results": results, "message": response_text}
```

### 範例 2：聊天端點

```python
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: Optional[List[Dict]] = None

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    # 1. 如果沒有 session_id，生成一個
    if not req.session_id:
        import uuid
        req.session_id = str(uuid.uuid4())[:8]
    
    # 2. 記錄使用者訊息（帶時間戳）
    supabase_session_id = GOODS_LOGGING_BRIDGE.log_user_message(
        ui_session_id=req.session_id,
        content=req.message,
        payload={
            "history_length": len(req.history or []),
            "timestamp": datetime.now().isoformat()
        },
        created_at=datetime.now()  # 可選：自訂時間
    )
    
    # 3. 生成 LLM 回覆
    llm_reply = generate_llm_response(req.message, req.history)
    
    # 4. 綁定 UI 會話與 Supabase 會話（確保對應關係）
    GOODS_LOGGING_BRIDGE.bind_ui_session(req.session_id, supabase_session_id)
    
    # 5. 記錄 LLM 回覆
    GOODS_LOGGING_BRIDGE.log_assistant_message(
        ui_session_id=req.session_id,
        reply=llm_reply,
        payload={
            "model": "gpt-4o-mini",
            "response_time_ms": 1234
        },
        supabase_session_id=supabase_session_id
    )
    
    return {
        "reply": llm_reply,
        "session_id": req.session_id
    }
```

### 範例 3：維修客服端點（實際專案範例）

```python
# 來自 backend/app.py 的實際程式碼
REPAIR_LOGGING_BRIDGE = ChatLoggingBridge(
    module_type="repair",
    channel="repair_chat_api",
    logger=logger,
)

@app.post("/api/repair/chat")
async def repair_chat_endpoint(req: RepairChatReq):
    # 生成或使用現有 session_id
    session_id = req.session_id
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())[:8]
    
    # 記錄使用者訊息
    supabase_session_id = REPAIR_LOGGING_BRIDGE.log_user_message(
        session_id,
        req.message,
        {
            "history_length": len(req.history or []),
            "topn": req.topn,
        },
    )
    
    # 執行維修項目搜尋
    results = search_repairs(req.message)
    reply = generate_repair_response(req.message, results)
    
    # 記錄系統回覆
    response_payload = {
        "reply": reply,
        "items": results,
        "meta": {"result_count": len(results)},
    }
    
    REPAIR_LOGGING_BRIDGE.bind_ui_session(session_id, supabase_session_id)
    REPAIR_LOGGING_BRIDGE.log_assistant_message(
        session_id,
        reply,
        response_payload,
        supabase_session_id=supabase_session_id,
    )
    
    return {"reply": reply, "repairs": results, "session_id": session_id}
```

---

## 🔧 方法二：直接使用 chat_logging API

如果您需要更精細的控制，可以直接使用底層 API。

### 基本用法

```python
from chat_logging import start_session, append_message
from datetime import datetime

# 1. 建立新會話
session = start_session(
    module_type="goods",
    channel="web",
    user_id="user123",           # 可選
    company_code="COMP001",      # 可選
    company_name="傳啟資訊",      # 可選
    metadata={"device": "mobile"} # 可選
)
session_id = session["session_id"]

# 2. 新增使用者訊息
user_msg = append_message(
    session_id=session_id,
    role="user",
    content="我想找冷氣機",
    payload={"query_type": "product"},
    source_module="goods"
)

# 3. 新增 LLM 回覆
llm_msg = append_message(
    session_id=session_id,
    role="llm",
    content="為您找到以下商品...",
    payload={
        "model": "gpt-4o-mini",
        "products_count": 5
    },
    source_module="goods",
    state="processed"
)

# 4. 新增客服人員訊息（如需要）
agent_msg = append_message(
    session_id=session_id,
    role="agent",
    content="我可以幫您處理訂單",
    source_module="goods"
)
```

---

## 📊 訊息類型 (role) 說明

| Role | 說明 | 使用場景 |
|------|------|----------|
| `user` | 使用者訊息 | 用戶輸入的查詢、問題 |
| `llm` | AI 助理回覆 | GPT 生成的回應、商品推薦 |
| `agent` | 客服人員 | 真人客服介入時的訊息 |
| `system` | 系統訊息 | 系統通知、狀態更新 |

---

## 📦 payload 欄位建議

### 使用者訊息 payload
```python
{
    "query_type": "product_search",      # 查詢類型
    "voice_input": False,                 # 是否語音輸入
    "device": "mobile",                   # 裝置類型
    "history_length": 3,                  # 對話歷史長度
    "filters": {"category": "家電"}       # 搜尋過濾條件
}
```

### 助理回覆 payload
```python
{
    "model": "gpt-4o-mini",              # 使用的模型
    "response_time_ms": 1234,            # 回應時間
    "items_count": 10,                   # 商品數量
    "confidence": 0.95,                  # 信心分數
    "meta": {                            # 其他中繼資料
        "result_count": 10,
        "search_terms": ["冷氣", "空調"]
    }
}
```

---

## 🔍 查詢寫入的資料

### 使用 Supabase Dashboard
1. 登入 Supabase 後台
2. 前往 Table Editor
3. 選擇 `chat_messages` 表
4. 查看最新記錄

### 使用測試腳本
```bash
cd /Users/huangchangchi/Documents/SEARCH_Goods
python scripts/supabase_db_test.py
```

### 使用 SQL 查詢
```sql
-- 查看最新 10 筆訊息
SELECT * FROM chat_messages 
ORDER BY created_at DESC 
LIMIT 10;

-- 查看特定會話的訊息
SELECT * FROM chat_messages 
WHERE session_id = 'your-session-uuid'
ORDER BY created_at ASC;

-- 統計各模組的訊息數量
SELECT source_module, role, COUNT(*) as count
FROM chat_messages
GROUP BY source_module, role;
```

---

## ⚠️ 注意事項

### 1. 環境變數設定
確保 `.env` 檔案包含：
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_role_key
```

### 2. 錯誤處理
Bridge 會自動處理錯誤，不會中斷主流程：
```python
try:
    supabase_session_id = chat_bridge.log_user_message(...)
except Exception as e:
    # Bridge 內部已經 catch，這裡的 except 通常不會觸發
    # 即使 Supabase 無法連線，API 仍會正常運作
    logger.warning(f"Logging failed: {e}")
```

### 3. Session 管理
- UI session ID 是前端管理的會話識別
- Supabase session ID 是資料庫中的 UUID
- Bridge 會自動維護兩者的對應關係

### 4. 效能考量
- 記錄是**非阻塞**的（best effort）
- 如果 Supabase 無法連線，不會影響主要功能
- 適合生產環境使用

---

## 🚀 進階功能

### 記錄商品推薦
```python
from chat_logging import log_recommendations

# 在記錄 LLM 回覆後，記錄推薦的商品
log_recommendations(
    session_id=session_id,
    message_id=llm_msg["message_id"],
    recommendations=[
        {
            "product_id": "AC001",
            "product_name": "日立冷氣",
            "source_rank": 1,
            "confidence": 0.95
        },
        {
            "product_id": "AC002",
            "product_name": "大金冷氣",
            "source_rank": 2,
            "confidence": 0.88
        }
    ]
)
```

### 記錄會話事件
```python
from chat_logging import log_session_event

# 記錄狀態變更
log_session_event(
    session_id=session_id,
    event_type="status_change",
    from_status="ongoing",
    to_status="resolved",
    details={"reason": "查詢完成"}
)

# 記錄錯誤事件
log_session_event(
    session_id=session_id,
    event_type="error",
    details={
        "error_type": "llm_timeout",
        "error_message": "OpenAI API timeout"
    }
)
```

---

## 📚 相關文件

- **API 參考**: `backend/chat_logging.py`
- **Bridge 實作**: `backend/chat_logging_bridge.py`
- **資料表設計**: `docs/系統開發/聊天紀錄資料表設計.md`
- **整合計劃**: `docs/setup/SUPABASE_整合開發計劃.md`
- **測試腳本**: `scripts/supabase_db_test.py`

---

## 🎓 總結

**推薦使用 ChatLoggingBridge**：
- ✅ 自動管理會話對應
- ✅ 內建錯誤處理
- ✅ 程式碼更簡潔
- ✅ 適合 FastAPI 端點

**直接使用 chat_logging API**：
- 🔧 更細緻的控制
- 🔧 適合複雜的記錄邏輯
- 🔧 需要手動處理會話管理

根據您的需求選擇合適的方式！如有疑問，請參考 `backend/app.py` 中的實際範例。
